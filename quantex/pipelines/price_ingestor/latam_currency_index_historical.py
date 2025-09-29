import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd

# Rutas/entorno
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from quantex.core.database_manager import supabase


def _fetch_ohlcv_series_paginated(ticker: str, start_date: str) -> pd.DataFrame | None:
    """
    Descarga todos los registros de market_data_ohlcv para un ticker desde start_date
    usando paginación. Devuelve DataFrame indexado por fecha (date) con columna 'close'.
    """
    page_size = 1000
    all_rows: list[dict] = []

    # Estrategia robusta: eq exacto → ilike exacto → ilike con comodines
    strategies = [
        ('eq', lambda q: q.eq('ticker', ticker)),
        ('ilike', lambda q: q.ilike('ticker', ticker)),
        ('ilike_wild', lambda q: q.ilike('ticker', f"%{ticker.strip()}%")),
    ]

    for label, apply_filter in strategies:
        print(f"   -> 🔍 Intento '{label}' en market_data_ohlcv para {ticker}", flush=True)
        offset = 0
        while True:
            print(f"      ⏳ offset={offset}", flush=True)
            q = (
                supabase.table('market_data_ohlcv')
                .select('timestamp,close,ticker')
                .gte('timestamp', start_date)
                .order('timestamp', desc=False)
                .range(offset, offset + page_size - 1)
            )
            q = apply_filter(q)
            res = q.execute()
            rows = res.data or []
            print(f"         ↳ página: {len(rows)} filas", flush=True)
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size
        if all_rows:
            break

    if not all_rows:
        return None

    df = pd.DataFrame(all_rows)
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.date
    df = df.set_index('timestamp')
    return df[['close']].copy()


def _get_or_create_series_definition() -> str | None:
    try:
        series_res = supabase.table('series_definitions').select('id').eq('ticker', 'latam_currency_index').maybe_single().execute()
        if series_res.data:
            return series_res.data['id']
        payload = {
            'ticker': 'latam_currency_index',
            'description': 'Índice de Monedas LATAM (Ponderado por Comercio Exterior)',
            'source': 'quantex_benchmarks',
            'unit': 'index_value',
            'category': 'currency_index',
            'country': 'latam',
            'display_name': 'Índice de Monedas LATAM (Ponderado por Comercio Exterior)',
            'is_active': True,
        }
        ins = supabase.table('series_definitions').insert(payload).execute()
        if ins.data:
            return ins.data[0]['id']
        return None
    except Exception as e:
        print(f"❌ Error creando/obteniendo definición de serie: {e}")
        return None


def _upsert_historical(records: list[dict]) -> Dict[str, Any]:
    try:
        series_id = _get_or_create_series_definition()
        if not series_id:
            return {'error': 'series_creation_failed'}
        for r in records:
            r['series_id'] = series_id
            r['ticker'] = 'latam_currency_index'

        batch_size = 1000
        inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            print(f"   -> 💾 Upsert lote {i//batch_size + 1}: {len(batch)} filas", flush=True)
            supabase.table('time_series_data').upsert(batch, on_conflict='series_id,timestamp').execute()
            inserted += len(batch)
        print(f"🎉 Serie histórica insertada: {inserted}/{len(records)} registros")
        return {'success': True, 'total_records': len(records), 'inserted_records': inserted}
    except Exception as e:
        print(f"❌ Error upsert histórico: {e}")
        return {'error': str(e)}


def build_latam_index_historical(start_date: str, dry_run: bool = False) -> Dict[str, Any]:
    print(f"📈 Construyendo serie histórica LATAM desde {start_date} (sin forward fill)...")

    weights = {
        'USDMXN.FOREX': 0.35,
        'USDBRL.FOREX': 0.30,
        'USDCOP.FOREX': 0.20,
        'USDPEN.FOREX': 0.15,
    }

    dfs: dict[str, pd.DataFrame] = {}
    for ticker in weights.keys():
        print(f"🔍 Descargando {ticker}...")
        df = _fetch_ohlcv_series_paginated(ticker, start_date)
        if df is None or df.empty:
            print(f"❌ No hay datos para {ticker}")
            return {'error': f'no_data_for_{ticker}'}
        df.rename(columns={'close': ticker}, inplace=True)
        dfs[ticker] = df

    # Join interno de las 4 series por fecha
    combined = None
    for t, d in dfs.items():
        combined = d if combined is None else combined.join(d, how='inner')
    combined = combined.sort_index().dropna(how='any')
    if combined.empty:
        print("❌ No hay fechas comunes entre las 4 series")
        return {'error': 'no_common_dates'}

    w = weights
    idx_values = (
        combined['USDMXN.FOREX'] * w['USDMXN.FOREX'] +
        combined['USDBRL.FOREX'] * w['USDBRL.FOREX'] +
        combined['USDCOP.FOREX'] * w['USDCOP.FOREX'] +
        combined['USDPEN.FOREX'] * w['USDPEN.FOREX']
    )

    records = [
        {'timestamp': dt.isoformat(), 'value': float(val)}
        for dt, val in idx_values.items()
        if pd.notna(val)
    ]
    print(f"✅ Índice histórico calculado: {len(records)} puntos")

    if dry_run:
        print(f"🧪 DRY-RUN: se insertarían {len(records)} registros")
        return {'historical_points': len(records)}

    return _upsert_historical(records)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Construye la serie histórica del índice LATAM (sin forward fill).')
    parser.add_argument('--start', required=True, help='Fecha de inicio YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true', help='No inserta en Supabase')
    args = parser.parse_args()

    try:
        _ = datetime.fromisoformat(args.start)
    except Exception:
        print(f"❌ Fecha inválida en --start={args.start}. Formato esperado YYYY-MM-DD")
        sys.exit(1)

    res = build_latam_index_historical(start_date=args.start, dry_run=args.dry_run)
    print(f"📋 Resultado: {res}")



import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import pandas as pd

from quantex.core.database_manager import supabase
from quantex.core.data_fetcher import get_data_series


def _fetch_clp_bonds() -> List[Dict[str, Any]]:
    """Fetch CLP nominal bonds with maturity from fixed_income_definitions."""
    response = supabase.table('fixed_income_definitions') \
        .select('id,name,currency,maturity_date') \
        .eq('currency', 'CLP') \
        .not_.is_('maturity_date', 'null') \
        .execute()
    return response.data or []


def _parse_date(date_value: Any) -> Optional[datetime]:
    if not date_value:
        return None
    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value.replace('Z', ''))
        except Exception:
            return None
    if isinstance(date_value, datetime):
        return date_value
    return None


def _pick_nearest_bond(bonds: List[Dict[str, Any]], target_years: int) -> Optional[Dict[str, Any]]:
    today = datetime.now().date()
    target_date = today + timedelta(days=round(365.25 * target_years))

    best = None
    best_diff = None
    for b in bonds:
        m = _parse_date(b.get('maturity_date'))
        if not m:
            continue
        m_date = m.date()
        if m_date <= today:
            continue
        diff = abs((m_date - target_date).days)
        if best is None or diff < best_diff:
            best = b
            best_diff = diff
    return best


def _fetch_latest_average_yield(instrument_id: str) -> tuple[Optional[float], Optional[str]]:
    """Get the most recent average_yield and its trade_date."""
    resp = supabase.table('fixed_income_trades') \
        .select('average_yield,trade_date') \
        .eq('instrument_id', instrument_id) \
        .order('trade_date', desc=True) \
        .limit(1) \
        .execute()
    rows = resp.data or []
    if not rows:
        return None, None
    
    row = rows[0]
    val = row.get('average_yield')
    trade_date = row.get('trade_date')
    
    try:
        return float(val), trade_date
    except (TypeError, ValueError):
        return None, trade_date


def _get_benchmark_definition_id(benchmark_name: str) -> Optional[str]:
    """Get benchmark definition ID by name (same logic as carga_historicos_bloomberg)."""
    existing = supabase.table('fixed_income_definitions') \
        .select('id') \
        .eq('name', benchmark_name) \
        .maybe_single() \
        .execute()
    
    if existing.data:
        return existing.data['id']
    
    print(f"⚠️  Benchmark '{benchmark_name}' no encontrado en fixed_income_definitions")
    return None


def _insert_benchmark_point(benchmark_name: str, trade_date: datetime, avg_yield: float) -> bool:
    # Obtener la definición del benchmark (debe existir previamente)
    instrument_id = _get_benchmark_definition_id(benchmark_name)
    if not instrument_id:
        return False
    
    payload = {
        'instrument_id': instrument_id,
        'instrument_name': benchmark_name,
        'trade_date': trade_date.date().isoformat(),
        'average_yield': avg_yield,
    }
    try:
        # Usar upsert para evitar duplicados por fecha
        supabase.table('fixed_income_trades').upsert(
            payload, 
            on_conflict='instrument_id,trade_date'
        ).execute()
        return True
    except Exception as e:
        print(f"   Error en upsert: {e}")
        return False


def sync_btp_benchmarks(dry_run: bool = False) -> Dict[str, Any]:
    """Create/update simple nominal CLP benchmarks for 2y/5y/10y using nearest-maturity bond yields.

    Bench names:
      - Benchmark BTP 2 años
      - Benchmark BTP 5 años
      - Benchmark BTP 10 años
    """
    today = datetime.now(timezone.utc)
    bonds = _fetch_clp_bonds()
    
    print(f"🔍 Encontrados {len(bonds)} bonos CLP con maturity_date")
    if dry_run:
        print("🧪 MODO DRY-RUN: No se insertará nada en Supabase")

    results: Dict[str, Any] = {}
    targets = {
        2: 'Benchmark BTP 2 años',
        5: 'Benchmark BTP 5 años',
        10: 'Benchmark BTP 10 años',
    }

    for years, bench_name in targets.items():
        print(f"\n--- Benchmark {years}y: {bench_name} ---")
        
        pick = _pick_nearest_bond(bonds, years)
        if not pick:
            print(f"❌ No se encontró bono para {years}y")
            results[bench_name] = 'no_bond_found'
            continue

        source_name = pick['name']
        source_id = pick['id']
        maturity = pick.get('maturity_date', 'N/A')
        print(f"✅ Bono seleccionado: {source_name}")
        print(f"   Maturity: {maturity}")
        print(f"   ID: {source_id}")
        
        avg, trade_date = _fetch_latest_average_yield(source_id)
        if avg is None:
            print(f"❌ No hay yield disponible para {source_name}")
            results[bench_name] = f'no_yield_for {source_name}'
            continue

        print(f"📊 Yield encontrado: {avg:.4f}% (fecha: {trade_date})")
        
        if dry_run:
            print(f"🧪 [DRY-RUN] Se insertaría: {bench_name} = {avg:.4f}% (fecha: {trade_date})")
            results[bench_name] = f'dry_run_ok: {avg:.4f}%'
        else:
            # Usar la fecha de la transacción, no la fecha actual
            trade_datetime = datetime.fromisoformat(trade_date) if trade_date else today
            ok = _insert_benchmark_point(bench_name, trade_datetime, avg)
            if ok:
                print(f"✅ Insertado en Supabase: {bench_name} = {avg:.4f}% (fecha: {trade_date})")
                results[bench_name] = 'ok'
            else:
                print(f"❌ Error insertando en Supabase")
                results[bench_name] = 'insert_failed'

    return results


def _get_or_create_series_definition(ticker: str, description: str) -> str | None:
    """
    Obtiene o crea una definición de serie siguiendo el patrón del sistema.
    Basado en sync_bcentral.py
    """
    try:
        # Buscar serie existente
        series_res = supabase.table('series_definitions').select('id').eq('ticker', ticker).maybe_single().execute()
        
        if series_res.data:
            series_id = series_res.data['id']
            print(f"   -> ✅ Usando serie existente: {series_id}")
            return series_id
        else:
            # Crear nueva definición siguiendo el patrón del sistema
            new_series = {
                'ticker': ticker,
                'description': description,
                'source': 'quantex_benchmarks',
                'unit': 'index_value',
                'category': 'currency_index',
                'country': 'latam',
                'display_name': description,
                'is_active': True
            }
            
            series_res = supabase.table('series_definitions').insert(new_series).execute()
            if series_res.data:
                series_id = series_res.data[0]['id']
                print(f"   -> ✅ Creada nueva definición de serie: {series_id}")
                return series_id
            else:
                print(f"   -> ❌ Error creando definición de serie")
                return None
                
    except Exception as e:
        print(f"❌ Error obteniendo/creando serie: {e}")
        return None


def _insert_latam_index_point(index_value: float, timestamp: str) -> bool:
    """
    Inserta punto del índice LATAM siguiendo el patrón del sistema.
    Basado en cochilco_final_bot.py y sync_bcentral.py
    """
    try:
        # Obtener o crear la definición de serie
        series_id = _get_or_create_series_definition(
            ticker='latam_currency_index',
            description='Índice de Monedas LATAM (Ponderado por Comercio Exterior)'
        )
        
        if not series_id:
            return False
        
        # Preparar el registro siguiendo el patrón del sistema
        record = {
            'series_id': series_id,
            'timestamp': timestamp,
            'value': index_value,
            'ticker': 'latam_currency_index'
        }
        
        # Upsert siguiendo el patrón del sistema
        upsert_res = supabase.table('time_series_data').upsert(
            record,
            on_conflict='series_id,timestamp'
        ).execute()
        
        if upsert_res.data:
            print(f"   -> ✅ Registro insertado exitosamente")
            return True
        else:
            print(f"   -> ❌ Error en upsert")
            return False
        
    except Exception as e:
        print(f"❌ Error insertando índice LATAM: {e}")
        return False


def sync_latam_currency_index(dry_run: bool = False) -> Dict[str, Any]:
    """
    Calcula y sincroniza el índice de monedas LATAM usando el buscador universal.
    Ponderaciones por comercio exterior:
    - USDMXN: 35%
    - USDBRL: 30% 
    - USDCOP: 20%
    - USDPEN: 15%
    """
    print("🌎 Iniciando cálculo del índice de monedas LATAM...")
    
    # Ponderaciones por comercio exterior
    weights = {
        'USDMXN.FOREX': 0.35,  # México - 35%
        'USDBRL.FOREX': 0.30,  # Brasil - 30%
        'USDCOP.FOREX': 0.20,  # Colombia - 20%
        'USDPEN.FOREX': 0.15   # Perú - 15%
    }
    
    if dry_run:
        print("🧪 MODO DRY-RUN: No se insertará nada en Supabase")
    
    results = {}
    
    try:
        # Obtener precios más recientes de cada moneda usando el buscador universal
        currency_prices = {}
        
        for ticker, weight in weights.items():
            print(f"🔍 Obteniendo precio para {ticker} usando buscador universal...")
            
            # Usar el buscador universal que busca en todas las tablas
            df = get_data_series(ticker, days=30)  # Últimos 30 días
            
            if df is None or df.empty:
                print(f"❌ No se encontraron datos para {ticker}")
                results[ticker] = 'no_data_found'
                continue
            
            # Obtener el precio más reciente (última fila)
            latest_price = df['close'].iloc[-1]
            latest_date = df.index[-1]
            
            currency_prices[ticker] = {
                'price': float(latest_price),
                'timestamp': latest_date.strftime('%Y-%m-%d'),
                'weight': weight
            }
            
            print(f"✅ {ticker}: {latest_price:.4f} (peso: {weight*100}%) - Fecha: {latest_date.strftime('%Y-%m-%d')}")
        
        # Calcular el índice ponderado
        if len(currency_prices) == 4:  # Todas las monedas disponibles
            weighted_index = 0
            total_weight = 0
            
            for ticker, data in currency_prices.items():
                weighted_index += data['price'] * data['weight']
                total_weight += data['weight']
            
            # Normalizar por el peso total (debería ser 1.0)
            if total_weight > 0:
                weighted_index = weighted_index / total_weight
            
            print(f"\n📊 ÍNDICE LATAM CALCULADO:")
            print(f"   Valor: {weighted_index:.4f}")
            print(f"   Fecha: {list(currency_prices.values())[0]['timestamp']}")
            
            if dry_run:
                print(f"🧪 [DRY-RUN] Se insertaría: latam_currency_index = {weighted_index:.4f}")
                results['index'] = f'dry_run_ok: {weighted_index:.4f}'
            else:
                # Insertar en la serie latam_currency_index
                success = _insert_latam_index_point(weighted_index, list(currency_prices.values())[0]['timestamp'])
                if success:
                    print(f"✅ Insertado en Supabase: latam_currency_index = {weighted_index:.4f}")
                    results['index'] = 'inserted_successfully'
                else:
                    print(f"❌ Error insertando en Supabase")
                    results['index'] = 'insert_failed'
            
        else:
            print(f"❌ No se pudo calcular el índice: {len(currency_prices)}/4 monedas disponibles")
            results['index'] = f'insufficient_data: {len(currency_prices)}/4'
    
    except Exception as e:
        print(f"❌ Error calculando índice LATAM: {e}")
        results['error'] = str(e)
    
    return results


def _fetch_ohlcv_series_paginated(ticker: str, start_date: str) -> pd.DataFrame | None:
    """
    Descarga todos los registros de market_data_ohlcv para un ticker desde start_date
    usando paginación (límite 1000 por request en Supabase UI/API por defecto).
    """
    try:
        page_size = 1000
        offset = 0
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
                    .order('timestamp', asc=True)
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
        df = df.rename(columns={'close': ticker})[[ticker]]
        return df
    except Exception:
        return None


def sync_latam_currency_index_historical(days_back: int = 365, dry_run: bool = False, start_date: str | None = None) -> Dict[str, Any]:
    """
    Genera serie histórica del índice LATAM SIN forward fill.
    - Usa únicamente fechas con datos reales para las 4 monedas (join interno)
    - No crea fechas adicionales ni rellena valores
    """
    print(f"📈 Generando serie histórica del índice LATAM ({days_back} días)...")
    
    # Ponderaciones por comercio exterior
    weights = {
        'USDMXN.FOREX': 0.35,  # México - 35%
        'USDBRL.FOREX': 0.30,  # Brasil - 30%
        'USDCOP.FOREX': 0.20,  # Colombia - 20%
        'USDPEN.FOREX': 0.15   # Perú - 15%
    }
    
    if dry_run:
        print("🧪 MODO DRY-RUN: No se insertará nada en Supabase")
    
    try:
        # Obtener datos históricos de todas las monedas
        currency_data = {}
        
        for ticker, weight in weights.items():
            print(f"🔍 Obteniendo datos históricos para {ticker}...")
            if start_date:
                df = _fetch_ohlcv_series_paginated(ticker, start_date)
            else:
                df = get_data_series(ticker, days=days_back)
            
            if df is not None and not df.empty:
                # Normalizar a DataFrame con índice fecha (date) y columna del ticker
                if 'close' in df.columns:
                    df = df[['close']].copy()
                    df.index = pd.to_datetime(df.index).date
                    df.rename(columns={'close': ticker}, inplace=True)
                else:
                    # Ya viene con columna renombrada en modo paginado
                    df.index = pd.to_datetime(df.index).date
                currency_data[ticker] = {'data': df, 'weight': weight}
                print(f"✅ {ticker}: {len(df)} registros históricos")
            else:
                print(f"❌ No hay datos históricos para {ticker}")
        
        if len(currency_data) != 4:
            print(f"❌ No se puede generar serie histórica: {len(currency_data)}/4 monedas")
            return {'error': 'insufficient_data'}
        
        # Calcular índice histórico solo en fechas comunes a las 4 series
        print("📊 Calculando índice histórico (sin forward fill)...")

        # Preparar dataframes por ticker con índice de fecha (sin hora) y columna renombrada
        dfs = []
        for ticker, data in currency_data.items():
            df_t = data['data'].copy()
            dfs.append(df_t)

        # Join interno para obtener solo fechas con las 4 monedas
        combined = dfs[0].join(dfs[1:], how='inner')
        combined = combined.sort_index().dropna(how='any')

        if combined.empty:
            print("❌ No hay fechas comunes entre las 4 series en el período solicitado")
            return {'error': 'no_common_dates'}

        # Pesos
        weights = {
            'USDMXN.FOREX': 0.35,
            'USDBRL.FOREX': 0.30,
            'USDCOP.FOREX': 0.20,
            'USDPEN.FOREX': 0.15,
        }

        weighted_values = (
            combined['USDMXN.FOREX'] * weights['USDMXN.FOREX'] +
            combined['USDBRL.FOREX'] * weights['USDBRL.FOREX'] +
            combined['USDCOP.FOREX'] * weights['USDCOP.FOREX'] +
            combined['USDPEN.FOREX'] * weights['USDPEN.FOREX']
        )

        historical_index = [
            {'timestamp': idx.isoformat(), 'value': float(val)}
            for idx, val in weighted_values.items() if pd.notna(val)
        ]
        
        print(f"✅ Índice histórico calculado: {len(historical_index)} puntos")
        
        if dry_run:
            print(f"🧪 [DRY-RUN] Se insertarían {len(historical_index)} registros históricos")
            return {'historical_points': len(historical_index)}
        else:
            # Insertar serie histórica
            return _insert_historical_series(historical_index)
    
    except Exception as e:
        print(f"❌ Error generando serie histórica: {e}")
        return {'error': str(e)}


def _insert_historical_series(historical_data: list) -> Dict[str, Any]:
    """
    Inserta la serie histórica del índice LATAM en Supabase.
    """
    try:
        # Obtener o crear la definición de serie
        series_id = _get_or_create_series_definition(
            ticker='latam_currency_index',
            description='Índice de Monedas LATAM (Ponderado por Comercio Exterior)'
        )
        
        if not series_id:
            return {'error': 'series_creation_failed'}
        
        # Preparar registros para inserción
        records_to_upsert = []
        for point in historical_data:
            record = {
                'series_id': series_id,
                'timestamp': point['timestamp'],
                'value': point['value'],
                'ticker': 'latam_currency_index'
            }
            records_to_upsert.append(record)
        
        print(f"📦 Preparando {len(records_to_upsert)} registros para inserción...")
        
        # Upsert en lotes para evitar límites de Supabase
        batch_size = 1000
        success_count = 0
        
        for i in range(0, len(records_to_upsert), batch_size):
            batch = records_to_upsert[i:i + batch_size]
            
            try:
                upsert_res = supabase.table('time_series_data').upsert(
                    batch,
                    on_conflict='series_id,timestamp'
                ).execute()
                
                if upsert_res.data:
                    success_count += len(batch)
                    print(f"   -> ✅ Lote {i//batch_size + 1}: {len(batch)} registros insertados")
                else:
                    print(f"   -> ❌ Error en lote {i//batch_size + 1}")
                    
            except Exception as e:
                print(f"   -> ❌ Error en lote {i//batch_size + 1}: {e}")
        
        print(f"🎉 Serie histórica insertada: {success_count}/{len(records_to_upsert)} registros")
        
        # Verificar cuántos registros realmente se insertaron
        try:
            verify_res = supabase.table('time_series_data').select('*', count='exact').eq('ticker', 'latam_currency_index').execute()
            actual_count = verify_res.count
            print(f"🔍 Verificación: {actual_count} registros encontrados en Supabase para 'latam_currency_index'")
        except Exception as e:
            print(f"⚠️ Error verificando registros: {e}")
            actual_count = None
        
        return {
            'success': True,
            'total_records': len(records_to_upsert),
            'inserted_records': success_count,
            'verified_count': actual_count
        }
        
    except Exception as e:
        print(f"❌ Error insertando serie histórica: {e}")
        return {'error': str(e)}


def verify_latam_index_data() -> Dict[str, Any]:
    """
    Verifica cuántos registros del índice LATAM hay en Supabase.
    """
    print("🔍 Verificando registros del índice LATAM en Supabase...")
    
    try:
        # Contar registros totales
        count_res = supabase.table('time_series_data').select('*', count='exact').eq('ticker', 'latam_currency_index').execute()
        total_count = count_res.count
        
        # Obtener algunos registros de muestra
        sample_res = supabase.table('time_series_data').select('timestamp,value').eq('ticker', 'latam_currency_index').order('timestamp', desc=True).limit(5).execute()
        
        print(f"📊 Total de registros: {total_count}")
        print(f"📅 Últimos 5 registros:")
        for record in sample_res.data:
            print(f"   {record['timestamp']}: {record['value']:.4f}")
        
        # Verificar si hay más de 100 registros
        if total_count > 100:
            print(f"⚠️ NOTA: Supabase solo muestra 100 registros por consulta en la interfaz")
            print(f"   Pero el script confirma que hay {total_count} registros en total")
        
        return {
            'total_count': total_count,
            'sample_data': sample_res.data
        }
        
    except Exception as e:
        print(f"❌ Error verificando datos: {e}")
        return {'error': str(e)}


def get_all_latam_index_records() -> Dict[str, Any]:
    """
    Obtiene TODOS los registros del índice LATAM sin límite de 100.
    """
    print("🔍 Obteniendo TODOS los registros del índice LATAM...")
    
    try:
        # Obtener todos los registros usando paginación
        all_records = []
        page_size = 1000
        offset = 0
        
        while True:
            batch_res = supabase.table('time_series_data').select('timestamp,value').eq('ticker', 'latam_currency_index').order('timestamp', desc=True).range(offset, offset + page_size - 1).execute()
            
            if not batch_res.data:
                break
                
            all_records.extend(batch_res.data)
            offset += page_size
            
            if len(batch_res.data) < page_size:
                break
        
        print(f"📊 Total de registros obtenidos: {len(all_records)}")
        print(f"📅 Rango de fechas:")
        if all_records:
            print(f"   Más reciente: {all_records[0]['timestamp']}")
            print(f"   Más antiguo: {all_records[-1]['timestamp']}")
        
        return {
            'total_records': len(all_records),
            'all_records': all_records
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo todos los registros: {e}")
        return {'error': str(e)}


def _debug_fetch_ticker(ticker: str, start_date: str | None = None, days_back: int | None = None) -> Dict[str, Any]:
    """
    Diagnóstico: intenta obtener histórico usando get_data_series y consulta directa a market_data_ohlcv (paginada).
    """
    print("\n🔎 DEBUG FETCH TICKER")
    print(f"   Ticker: {ticker}")
    print(f"   start_date: {start_date}")
    print(f"   days_back: {days_back}")

    result: Dict[str, Any] = {'ticker': ticker}

    # 1) Vía get_data_series (buscador universal)
    try:
        if days_back is None and start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                days_back = (datetime.now() - start_dt).days
            except Exception:
                days_back = 3650
        if days_back is None:
            days_back = 3650

        df = get_data_series(ticker, days=days_back)
        if df is not None and not df.empty:
            first_dt = df.index[0]
            last_dt = df.index[-1]
            result['get_data_series'] = {
                'rows': int(len(df)),
                'first_date': str(first_dt),
                'last_date': str(last_dt),
                'columns': list(df.columns)
            }
            print(f"   -> get_data_series OK: {len(df)} filas | {first_dt} → {last_dt}")
        else:
            result['get_data_series'] = {'rows': 0}
            print("   -> get_data_series: sin filas")
    except Exception as e:
        result['get_data_series'] = {'error': str(e)}
        print(f"   -> get_data_series error: {e}")

    # 2) Vía consulta directa a market_data_ohlcv (paginada)
    try:
        page_size = 1000
        offset = 0
        total = 0
        first_seen = None
        last_seen = None
        # intentar eq exacto primero
        while True:
            q = supabase.table('market_data_ohlcv').select('timestamp,close')
            if start_date:
                q = q.gte('timestamp', start_date)
                res = q.eq('ticker', ticker).order('timestamp', desc=False).range(offset, offset + page_size - 1).execute()
            rows = res.data or []
            if not rows:
                break
            if first_seen is None:
                first_seen = rows[0]['timestamp']
            last_seen = rows[-1]['timestamp']
            total += len(rows)
            if len(rows) < page_size:
                break
            offset += page_size

        if total == 0:
            # intentar ilike con comodines
            offset = 0
            while True:
                q = supabase.table('market_data_ohlcv').select('timestamp,close,ticker')
                if start_date:
                    q = q.gte('timestamp', start_date)
                res = q.ilike('ticker', f"%{ticker}%").order('timestamp', desc=False).range(offset, offset + page_size - 1).execute()
                rows = res.data or []
                if not rows:
                    break
                if first_seen is None:
                    first_seen = rows[0]['timestamp']
                last_seen = rows[-1]['timestamp']
                total += len(rows)
                if len(rows) < page_size:
                    break
                offset += page_size

        result['market_data_ohlcv'] = {
            'rows': total,
            'first_date': first_seen,
            'last_date': last_seen
        }
        print(f"   -> market_data_ohlcv: {total} filas | {first_seen} → {last_seen}")
    except Exception as e:
        result['market_data_ohlcv'] = {'error': str(e)}
        print(f"   -> market_data_ohlcv error: {e}")

    return result

if __name__ == '__main__':
    import sys
    dry_run = '--dry-run' in sys.argv
    verify_all = '--verify-all' in sys.argv
    # Permite especificar fecha de inicio para serie histórica (sin forward fill)
    start_arg = None
    test_fetch_arg = None
    for arg in sys.argv:
        if arg.startswith('--start='):
            start_arg = arg.split('=', 1)[1].strip()
        if arg.startswith('--test-fetch='):
            test_fetch_arg = arg.split('=', 1)[1].strip()
    
    if verify_all:
        print("🔍 VERIFICACIÓN COMPLETA DE REGISTROS...")
        print("="*60)
        try:
            all_records = get_all_latam_index_records()
            print(f"📋 Resultado: {all_records}")
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
        print("="*60)
        print("🎉 VERIFICACIÓN COMPLETADA")
        exit()
    
    print("🚀 Ejecutando benchmarks...")
    print("="*60)
    
    # BTP Benchmarks (renta fija)
    print("📊 BTP BENCHMARKS (Renta Fija):")
    try:
        btp_results = sync_btp_benchmarks(dry_run=dry_run)
        print(f"📋 BTP Resumen: {btp_results}")
    except Exception as e:
        print(f"❌ Error ejecutando benchmarks BTP: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    
    # LATAM Currency Index (punto actual)
    print("🌎 LATAM CURRENCY INDEX (Punto Actual):")
    try:
        latam_results = sync_latam_currency_index(dry_run=dry_run)
        print(f"📋 LATAM Resumen: {latam_results}")
    except Exception as e:
        print(f"❌ Error ejecutando índice LATAM: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    
    # (OPCIONAL) TEST FETCH TICKER
    if test_fetch_arg:
        print("\n" + "="*60)
        print("🧪 TEST FETCH TICKER:")
        try:
            # days_back se calculará desde start si existe
            tf = _debug_fetch_ticker(test_fetch_arg, start_date=start_arg)
            print(f"📋 Test Fetch Resultado: {tf}")
        except Exception as e:
            print(f"❌ Error en test fetch: {e}")

    # LATAM Currency Index (serie histórica): se mueve a script separado
    if start_arg:
        print("📎 Nota: Para reconstruir histórico, usa:")
        print("   python -m quantex.pipelines.price_ingestor.latam_currency_index_historical --start=YYYY-MM-DD [--dry-run]")
    
    print("\n" + "="*60)
    
    # Verificación de datos insertados
    print("🔍 VERIFICACIÓN DE DATOS:")
    try:
        verify_results = verify_latam_index_data()
        print(f"📋 Verificación Resumen: {verify_results}")
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
    
    print("\n" + "="*60)
    print("🎉 BENCHMARKS COMPLETADOS")
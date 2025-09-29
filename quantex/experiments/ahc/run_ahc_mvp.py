import os
import sys
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, LogLocator
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client


CUTOFF_DATE_STR = None  # None => hasta hoy


def _get_supabase_client() -> Client | None:
    # Intentar cargar .env desde múltiples ubicaciones y también desde el entorno actual
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')),
        os.path.abspath(os.path.join(os.getcwd(), 'quantex', '.env')),
        os.path.abspath(os.path.join(os.getcwd(), '.env')),
    ]
    for p in candidates:
        if os.path.exists(p):
            load_dotenv(dotenv_path=p)
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Variables de entorno de Supabase no encontradas. Configure SUPABASE_URL y SUPABASE_SERVICE_KEY.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Error creando cliente de Supabase: {e}")
        return None


def _fetch_by_date_chunks(sb: Client, identifier: str, start_date: datetime, end_date: datetime, cols: str) -> list:
    """Consulta por tramos de fechas (ej. 365 días) para evitar el límite de 1000 filas por request."""
    rows_all = []
    chunk_days = 365
    cursor = start_date
    while cursor < end_date:
        next_cut = min(cursor + timedelta(days=chunk_days), end_date)
        try:
            resp = sb.table('market_data_ohlcv').select(cols) \
                .eq('ticker', identifier) \
                .gte('timestamp', cursor.strftime('%Y-%m-%d')) \
                .lt('timestamp', next_cut.strftime('%Y-%m-%d')) \
                .order('timestamp', desc=False) \
                .limit(2000) \
                .execute()
            rows = resp.data or []
            if rows:
                rows_all.extend(rows)
        except Exception as e:
            print(f"Aviso: fallo tramo {cursor.date()} - {next_cut.date()}: {e}")
        cursor = next_cut
    return rows_all


def fetch_ohlcv(identifier: str, days: int) -> pd.DataFrame | None:
    sb = _get_supabase_client()
    if not sb:
        return None

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_date_str = start_date.strftime('%Y-%m-%d')

    # Intento 1: por tramos solo 'close'
    rows = _fetch_by_date_chunks(sb, identifier, start_date, end_date, 'timestamp, close')
    if rows:
        df = pd.DataFrame(rows)
        df.rename(columns={'timestamp': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        # Consolidar duplicados si los hubiera (promedio o último)
        df = df[~df.index.duplicated(keep='last')]
        return df[['close']]

    # Intento 2: por tramos OHLCV completo
    rows = _fetch_by_date_chunks(sb, identifier, start_date, end_date, 'timestamp, open, high, low, close, volume')
    if rows:
        df = pd.DataFrame(rows)
        df.rename(columns={'timestamp': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        df = df[~df.index.duplicated(keep='last')]
        return df[['open', 'high', 'low', 'close', 'volume']]

    print(f"No se encontraron datos para '{identifier}'.")
    return None


def generate_log_chart(identifier: str, years: int = 20, cutoff_date_str: str | None = CUTOFF_DATE_STR, output_filename: str | None = None, inflection_points: list = None, start_date_str: str | None = None) -> str | None:
    days = int(years * 365 + 30)
    df = fetch_ohlcv(identifier, days)
    if df is None or df.empty or 'close' not in df.columns:
        print(f"No se pudo obtener datos para '{identifier}'.")
        return None

    # Filtro opcional por inicio
    if start_date_str:
        start_date = pd.to_datetime(start_date_str)
        df = df[df.index >= start_date]
        if df.empty:
            print(f"No hay datos posteriores a {start_date_str} para '{identifier}'.")
            return None

    # Recorte opcional por cutoff (si se entrega). Si es None, graficamos hasta hoy.
    if cutoff_date_str:
        cutoff_date = pd.to_datetime(cutoff_date_str)
        df = df[df.index < cutoff_date]
        if df.empty:
            print(f"No hay datos anteriores a {cutoff_date_str} para '{identifier}'.")
            return None

    outputs_dir = os.path.join("quantex", "experiments", "ahc")
    os.makedirs(outputs_dir, exist_ok=True)
    if not output_filename:
        output_filename = f"ahc_log_{identifier.replace('/', '_').replace('^','')}.png"
    out_path = os.path.join(outputs_dir, output_filename)

    plt.figure(figsize=(20, 6))
    ax = plt.gca()

    # Solo cierre
    plt.plot(df.index, df['close'], color="#1f77b4", linewidth=1.5)
    ax.set_yscale('log')

    # Agregar líneas verticales para puntos de inflexión si se proporcionan
    if inflection_points:
        for i, point in enumerate(inflection_points, 1):
            try:
                event_date = pd.to_datetime(point['date'])
                if event_date in df.index:
                    # Línea vertical
                    plt.axvline(x=event_date, color='red', linestyle='--', alpha=0.7, linewidth=1)
                    # Número del evento
                    plt.text(event_date, df['close'].max() * 0.95, str(i),
                            ha='center', va='top', fontsize=8, fontweight='bold',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7))
            except Exception as e:
                print(f"Error procesando punto de inflexión {i}: {e}")
                continue

    # Forzar etiquetas numéricas legibles en eje Y (sin notación científica)
    formatter = ScalarFormatter(useMathText=False)
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)
    ax.yaxis.set_minor_formatter(formatter)

    # Ubicación de ticks (automática, pero con locators razonables)
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=10))

    title_suffix = []
    if start_date_str:
        title_suffix.append(f"desde {start_date_str}")
    title_suffix.append(f"hasta {cutoff_date_str}" if cutoff_date_str else "hasta hoy")
    plt.title(f"{identifier} — Escala Logarítmica ({', '.join(title_suffix)})")
    plt.xlabel("Fecha")
    plt.ylabel("Precio (log)")
    plt.grid(True, which='both', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    print(f"Grafico guardado en: {out_path}")
    return out_path


if __name__ == "__main__":
    identifier = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AHC_IDENTIFIER", "SPX")
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    cutoff = sys.argv[3] if len(sys.argv) > 3 else CUTOFF_DATE_STR
    start = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("AHC_START_DATE")
    generate_log_chart(identifier=identifier, years=years, cutoff_date_str=cutoff, start_date_str=start)

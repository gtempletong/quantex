# El Auditor de Datos. La herramienta de monitoreo que creamos para revisar la salud de tus datos y generar el reporte HTML.

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.database_manager import supabase

def audit_series(table_name: str, ticker_col: str, ticker_value: str, date_col: str, value_col: str, display_name: str | None = None):
    """
    Audita los últimos 800 registros de una única serie de tiempo.
    """
    name_to_show = display_name or ticker_value
    result = {
        "table": table_name,
        "name": name_to_show,
        "status": "✅ OK",
        "date_range": "N/A",
        "records": 0,
        "nulls": 0,
        "gaps": 0
    }

    try:
        data_res = supabase.table(table_name).select(f"{date_col}, {value_col}") \
            .eq(ticker_col, ticker_value) \
            .order(date_col, desc=True) \
            .limit(800) \
            .execute()

        if not data_res.data:
            result["status"] = "🟡 Advertencia"
            result["date_range"] = "Sin datos"
            return result

        df = pd.DataFrame(data_res.data).sort_values(by=date_col, ascending=True)
        df[date_col] = pd.to_datetime(df[date_col]).dt.tz_localize(None)

        min_date, max_date, total_records = df[date_col].min(), df[date_col].max(), len(df)
        result["date_range"] = f"{min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')}"
        result["records"] = total_records

        null_values = df[value_col].isnull().sum()
        result["nulls"] = int(null_values)
        if null_values > 0:
            result["status"] = "🟡 Advertencia"
        
        if max_date < (datetime.now() - timedelta(days=5)):
            result["status"] = "🟡 Advertencia"

        missing_dates = pd.date_range(start=min_date, end=max_date, freq='B').difference(df[date_col])
        result["gaps"] = len(missing_dates)
        if not missing_dates.empty:
            result["status"] = "🚨 Crítico"
            
    except Exception as e:
        result["status"] = "❌ Error"
        result["date_range"] = str(e)

    return result

def generate_html_report(audit_results: list):
    """
    Toma una lista de resultados de auditoría y genera un reporte HTML.
    """
    print(" -> 📄 Generando reporte HTML...")
    
    status_styles = {
        "✅ OK": "style='background-color: #28a745; color: white;'",
        "🟡 Advertencia": "style='background-color: #ffc107; color: black;'",
        "🚨 Crítico": "style='background-color: #dc3545; color: white;'",
        "❌ Error": "style='background-color: #6c757d; color: white;'"
    }

    rows_html = ""
    # Ordenamos los resultados para una mejor visualización
    sorted_results = sorted(audit_results, key=lambda x: (x['table'], x['name']))

    for r in sorted_results:
        style = status_styles.get(r['status'], "")
        rows_html += f"""
        <tr>
            <td {style}>{r['status']}</td>
            <td>{r['name']}</td>
            <td>{r['table']}</td>
            <td>{r['date_range']}</td>
            <td>{r['records']}</td>
            <td>{r['gaps']}</td>
            <td>{r['nulls']}</td>
        </tr>
        """

    html_template = f"""
    <html>
    <head>
        <title>Reporte de Auditoría de Datos Quantex</title>
        <style>
            body {{ font-family: sans-serif; background-color: #1a1a1a; color: #e0e0e0; padding: 20px; }}
            h1 {{ color: #007BFF; border-bottom: 2px solid #007BFF; padding-bottom: 10px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 0.9em; }}
            th, td {{ border: 1px solid #444; padding: 10px; text-align: left; }}
            th {{ background-color: #007BFF; color: white; }}
            tr:nth-child(even) {{ background-color: #2c2c2c; }}
        </style>
    </head>
    <body>
        <h1>🩺 Reporte de Salud de Datos Quantex</h1>
        <p>Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <table>
            <tr>
                <th>Estado</th>
                <th>Activo / Serie</th>
                <th>Tabla</th>
                <th>Rango de Fechas</th>
                <th>Registros</th>
                <th>Gaps (Días Faltantes)</th>
                <th>Valores Nulos</th>
            </tr>
            {rows_html}
        </table>
    </body>
    </html>
    """
    
    report_filename = "auditoria_de_datos.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"\n--- ✅ Reporte Finalizado. Abre el archivo '{report_filename}' en tu navegador. ---")


def main():
    print("--- 🩺 Iniciando Auditoría de Datos de Quantex (Modo Rápido: 800 registros) ---")
    if not supabase: return

    all_audit_results = []
    
    # 1. Auditar market_data_ohlcv
    defs_res = supabase.table('instrument_definitions').select('ticker').eq('is_active', True).execute()
    if defs_res.data:
        for item in defs_res.data:
            result = audit_series('market_data_ohlcv', 'ticker', item['ticker'], 'timestamp', 'close')
            all_audit_results.append(result)
    
    # 2. Auditar fixed_income_trades
    defs_res = supabase.table('fixed_income_definitions').select('name').execute()
    if defs_res.data:
        for item in defs_res.data:
            result = audit_series('fixed_income_trades', 'instrument_name', item['name'], 'trade_date', 'average_yield')
            all_audit_results.append(result)

    # 3. Auditar time_series_data
    # --- INICIO DE LA CORRECCIÓN ---
    # Ahora pedimos el id y el ticker para usar el ticker en el reporte
    defs_res = supabase.table('series_definitions').select('id, ticker').execute()
    if defs_res.data:
        series_map = {item['id']: item['ticker'] for item in defs_res.data if item.get('ticker')}
        print(f" -> Encontradas {len(series_map)} series en la tabla de definiciones.")
        for series_id, ticker_name in series_map.items():
            result = audit_series(
                table_name='time_series_data', 
                ticker_col='series_id', 
                ticker_value=series_id, 
                date_col='timestamp', 
                value_col='value',
                display_name=ticker_name # <--- Le pasamos el ticker como nombre descriptivo
            )
            all_audit_results.append(result)
    # --- FIN DE LA CORRECCIÓN ---
    
    generate_html_report(all_audit_results)


if __name__ == "__main__":
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    main()
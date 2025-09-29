# quantex/price_pipeline/price_ingestor/carga_historicos_bloomberg.py (Versión con Mapeo Inteligente)

import os
import sys
import pandas as pd
from dotenv import load_dotenv
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.database_manager import supabase
from quantex.config import Config

# --- CONFIGURACIÓN ---
GOOGLE_SHEET_NAME = "Bloomberg Supabase Data.xlsx"
TAB_NAME = "carga_supabase"
# ---------------------

def load_data_from_gsheet(sheet_name: str, tab_name: str, drive_service) -> pd.DataFrame | None:
    print(f"  -> 📄 Leyendo la pestaña '{tab_name}' de '{sheet_name}'...")
    try:
        files = drive_service.files().list(q=f"name = '{sheet_name}' and trashed = false", fields='files(id)').execute().get('files', [])
        if not files:
            raise FileNotFoundError(f"No se encontró el archivo '{sheet_name}' en Google Drive.")
        
        request = drive_service.files().get_media(fileId=files[0]['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        df = pd.read_excel(fh, sheet_name=tab_name, engine='openpyxl')
        
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        date_col = df.columns[0]
        df.rename(columns={date_col: 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"     ✅ Se leyeron {len(df)} filas y {len(df.columns)} columnas.")
        return df
        
    except Exception as e:
        print(f"     ❌ Error leyendo Google Sheet: {e}")
        return None

def main():
    print("--- 🚀 Iniciando Carga Masiva de Datos Históricos ---")
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    
    # ✅ SEGURO: Obtener scopes desde configuración
    SCOPES = [Config.get_google_drive_scopes()]
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    print("\n--- Creando mapa maestro de activos desde Supabase ---")
    master_map = {}
    
    # Renta Variable (sigue usando 'ticker')
    res = supabase.table('instrument_definitions').select('ticker').execute()
    if res.data:
        for item in res.data: master_map[item['ticker']] = {'table': 'market_data_ohlcv', 'type': 'ohlcv'}
        
    # Renta Fija (sigue usando 'name')
    res = supabase.table('fixed_income_definitions').select('id, name').execute()
    if res.data:
        fi_map = {item['name']: item['id'] for item in res.data}
        for name in fi_map: master_map[name] = {'table': 'fixed_income_trades', 'type': 'fi', 'id': fi_map[name]}

    # --- INICIO DE LA CORRECCIÓN ---
    # Time Series (ahora usa 'source_sheet_header' como la clave del mapa)
    res = supabase.table('series_definitions').select('id, ticker, source_sheet_header').execute()
    if res.data:
        for item in res.data:
            if item.get('source_sheet_header'):
                master_map[item['source_sheet_header']] = {
                    'table': 'time_series_data',
                    'type': 'ts',
                    'id': item['id'],
                    'ticker': item['ticker'] # Guardamos el ticker para usarlo después
                }
    # --- FIN DE LA CORRECCIÓN ---

    print(f" -> ✅ Mapa maestro creado con {len(master_map)} activos.")
    
    df_source = load_data_from_gsheet(GOOGLE_SHEET_NAME, TAB_NAME, drive_service)
    if df_source is None:
        return

    print("\n--- Procesando y enrutando datos a sus tablas de destino ---")
    for column_header in df_source.columns:
        if column_header == 'timestamp': continue

        destination_info = master_map.get(column_header)
        if not destination_info:
            print(f" -> 🟡 Advertencia: El encabezado '{column_header}' del Google Sheet no fue encontrado en el mapa maestro. Se omitirá.")
            continue
            
        print(f" -> Procesando '{column_header}' para la tabla '{destination_info['table']}'...")
        
        df_long = df_source[['timestamp', column_header]].copy()
        df_long[column_header] = pd.to_numeric(df_long[column_header], errors='coerce')
        df_long.dropna(subset=[column_header], inplace=True)
        
        if df_long.empty:
            print(f"    -> ℹ️ No hay datos válidos para '{column_header}' después de la limpieza.")
            continue

        records = []
        on_conflict_key = ''
        
        if destination_info['type'] == 'ohlcv':
            df_long.rename(columns={column_header: 'close'}, inplace=True)
            df_long['ticker'] = column_header
            df_long['open'] = df_long['high'] = df_long['low'] = df_long['close']
            df_long['volume'] = 0
            df_long['source'] = 'bloomberg_historical'
            df_long['timestamp'] = df_long['timestamp'].dt.strftime('%Y-%m-%d')
            records = df_long.to_dict('records')
            on_conflict_key = 'timestamp,ticker'
            
        elif destination_info['type'] == 'fi':
            df_long.rename(columns={'timestamp': 'trade_date', column_header: 'average_yield'}, inplace=True)
            df_long['instrument_name'] = column_header
            df_long['instrument_id'] = destination_info['id']
            df_long['quantity'] = df_long['amount_clp'] = df_long['closing_price_percent'] = 0
            df_long['trade_date'] = df_long['trade_date'].dt.strftime('%Y-%m-%d')
            records = df_long.to_dict('records')
            on_conflict_key = 'instrument_id,trade_date'

        elif destination_info['type'] == 'ts':
            df_long.rename(columns={column_header: 'value'}, inplace=True)
            df_long['series_id'] = destination_info['id']
            df_long['ticker'] = destination_info['ticker'] # Usamos el ticker guardado del mapa
            df_long['timestamp'] = df_long['timestamp'].dt.strftime('%Y-%m-%d')
            records = df_long.to_dict('records')
            on_conflict_key = 'series_id,timestamp'

        if records:
            print(f"    -> 📦 Preparados {len(records)} registros limpios. Guardando en Supabase...")
            supabase.table(destination_info['table']).upsert(records, on_conflict=on_conflict_key).execute()
            print("    -> ✅ Datos guardados.")

    print("\n--- 🎉 Carga Masiva Completada ---")

if __name__ == "__main__":
    main()
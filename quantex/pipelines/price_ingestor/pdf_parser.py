#El Ingestor de Renta Fija Local. El script que lee los boletines en PDF de la Bolsa de Santiago. Lo acabamos de arreglar.

import os
import fitz  # PyMuPDF
import pandas as pd
import re
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

from quantex.core.database_manager import upsert_fixed_income_trades

# --- 1. CONEXIÓN A SUPABASE ---
try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Conexión a Supabase inicializada exitosamente.")
except Exception as e:
    print(f"❌ ERROR al inicializar el cliente de Supabase: {e}")
    supabase = None

# --- 2. FUNCIONES DE PARSEO DE PDF ---

def clean_numeric_value(value: str) -> float | None:
    if not isinstance(value, str) or not value.strip(): return None
    try:
        return float(value.replace('.', '').replace(',', '.'))
    except (ValueError, TypeError): return None

def extract_date_from_page(page: fitz.Page) -> str | None:
    text = page.get_text("text")
    match = re.search(r'\w+\s+(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', text, re.IGNORECASE)
    if match:
        day, month_str, year = match.groups()
        # --- INICIO DE LA CORRECCIÓN ---
        # Mapa de meses completo en español
        month_map = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
            'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
            'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        # --- FIN DE LA CORRECCIÓN ---
        month = month_map.get(month_str.upper())
        if month:
            return datetime(int(year), month, int(day)).strftime('%Y-%m-%d')
    return None

# --- INICIO DE LA NUEVA LÓGICA ---
def find_table_start_page(doc: fitz.Document, search_text: str) -> int | None:
    """Busca en el documento la primera página que contiene un texto específico."""
    print(f"🔎 Buscando la página de inicio de la tabla con el texto: '{search_text}'...")
    for page in doc:
        if page.search_for(search_text):
            print(f"  -> ✅ Tabla encontrada en la página: {page.number + 1}")
            return page.number
    print(f"  -> ❌ No se encontró la página con el texto de búsqueda.")
    return None
# --- FIN DE LA NUEVA LÓGICA ---

def parse_bcs_fixed_income(pdf_path: str) -> tuple[pd.DataFrame | None, str | None]:
    print(f"📄 Procesando el archivo: {pdf_path}")
    doc = fitz.open(pdf_path)
    all_data_rows = []
    trade_date = None

    # --- INICIO DEL CAMBIO PRINCIPAL ---
    # Ya no usamos [63, 64]. Ahora buscamos la página dinámicamente.
    start_page = find_table_start_page(doc, "Resumen de Transacciones Mercado Renta Fija")
    
    if start_page is None:
        return None, None

    # Asumimos que la tabla puede extenderse a la página siguiente
    pages_to_process = range(start_page, min(start_page + 3, len(doc)))
    # --- FIN DEL CAMBIO PRINCIPAL ---

    for page_num in pages_to_process:
        print(f"  -> Leyendo página {page_num + 1}...")
        page = doc[page_num]
        
        if not trade_date:
            trade_date = extract_date_from_page(page)
            print(f"📅 Fecha extraída del documento: {trade_date or 'No encontrada'}")

        pattern = re.compile(r"^(\S+)\s+(\S+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+(-?[\d,\.]+)$")
        
        blocks = page.get_text("blocks")
        for block in blocks:
            text = block[4].strip()
            match = pattern.match(text)
            if match:
                all_data_rows.append(list(match.groups()))

    if not all_data_rows:
        print("❌ No se encontraron datos de transacciones en el PDF.")
        return None, None
        
    df = pd.DataFrame(all_data_rows, columns=['Nemo', 'Plazo', 'Cantidad', 'Monto_Transado', 'Precio_Mayor', 'Precio_Menor', 'Precio_Medio', 'Precio_Cierre', 'TIR_Media'])
    
    # Limpiar solo las columnas numéricas, preservando Nemo y Plazo como strings
    numeric_cols = ['Cantidad', 'Monto_Transado', 'Precio_Mayor', 'Precio_Menor', 'Precio_Medio', 'Precio_Cierre', 'TIR_Media']
    for col in numeric_cols:
        df[col] = df[col].apply(clean_numeric_value)
    
    # Limpiar Nemo (ticker) - solo remover espacios en blanco
    df['Nemo'] = df['Nemo'].astype(str).str.strip()
        
    df.dropna(how='all', inplace=True)
    print(f"✅ PDF parseado. Se encontraron {len(df)} registros limpios en total.")
    return df, trade_date

# --- LÓGICA DE PROCESAMIENTO Y GUARDADO (SIN CAMBIOS) ---

def get_instrument_map(tickers: list) -> dict:
    print(f"🔍 Buscando información para {len(tickers)} instrumentos en la base de datos...")
    try:
        # CORRECCIÓN: Apuntar a la tabla correcta 'fixed_income_definitions'
        response = supabase.table('fixed_income_definitions').select('id, ticker, name').in_('ticker', tickers).execute()
        if response.data:
            instrument_map = {item['ticker']: {'id': item['id'], 'name': item['name']} for item in response.data}
            print(f"  -> ✅ Se encontró información para {len(instrument_map)} instrumentos.")
            return instrument_map
    except Exception as e:
        print(f"  -> ❌ Error al buscar instrumentos: {e}")
    return {}

def process_and_save_data(trades_df: pd.DataFrame, trade_date: str, instrument_map: dict):
    records_to_upsert = []
    missing_instruments = []

    for _, row in trades_df.iterrows():
        nemo = row['Nemo']
        instrument_info = instrument_map.get(nemo)

        if instrument_info:
            record = {
                'instrument_id': instrument_info['id'],
                'instrument_name': instrument_info['name'],
                'trade_date': trade_date,
                'quantity': int(row['Cantidad']),
                'amount_clp': row['Monto_Transado'],
                'closing_price_percent': row['Precio_Cierre'],
                'average_yield': row['TIR_Media']
            }
            records_to_upsert.append(record)
        else:
            missing_instruments.append(nemo)
    
    if missing_instruments:
        print(f"\n⚠️ ADVERTENCIA: No se procesarán los siguientes instrumentos por no estar en la BD: {len(set(missing_instruments))} tickers.")

    trades_df['Instrumento'] = trades_df['Nemo'].map(lambda n: instrument_map.get(n, {}).get('name', 'DESCONOCIDO'))

    upsert_fixed_income_trades(records_to_upsert)

# --- ORQUESTADOR PRINCIPAL (SIN CAMBIOS) ---

if __name__ == '__main__':
    if not supabase:
        print("🔴 Finalizando script debido a un error de conexión con Supabase.")
    else:
        date_input = input("➡️  Por favor, ingresa la fecha del boletín (formato ddmmaa, ej: 210825): ")
        pdf_file_name = f"ibd{date_input}.pdf"
        pdf_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), pdf_file_name)

        if not os.path.exists(pdf_file_path):
            print(f"❌ ERROR: No se encontró el archivo '{pdf_file_name}'.")
        else:
            # --- PASO 1: PROCESAR TRANSACCIONES DEL DÍA ---
            trades_today_df, trade_date = parse_bcs_fixed_income(pdf_file_path)
            if trades_today_df is None or trades_today_df.empty:
                print("No se encontraron transacciones en el PDF de hoy. El proceso terminará.")
                exit()
            
            print(f"\n--- 🏦 Lógica de Relleno de Precios ---")
            
            # --- PASO 2: IDENTIFICAR EL UNIVERSO DE BONOS (SOLO PDF_PARSER) ---
            all_rf_instruments_res = supabase.table('fixed_income_definitions').select('id, ticker, name').eq('data_source', 'pdf_parser').execute()
            all_rf_instruments = all_rf_instruments_res.data or []
            instrument_universe_map = {item['ticker']: {'id': item['id'], 'name': item['name']} for item in all_rf_instruments}
            
            # --- PASO 3: ENCONTRAR LOS "BONOS SILENCIOSOS" ---
            tickers_traded_today = set(trades_today_df['Nemo'].unique())
            all_rf_tickers = set(instrument_universe_map.keys())
            missing_tickers = all_rf_tickers - tickers_traded_today
            
            records_to_upsert = []

            # --- PASO 4 (A): PREPARAR REGISTROS DE BONOS QUE SÍ TRANSARON ---
            for _, row in trades_today_df.iterrows():
                instrument_info = instrument_universe_map.get(row['Nemo'])
                if instrument_info:
                    records_to_upsert.append({
                        'instrument_id': instrument_info['id'], 'instrument_name': instrument_info['name'], 'ticker': row['Nemo'],
                        'trade_date': trade_date, 'quantity': int(row['Cantidad']),
                        'amount_clp': row['Monto_Transado'], 'closing_price_percent': row['Precio_Cierre'],
                        'average_yield': row['TIR_Media']
                    })

            # --- PASO 4 (B): BUSCAR ÚLTIMO PRECIO Y RELLENAR (LÓGICA SIMPLIFICADA) ---
            if missing_tickers:
                print(f"🔍 Buscando el último precio para {len(missing_tickers)} instrumentos que no transaron hoy...")
                for ticker in missing_tickers:
                    instrument_info = instrument_universe_map.get(ticker)
                    if not instrument_info: continue

                    # Hacemos una consulta simple para cada bono que falta
                    response = supabase.table('fixed_income_trades') \
                        .select('closing_price_percent, average_yield') \
                        .eq('instrument_id', instrument_info['id']) \
                        .order('trade_date', desc=True) \
                        .limit(1) \
                        .maybe_single() \
                        .execute()

                    last_trade_info = response.data
                    if last_trade_info:
                        records_to_upsert.append({
                            'instrument_id': instrument_info['id'], 'instrument_name': instrument_info['name'], 'ticker': ticker,
                            'trade_date': trade_date,
                            'quantity': 0,
                            'amount_clp': 0,
                            'closing_price_percent': last_trade_info['closing_price_percent'],
                            'average_yield': last_trade_info['average_yield']
                        })
                print(f"  -> ✅ Búsqueda de precios anteriores completada.")

            # --- PASO 5: GUARDAR TODO EN SUPABASE ---
            if records_to_upsert:
                print(f"\n💾 Total de registros a guardar (transados + arrastrados): {len(records_to_upsert)}")
                upsert_fixed_income_trades(records_to_upsert)
            else:
                print("\n🟡 No se prepararon registros para guardar.")
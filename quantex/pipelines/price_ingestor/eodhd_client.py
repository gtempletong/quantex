# quantex/pipelines/price_ingestor/eodhd_client.py

import os
import sys
import time
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from quantex.core.database_manager import upsert_fixed_income_trades
from quantex.config import Config

# --- Configuración de Rutas y Conexión ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Importamos el cliente de Supabase
from quantex.core.database_manager import supabase

# ==============================================================================
# LÓGICA DE SINCRONIZACIÓN OHLCV (VERSIÓN INTELIGENTE Y AUTOMÁTICA)
# ==============================================================================

def sync_eodhd_data_to_supabase():
    """
    Obtiene y guarda datos OHLCV desde EODHD.
    Automáticamente detecta si debe hacer una carga histórica completa (si el ticker es nuevo)
    o una actualización incremental de 7 días (si el ticker ya tiene datos).
    """
    TABLE_NAME = "market_data_ohlcv"
    SOURCE_NAME = "eodhd"
    API_KEY = os.environ.get("EODHD_API_KEY")
    
    print(f"--- 🚀 Iniciando Sincronización Inteligente desde {SOURCE_NAME} ---")

    if not supabase:
        print("❌ Error: No se pudo conectar con Supabase.")
        return
    if not API_KEY:
        print("❌ Error: La variable de entorno EODHD_API_KEY no está configurada.")
        return

    try:
        response = supabase.table('instrument_definitions').select('ticker').eq('data_source', SOURCE_NAME).eq('is_active', True).execute()
        tickers_to_sync = [item['ticker'] for item in response.data]
        
        if not tickers_to_sync:
            print(f"-> 🟡 No se encontraron tickers activos para la fuente '{SOURCE_NAME}'.")
            return
            
        print(f"-> 🎯 Tickers a sincronizar: {tickers_to_sync}")
        
        for ticker in tickers_to_sync:
            sync_timestamp = datetime.now(timezone.utc)
            try:
                # --- LÓGICA INTELIGENTE: Detectar modo de carga ---
                check_res = supabase.table(TABLE_NAME).select('timestamp', count='exact').eq('ticker', ticker).limit(1).execute()
                record_count = check_res.count
                
                params = {
                    'api_token': API_KEY,
                    'fmt': 'json',
                    'period': 'd'
                }

                if record_count == 0:
                    print(f"  -> 🚚 Ticker nuevo detectado. Modo: Carga Histórica Completa para {ticker}...")
                else:
                    print(f"  -> 🔄 Ticker existente detectado. Modo: Actualización Incremental para {ticker}...")
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    params['from'] = start_date.strftime('%Y-%m-%d')
                    params['to'] = end_date.strftime('%Y-%m-%d')

                # ✅ SEGURO: Obtener URL desde configuración
                api_response = requests.get(f'{Config.get_eodhd_url()}/{ticker}', params=params)
                api_response.raise_for_status()
                data = api_response.json()

                if not data or not isinstance(data, list):
                    raise Exception(f"No se recibieron datos de la API para {ticker}.")

                records_to_upsert = []
                for row in data:
                    # Ignorar datos de fin de semana (sábado=5, domingo=6)
                    try:
                        row_date = datetime.strptime(row['date'], '%Y-%m-%d')
                        if row_date.weekday() >= 5:
                            continue
                    except Exception:
                        # Si hay algún problema parseando la fecha, no filtramos
                        pass

                    record = {
                        "timestamp": row['date'],
                        "ticker": ticker,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row.get('adjusted_close') or row['close']),
                        "volume": int(row['volume']),
                        "source": SOURCE_NAME
                    }
                    records_to_upsert.append(record)
                
                if records_to_upsert:
                    print(f"    -> Upsertando {len(records_to_upsert)} registros para {ticker}...")
                    supabase.table(TABLE_NAME).upsert(records_to_upsert, on_conflict='timestamp,ticker').execute()
                
                supabase.table('instrument_definitions').update({
                    'last_sync_status': 'success',
                    'last_sync_timestamp': sync_timestamp.isoformat()
                }).eq('ticker', ticker).execute()
                
                print(f"    -> ✅ Sincronización para {ticker} completada.")

            except Exception as e:
                print(f"    -> ❌ Error procesando {ticker}: {e}")
                supabase.table('instrument_definitions').update({
                    'last_sync_status': 'error',
                    'last_sync_timestamp': sync_timestamp.isoformat()
                }).eq('ticker', ticker).execute()
        
        print("\n--- 🎉 Sincronización Finalizada ---")

    except Exception as e:
        print(f"--- 💥 ERROR CRÍTICO en el script de sincronización EODHD: {e} ---")

if __name__ == "__main__":
    sync_eodhd_data_to_supabase()


# ==============================================================================
# MOTOR 2: SINCRONIZACIÓN DE YIELDS DE RENTA FIJA (VERSIÓN CORREGIDA)
# ==============================================================================
def sync_us_treasuries_yields():
    API_KEY = os.environ.get("EODHD_API_KEY")
    SOURCE_NAME = 'eodhd'
    
    print(f"--- 🏦 Iniciando Sincronización Inteligente de Yields desde {SOURCE_NAME} ---")

    if not supabase or not API_KEY:
        print("❌ Error: Falta la conexión a Supabase o la EODHD_API_KEY.")
        return

    try:
        response = supabase.table('fixed_income_definitions').select('id, ticker, name').eq('data_source', SOURCE_NAME).execute()
        instruments_to_sync = response.data
        
        if not instruments_to_sync:
            print(f"-> 🟡 No se encontraron instrumentos para la fuente '{SOURCE_NAME}'.")
            return
            
        print(f"-> 🎯 Instrumentos a sincronizar: {[item['ticker'] for item in instruments_to_sync]}")
        
        for instrument in instruments_to_sync:
            ticker = instrument['ticker']
            
            check_res = supabase.table('fixed_income_trades').select('trade_date', count='exact').eq('instrument_id', instrument['id']).limit(1).execute()
            record_count = check_res.count
            
            if record_count == 0:
                print(f"  -> 🚚 Ticker nuevo. Modo: Carga Histórica por Chunks para {ticker}...")
                
                total_records_upserted = 0
                current_year = datetime.now().year
                for year in range(current_year - 20, current_year + 1):
                    print(f"    -> 🗓️  Obteniendo datos para el año {year}...")
                    start_date, end_date = f"{year}-01-01", f"{year}-12-31"
                    
                    params = { 'api_token': API_KEY, 'fmt': 'json', 'period': 'd', 'from': start_date, 'to': end_date }
                    # ✅ SEGURO: Obtener URL desde configuración
                    api_response = requests.get(f'{Config.get_eodhd_url()}/{ticker}', params=params)
                    api_response.raise_for_status()
                    data = api_response.json()

                    if data and isinstance(data, list):
                        records_to_upsert = [{'instrument_id': instrument['id'], 'instrument_name': instrument['name'], 'ticker': instrument['ticker'], 'trade_date': row['date'], 'average_yield': row.get('adjusted_close') or row.get('close'), 'quantity': 0, 'amount_clp': 0, 'closing_price_percent': 0} for row in data]
                        
                        if records_to_upsert:
                            # --- INICIO DE LA CORRECCIÓN ---
                            upsert_fixed_income_trades(records_to_upsert)
                            # --- FIN DE LA CORRECCIÓN ---
                            total_records_upserted += len(records_to_upsert)
                        
                        time.sleep(0.5) 

                print(f"    -> Se guardaron un total de {total_records_upserted} registros históricos.")

            else:
                print(f"  -> 🔄 Ticker existente. Modo: Actualización Incremental para {ticker}...")
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                params = { 'api_token': API_KEY, 'fmt': 'json', 'period': 'd', 'from': start_date.strftime('%Y-%m-%d'), 'to': end_date.strftime('%Y-%m-%d')}
                
                # ✅ SEGURO: Obtener URL desde configuración
                api_response = requests.get(f'{Config.get_eodhd_url()}/{ticker}', params=params)
                api_response.raise_for_status()
                data = api_response.json()

                if data and isinstance(data, list):
                    records_to_upsert = [{'instrument_id': instrument['id'], 'instrument_name': instrument['name'], 'ticker': instrument['ticker'], 'trade_date': row['date'], 'average_yield': row.get('adjusted_close') or row.get('close'), 'quantity': 0, 'amount_clp': 0, 'closing_price_percent': 0} for row in data]
                    if records_to_upsert:
                        print(f"    -> Guardando {len(records_to_upsert)} registros...")
                        # --- INICIO DE LA CORRECCIÓN ---
                        upsert_fixed_income_trades(records_to_upsert)
                        # --- FIN DE LA CORRECCIÓN ---

            print(f"    -> ✅ Sincronización para {ticker} completada.")

        print("\n--- ✅ Sincronización de Yields de Bonos Finalizada ---")

    except Exception as e:
        print(f"--- 💥 ERROR CRÍTICO en la sincronización de yields: {e} ---")

if __name__ == "__main__":
    sync_us_treasuries_yields()
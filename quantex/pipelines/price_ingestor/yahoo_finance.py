# quantex/pipelines/price_ingestor/yahoo_finance.py

import os
import sys
import yfinance as yf
from datetime import datetime, timedelta, timezone # <-- IMPORTACIÓN CORREGIDA
from dotenv import load_dotenv
import pandas as pd
import json
from tqdm import tqdm
import pprint

# --- Configuración de Rutas y Conexión ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Importamos el cliente de Supabase
from quantex.core.database_manager import supabase

# ==============================================================================
# SECCIÓN 1: TU FUNCIÓN ORIGINAL (SE MANTIENE INTACTA)
# ==============================================================================

def get_yahoo_data_for_date(ticker: str, series_type: str, date: str | None = None) -> dict | None:
    """
    Obtiene datos de Yahoo Finance.
    - Para series_type='price', puede obtener el precio de cierre histórico.
    - Para series_type='pe_ratio', solo puede obtener el más reciente.
    """
    print(f"   -> [yahoo_client] Buscando {series_type} para {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        if date:
            # --- MODO HISTÓRICO ---
            print(f"      -> 🗓️  Buscando para fecha específica: {date}")
            if series_type == 'price':
                hist = stock.history(start=date, end=(datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d'))
                if not hist.empty:
                    close_price = hist['Close'].iloc[0]
                    return {"date": date, "value": float(close_price)}
                else:
                    print(f"      -> ⚠️  No se encontró data de precio para {ticker} en {date}.")
                    return None
            else:
                print(f"      -> ℹ️  La búsqueda de P/E histórico no está soportada. Omitiendo.")
                return None
        else:
            # --- MODO MÁS RECIENTE ---
            today_str = datetime.now().strftime('%Y-%m-%d')
            if series_type == 'pe_ratio':
                pe_ratio = stock.info.get('trailingPE')
                if pe_ratio:
                    return {"date": today_str, "value": float(pe_ratio)}
            elif series_type == 'price':
                 hist = stock.history(period="1d")
                 if not hist.empty:
                    close_price = hist['Close'].iloc[0]
                    return {"date": today_str, "value": float(close_price)}
            
            print(f"      -> ⚠️  No se pudo obtener el dato más reciente para {ticker}.")
            return None

    except Exception as e:
        print(f"   -> ❌ Error obteniendo datos de Yahoo Finance: {e}")
        return None

# ==============================================================================
# LÓGICA DE SINCRONIZACIÓN (VERSIÓN INTELIGENTE Y AUTOMÁTICA)
# ==============================================================================

def sync_yfinance_data_to_supabase():
    """
    Obtiene y guarda datos OHLCV desde Yahoo Finance.
    Automáticamente detecta si debe hacer una carga histórica completa o una
    actualización incremental de 7 días.
    """
    TABLE_NAME = "market_data_ohlcv"
    SOURCE_NAME = "yfinance"

    print(f"--- 🚀 Iniciando Sincronización Inteligente desde {SOURCE_NAME} ---")

    if not supabase:
        print("❌ Error: No se pudo conectar con Supabase.")
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
                check_res = supabase.table(TABLE_NAME).select('timestamp', count='exact').eq('ticker', ticker).limit(1).execute()
                record_count = check_res.count

                data_df = None
                if record_count == 0:
                    print(f"  -> 🚚 Ticker nuevo detectado. Modo: Carga Histórica Completa para {ticker}...")
                    data_df = yf.download(ticker, period="10y", auto_adjust=True)
                else:
                    print(f"  -> 🔄 Ticker existente detectado. Modo: Actualización Incremental para {ticker}...")
                    
                    # --- INICIO DE LA CORRECCIÓN CLAVE ---
                    # Pedimos los datos hasta mañana para incluir el día de hoy.
                    end_date = datetime.now() + timedelta(days=1)
                    start_date = end_date - timedelta(days=8) # Ajustamos a 8 para seguir teniendo 7 días de datos
                    # --- FIN DE LA CORRECCIÓN CLAVE ---
                    
                    data_df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), auto_adjust=True)

                if data_df.empty:
                    raise Exception(f"No se recibieron datos de la API para {ticker}.")

                if data_df.index.tz is not None:
                    print("    -> Normalizando zona horaria de las fechas...")
                    data_df.index = data_df.index.tz_localize(None)

                print(f"    -> Preparando {len(data_df)} registros para upsertar...")
                records_to_upsert = []
                for index, row in data_df.iterrows():
                    record = {
                        "timestamp": index.strftime('%Y-%m-%d'),
                        "ticker": ticker,
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume']),
                        "source": SOURCE_NAME
                    }
                    records_to_upsert.append(record)

                if records_to_upsert:
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
        print(f"--- 💥 ERROR CRÍTICO en el script de sincronización Yahoo Finance: {e} ---")


# --- Punto de entrada para ejecución directa (para pruebas) ---
if __name__ == "__main__":
    sync_yfinance_data_to_supabase()
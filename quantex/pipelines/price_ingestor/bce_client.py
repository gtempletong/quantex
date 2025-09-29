# quantex/pipelines/price_ingestor/bce_client.py

import os
import sys
import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta

# --- Configuración de Rutas y Conexión ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from quantex.core.database_manager import supabase
# --- INICIO DE LA CORRECCIÓN ---
# Importamos la función de guardado especializada
from quantex.core.database_manager import upsert_fixed_income_trades
from quantex.config import Config
# --- FIN DE LA CORRECCIÓN ---


def sync_bce_rates():
    SOURCE_NAME = 'bce'
    # ✅ SEGURO: Obtener URL desde configuración
    API_ENDPOINT = Config.get_bce_url()
    
    print(f"--- 🇪🇺 Iniciando Sincronización Inteligente de Tasas desde {SOURCE_NAME} ---")

    if not supabase:
        print("❌ Error: Falta la conexión a Supabase.")
        return

    try:
        response = supabase.table('fixed_income_definitions').select('id, ticker, name').eq('data_source', SOURCE_NAME).execute()
        instruments_to_sync = response.data
        
        if not instruments_to_sync:
            print(f"-> 🟡 No se encontraron instrumentos para la fuente '{SOURCE_NAME}'.")
            return
            
        print(f"-> 🎯 Instrumentos a sincronizar: {[item['name'] for item in instruments_to_sync]}")
        
        for instrument in instruments_to_sync:
            instrument_key = instrument['ticker']
            
            check_res = supabase.table('fixed_income_trades').select('trade_date', count='exact').eq('instrument_id', instrument['id']).limit(1).execute()
            record_count = check_res.count
            
            end_date = datetime.now()
            start_date = None

            if record_count == 0:
                print(f"  -> 🚚 Ticker nuevo. Modo: Carga Histórica para {instrument['name']}...")
                start_date = datetime(2004, 1, 1)
            else:
                print(f"  -> 🔄 Ticker existente. Modo: Actualización Incremental para {instrument['name']}...")
                start_date = end_date - timedelta(days=30)
            
            url = f"{API_ENDPOINT}/YC/{instrument_key}"
            params = {
                'startPeriod': start_date.strftime('%Y-%m-%d'),
                'endPeriod': end_date.strftime('%Y-%m-%d')
            }
            headers = {'Accept': 'application/vnd.sdmx.genericdata+xml;version=2.1'}

            print(f"    -> Consultando API del BCE para el período {params['startPeriod']} a {params['endPeriod']}...")
            api_response = requests.get(url, params=params, headers=headers)
            api_response.raise_for_status()
            
            root = ET.fromstring(api_response.content)
            
            ns = {
                'g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic',
                'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message'
            }
            
            series_node = root.find('.//g:Series', ns)
            if series_node is None:
                print(f"    -> ⚠️ No se encontraron series de datos en la respuesta para {instrument['name']}.")
                continue

            records_to_upsert = []
            for obs in series_node.findall('g:Obs', ns):
                trade_date = obs.find('g:ObsDimension', ns).get('value')
                average_yield = obs.find('g:ObsValue', ns).get('value')
                
                if trade_date and average_yield is not None:
                    records_to_upsert.append({
                        'instrument_id': instrument['id'], 'instrument_name': instrument['name'], 'ticker': instrument['ticker'],
                        'trade_date': trade_date, 'average_yield': float(average_yield),
                        'quantity': 0, 'amount_clp': 0, 'closing_price_percent': 0
                    })
           
            if records_to_upsert:
                # --- INICIO DE LA CORRECCIÓN ---
                # Usamos la función especializada en lugar del upsert directo
                print(f"    -> Guardando {len(records_to_upsert)} registros...")
                # Usar upsert directo con on_conflict para manejar duplicados
                supabase.table('fixed_income_trades').upsert(records_to_upsert, on_conflict='instrument_id,trade_date').execute()
                # --- FIN DE LA CORRECCIÓN ---
            else:
                print(f"    -> ℹ️ No se encontraron nuevos registros para el período solicitado.")

            print(f"    -> ✅ Sincronización para {instrument['name']} completada.")
            time.sleep(0.5)

        print("\n--- ✅ Sincronización de Tasas del BCE Finalizada ---")

    except Exception as e:
        print(f"--- 💥 ERROR CRÍTICO en la sincronización del BCE: {e} ---")
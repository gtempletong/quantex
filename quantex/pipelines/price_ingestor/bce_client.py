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


def _get_with_retries(url: str, params: dict, headers: dict, max_retries: int = 3):
    """Realiza GET con reintentos exponenciales ante errores transitorios (503/429/5xx)."""
    backoffs = [1, 3, 5, 10]
    attempt = 0
    last_exc = None
    while attempt < max_retries:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            # Si el BCE responde 503/429, considerarlo transitorio
            if resp.status_code in (429, 503):
                raise requests.HTTPError(f"{resp.status_code} {resp.reason}")
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            wait_s = backoffs[min(attempt, len(backoffs)-1)]
            print(f"    -> ⚠️ Error transitorio ({e}). Reintentando en {wait_s}s (intento {attempt+1}/{max_retries})...")
            time.sleep(wait_s)
            attempt += 1
    # Si agotó reintentos, propagar última excepción
    raise last_exc


def sync_bce_rates() -> bool:
    SOURCE_NAME = 'bce'
    # ✅ SEGURO: Obtener URL desde configuración
    API_ENDPOINT = Config.get_bce_url()
    
    print(f"--- Iniciando Sincronización Inteligente de Tasas desde {SOURCE_NAME} ---")

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
        
        any_saved = False
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
                start_date = end_date - timedelta(days=90)  # Ventana amplia para amortiguar baches del BCE
            
            url = f"{API_ENDPOINT}/service/data/YC/{instrument_key}"
            params = {
                'startPeriod': start_date.strftime('%Y-%m-%d'),
                'endPeriod': end_date.strftime('%Y-%m-%d')
            }
            headers = {
                'Accept': 'application/vnd.sdmx.genericdata+xml;version=2.1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            print(f"    -> Consultando API del BCE para el período {params['startPeriod']} a {params['endPeriod']}...")
            # Reintentos ante 503/429/5xx
            try:
                api_response = _get_with_retries(url, params, headers, max_retries=4)
            except Exception as api_error:
                # Fallback: si falla el período reciente, probar con ventana más antigua
                print(f"    -> ⚠️ Error en período reciente: {api_error}")
                print(f"    -> 🔄 Intentando período alternativo (últimos 180 días)...")
                fallback_params = params.copy()
                fallback_start = end_date - timedelta(days=180)
                fallback_params['startPeriod'] = fallback_start.strftime('%Y-%m-%d')
                try:
                    api_response = _get_with_retries(url, fallback_params, headers, max_retries=2)
                    print(f"    -> ✅ Fallback exitoso: usando datos de {fallback_params['startPeriod']}")
                except Exception as fallback_error:
                    print(f"    -> ❌ Fallback también falló: {fallback_error}")
                    continue
            
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
                print(f"    -> Guardando {len(records_to_upsert)} registros...")
                try:
                    # Alinear con EODHD y PDF parser: usar helper centralizado
                    ok = upsert_fixed_income_trades(records_to_upsert)
                    if ok:
                        print(f"    -> ✅ Upsert completado (helper).")
                        any_saved = True
                    else:
                        print(f"    -> ⚠️ Upsert reportó fallo (helper). Revisa logs previos.")
                except Exception as up_e:
                    print(f"    -> 💥 Error en upsert a 'fixed_income_trades' (helper): {up_e}")
            else:
                print(f"    -> ℹ️ No se encontraron nuevos registros para el período solicitado.")

            print(f"    -> ✅ Sincronización para {instrument['name']} completada.")
            time.sleep(2)  # Pausa más larga para evitar detección anti-bot

        print("\n--- ✅ Sincronización de Tasas del BCE Finalizada ---")
        return any_saved

    except Exception as e:
        print(f"--- 💥 ERROR CRÍTICO en la sincronización del BCE: {e} ---")
        return False

if __name__ == "__main__":
    sync_bce_rates()
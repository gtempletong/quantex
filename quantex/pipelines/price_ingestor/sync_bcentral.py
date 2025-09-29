# quantex/pipelines/price_ingestor/sync_bcentral.py

import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client, Client
import math

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

BC_USER = os.getenv("BC_USER")
BC_PASSWORD = os.getenv("BC_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([BC_USER, BC_PASSWORD, SUPABASE_URL, SUPABASE_KEY]):
    print("❌ ERROR: Faltan credenciales en el archivo .env")
    exit(1)

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BC_BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

def get_series_data(serie_id: str, days_back: int = 60) -> list:
    """
    Obtiene todos los datos históricos para una serie del BCCh.
    Retorna una lista de diccionarios con 'date' y 'value'.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        'user': BC_USER,
        'pass': BC_PASSWORD,
        'function': 'GetSeries',
        'timeseries': serie_id,
        'firstdate': start_date.strftime('%Y-%m-%d'),
        'lastdate': end_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(BC_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        observations = data.get('Series', {}).get('Obs', [])
        
        if observations:
            print(f"   -> ✅ Obtenidas {len(observations)} observaciones para '{serie_id}'")
            return observations
        else:
            print(f"   -> 🟡 No se encontraron observaciones para '{serie_id}'")
            return []

    except Exception as e:
        print(f"   -> ❌ Error obteniendo datos para '{serie_id}': {e}")
        return []


def sync_bcentral_series_to_supabase(serie_id: str, config: dict):
    """
    Sincroniza una serie del Banco Central a Supabase (solo ingesta de datos reales).
    Los metadatos se usan solo para el dossier, no se guardan en Supabase.
    """
    ticker = config['ticker']
    description = config['description']
    days_back = config.get('days_back', 30)  # Default 30 días si no se especifica
    
    print(f"🔄 Sincronizando serie BCCh '{serie_id}' como ticker '{ticker}'...")
    
    # 1. Obtener datos del BCCh
    observations = get_series_data(serie_id, days_back)
    if not observations:
        print(f"   -> ❌ No hay datos para sincronizar")
        return False
    
    # 2. Buscar o crear definición de serie
    series_def_res = supabase.table('series_definitions').select('id').eq('ticker', ticker).maybe_single().execute()
    
    if series_def_res.data:
        series_id = series_def_res.data['id']
        print(f"   -> ✅ Usando serie existente: {series_id}")
    else:
        # Crear nueva definición (estructura original de Supabase)
        new_series = {
            'ticker': ticker,
            'description': description,
            'source': 'bcentral',
            'unit': 'percentage' if 'TPM' in serie_id else 'millions_usd',
            'category': 'economic_indicator',
            'country': 'chile',
            'display_name': description
        }
        
        series_res = supabase.table('series_definitions').insert(new_series).execute()
        if series_res.data:
            series_id = series_res.data[0]['id']
            print(f"   -> ✅ Creada nueva definición de serie: {series_id}")
        else:
            print(f"   -> ❌ Error creando definición de serie")
            return False
    
    # 3. Preparar datos para upsert (filtrando valores no finitos)
    records_to_upsert = []
    skipped_count = 0
    for obs in observations:
        ts = obs.get('indexDateString')
        v_raw = obs.get('value')
        try:
            v = float(v_raw)
        except (TypeError, ValueError):
            skipped_count += 1
            continue
        if math.isnan(v) or math.isinf(v):
            skipped_count += 1
            continue
        record = {
            'series_id': series_id,
            'timestamp': ts,
            'value': v,
            'ticker': ticker
        }
        records_to_upsert.append(record)
    
    # 4. Upsert directo (sin forward fill; FF centralizado en run_all_syncs)
    if records_to_upsert:
        print(f"   -> 📦 Preparando {len(records_to_upsert)} registros para upsert (sin forward fill)...")
        if skipped_count:
            print(f"   -> ⚠️ {skipped_count} observaciones omitidas por valores no numéricos/NaN/inf")
        
        # Normalizar fecha a ISO
        for r in records_to_upsert:
            try:
                r['timestamp'] = datetime.strptime(r['timestamp'], '%d-%m-%Y').strftime('%Y-%m-%d')
            except Exception:
                pass
        
        try:
            supabase.table('time_series_data').upsert(
                records_to_upsert,
                on_conflict='series_id,timestamp'
            ).execute()
            print(f"   -> ✅ Datos sincronizados exitosamente (ingesta pura)")
            return True
        except Exception as e:
            print(f"   -> ❌ Error en upsert: {e}")
            return False
    
    return False


def get_bcentral_series_config():
    """
    Retorna la configuración de series BCCH como fuente de la verdad.
    """
    return {
        'F022.TPM.TIN.D001.NO.Z.D': {
            'ticker': 'chile_tpm',
            'description': 'Tasa de Política Monetaria Chile',
            'display_name': 'Tasa de Política Monetaria Chile',
            'context_for_ai': 'Tasa de política monetaria oficial del Banco Central de Chile.',
            'days_back': 10  # Se actualiza diariamente
        },
        'F099.DER.STO.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D': {
            'ticker': 'Posicion Extranjera CLP',
            'description': 'Posición Forward de Extranjeros en Chile',
            'display_name': 'Posición Forward de Extranjeros en Chile',
            'context_for_ai': 'Posición forward neta de extranjeros en pesos chilenos.',
            'days_back': 15  # Desfase de 2 días + margen
        },
        'F019.TPM.TIN.10.D': {
            'ticker': 'us_tpm',
            'description': 'Tasa de politica monetaria FED',
            'display_name': 'Tasa de Política Monetaria FED',
            'context_for_ai': 'Tasa de política monetaria de la Reserva Federal de Estados Unidos.',
            'days_back': 10  # Se actualiza diariamente
        },
        'F089.TPM.TAS.11.M': {
            'ticker': 'bcch_expectativas_tpm_prox_reunion',
            'description': 'Expectativas de tasa de política monetaria para la próxima reunión del BCCH',
            'display_name': 'Expectativas TPM Próxima Reunión',
            'context_for_ai': 'Expectativas del mercado sobre la tasa de política monetaria para la próxima reunión del BCCH.  Fuente:  Encuesta de Operadores Financieros del Banco Central de Chile'
        },
        'F089.TPM.TAS.31.M': {
            'ticker': 'bcch_expectativas_tpm_subsiguiente_reunion',
            'description': 'Expectativas de tasa de política monetaria para la subsiguiente reunión del BCCH',
            'display_name': 'Expectativas TPM Subsiguiente Reunión',
            'context_for_ai': 'Expectativas del mercado sobre la tasa de política monetaria para la subsiguiente reunión del BCCH.Fuente:  Encuesta de Operadores Financieros del Banco Central de Chile'
        }
    }

def sync_all_bcentral_series():
    """
    Sincroniza todas las series del Banco Central configuradas.
    """
    print("🔄 Iniciando sincronización de series BCCh...")
    
    # Configuración de series con metadatos para la IA
    bcentral_series = get_bcentral_series_config()
    
    success_count = 0
    for serie_id, config in bcentral_series.items():
        success = sync_bcentral_series_to_supabase(
            serie_id=serie_id,
            config=config
        )
        if success:
            success_count += 1
    
    print(f"🎉 Sincronización completada: {success_count}/{len(bcentral_series)} series exitosas")
    return success_count == len(bcentral_series)


if __name__ == "__main__":
    print("=== SINCRONIZACIÓN BANCO CENTRAL CHILE ===")
    sync_all_bcentral_series()

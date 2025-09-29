# quantex/core/data_fetcher.py

import pandas as pd
from datetime import datetime, timedelta
from .database_manager import supabase

# En: quantex/core/data_fetcher.py

def get_data_series(identifier: str, days: int) -> pd.DataFrame | None:
    """
    Busca un identificador y devuelve sus datos históricos, asegurando que el
    índice de fecha no tenga información de zona horaria (tz-naive).
    (Versión con Estandarización de Zona Horaria)
    """
    print(f"-> 🔎 [Buscador Universal] Solicitando datos para '{identifier}' de los últimos {days} días...")
    
    end_date = datetime.now()
    start_date_str = (end_date - timedelta(days=days)).strftime('%Y-%m-%d')

    # 1. Buscar en instrument_definitions
    print(f"   -> 🔍 [DEBUG] Buscando en instrument_definitions para '{identifier}'...")
    inst_def_res = supabase.table('instrument_definitions').select('id, ticker').ilike('ticker', identifier).maybe_single().execute()
    print(f"   -> 🔍 [DEBUG] Resultado de búsqueda en instrument_definitions: {inst_def_res.data if inst_def_res else 'None'}")
    
    if inst_def_res and inst_def_res.data:
        print(f"   -> ✅ [DEBUG] Instrumento encontrado en instrument_definitions: ID={inst_def_res.data['id']}, ticker={inst_def_res.data['ticker']}")
        # ... (lógica de búsqueda no cambia)
        response = supabase.table('market_data_ohlcv').select('*').ilike('ticker', identifier).gte('timestamp', start_date_str).order('timestamp', desc=False).execute()
        print(f"   -> 🔍 [DEBUG] Datos encontrados en market_data_ohlcv: {len(response.data) if response.data else 0} registros")
        if not response.data: 
            print(f"   -> ⚠️ [DEBUG] No hay datos en market_data_ohlcv para el ticker {identifier}")
            return None
        df = pd.DataFrame(response.data)
        df.rename(columns={'timestamp': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None) # <-- LÍNEA CLAVE AÑADIDA
        df.set_index('date', inplace=True)
        print(f"   -> ✅ [DEBUG] DataFrame creado exitosamente con {len(df)} filas")
        return df[['open', 'high', 'low', 'close', 'volume']]
    else:
        print(f"   -> ❌ [DEBUG] No se encontró '{identifier}' en instrument_definitions")

    # 2. Buscar en fixed_income_definitions
    print(f"   -> 🔍 [DEBUG] Buscando en fixed_income_definitions para '{identifier}'...")
    fi_def_res = supabase.table('fixed_income_definitions').select('id, ticker').ilike('ticker', identifier).maybe_single().execute()
    print(f"   -> 🔍 [DEBUG] Resultado de búsqueda en fixed_income_definitions: {fi_def_res.data if fi_def_res else 'None'}")
    
    if fi_def_res and fi_def_res.data:
        print(f"   -> ✅ [DEBUG] Fixed income encontrado en fixed_income_definitions: ID={fi_def_res.data['id']}, ticker={fi_def_res.data['ticker']}")
        # ... (lógica de búsqueda no cambia)
        response = supabase.table('fixed_income_trades').select('trade_date, average_yield').eq('instrument_id', fi_def_res.data['id']).gte('trade_date', start_date_str).order('trade_date', desc=False).execute()
        print(f"   -> 🔍 [DEBUG] Datos encontrados en fixed_income_trades: {len(response.data) if response.data else 0} registros")
        if not response.data: 
            print(f"   -> ⚠️ [DEBUG] No hay datos en fixed_income_trades para el instrument_id {fi_def_res.data['id']}")
            return None
        df = pd.DataFrame(response.data)
        df.rename(columns={'trade_date': 'date', 'average_yield': 'close'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None) # <-- LÍNEA CLAVE AÑADIDA
        df.set_index('date', inplace=True)
        print(f"   -> ✅ [DEBUG] DataFrame creado exitosamente con {len(df)} filas")
        return df[['close']]
    else:
        print(f"   -> ❌ [DEBUG] No se encontró '{identifier}' en fixed_income_definitions")

    # 3. Buscar en series_definitions
    print(f"   -> 🔍 [DEBUG] Buscando en series_definitions para '{identifier}'...")
    series_def_res = supabase.table('series_definitions').select('id, ticker').ilike('ticker', identifier).maybe_single().execute()
    print(f"   -> 🔍 [DEBUG] Resultado de búsqueda en series_definitions: {series_def_res.data if series_def_res else 'None'}")
    
    if series_def_res and series_def_res.data:
        print(f"   -> ✅ [DEBUG] Serie encontrada en series_definitions: ID={series_def_res.data['id']}, ticker={series_def_res.data['ticker']}")
        # ... (lógica de búsqueda no cambia)
        response = supabase.table('time_series_data').select('timestamp, value').eq('series_id', series_def_res.data['id']).gte('timestamp', start_date_str).order('timestamp', desc=False).execute()
        print(f"   -> 🔍 [DEBUG] Datos encontrados en time_series_data: {len(response.data) if response.data else 0} registros")
        if not response.data: 
            print(f"   -> ⚠️ [DEBUG] No hay datos en time_series_data para la serie {series_def_res.data['id']}")
            return None
        df = pd.DataFrame(response.data)
        df.rename(columns={'timestamp': 'date', 'value': 'close'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None) # <-- LÍNEA CLAVE AÑADIDA
        df.set_index('date', inplace=True)
        print(f"   -> ✅ [DEBUG] DataFrame creado exitosamente con {len(df)} filas")
        return df[['close']]
    else:
        print(f"   -> ❌ [DEBUG] No se encontró '{identifier}' en series_definitions")

    print(f"   -> ❌ [Error] No se encontró el identificador '{identifier}' en ninguna tabla de definiciones.")
    return None
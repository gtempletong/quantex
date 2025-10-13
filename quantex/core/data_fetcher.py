# quantex/core/data_fetcher.py

import pandas as pd
from datetime import datetime, timedelta
from .database_manager import supabase

# En: quantex/core/data_fetcher.py

def get_data_series(identifier: str, days: int) -> pd.DataFrame | None:
    """
    Busca un identificador y devuelve sus datos históricos con paginación por batches.
    (Versión con Paginación para superar límites de 1000 registros)
    """
    print(f"-> 🔎 [Buscador Universal] Solicitando datos para '{identifier}' de los últimos {days} días...")
    
    end_date = datetime.now()
    start_date_str = (end_date - timedelta(days=days)).strftime('%Y-%m-%d')
    BATCH_SIZE = 1000

    # 1. Buscar en instrument_definitions
    print(f"   -> 🔍 [DEBUG] Buscando en instrument_definitions para '{identifier}'...")
    inst_def_res = supabase.table('instrument_definitions').select('id, ticker').ilike('ticker', identifier).maybe_single().execute()
    print(f"   -> 🔍 [DEBUG] Resultado de búsqueda en instrument_definitions: {inst_def_res.data if inst_def_res else 'None'}")
    
    if inst_def_res and inst_def_res.data:
        print(f"   -> ✅ [DEBUG] Instrumento encontrado en instrument_definitions: ID={inst_def_res.data['id']}, ticker={inst_def_res.data['ticker']}")
        
        # Paginación para market_data_ohlcv
        all_data = []
        offset = 0
        while True:
            batch_num = offset // BATCH_SIZE + 1
            print(f"   -> 📦 [DEBUG] Obteniendo batch #{batch_num} (offset: {offset})...")
            response = supabase.table('market_data_ohlcv').select('*').ilike('ticker', identifier).gte('timestamp', start_date_str).order('timestamp', desc=False).range(offset, offset + BATCH_SIZE - 1).execute()
            
            if not response.data or len(response.data) == 0:
                break
            
            all_data.extend(response.data)
            print(f"   -> ✅ [DEBUG] Batch #{batch_num}: {len(response.data)} registros obtenidos")
            
            if len(response.data) < BATCH_SIZE:
                break
            
            offset += BATCH_SIZE
        
        print(f"   -> 🎯 [DEBUG] TOTAL datos en market_data_ohlcv: {len(all_data)} registros")
        if not all_data:
            print(f"   -> ⚠️ [DEBUG] No hay datos en market_data_ohlcv para el ticker {identifier}")
            return None
        
        df = pd.DataFrame(all_data)
        df.rename(columns={'timestamp': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        df = df[~df.index.duplicated(keep='first')]  # Eliminar duplicados por si acaso
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
        
        # Paginación para fixed_income_trades
        all_data = []
        offset = 0
        while True:
            batch_num = offset // BATCH_SIZE + 1
            print(f"   -> 📦 [DEBUG] Obteniendo batch #{batch_num} (offset: {offset})...")
            response = supabase.table('fixed_income_trades').select('trade_date, average_yield').eq('instrument_id', fi_def_res.data['id']).gte('trade_date', start_date_str).order('trade_date', desc=False).range(offset, offset + BATCH_SIZE - 1).execute()
            
            if not response.data or len(response.data) == 0:
                break
            
            all_data.extend(response.data)
            print(f"   -> ✅ [DEBUG] Batch #{batch_num}: {len(response.data)} registros obtenidos")
            
            if len(response.data) < BATCH_SIZE:
                break
            
            offset += BATCH_SIZE
        
        print(f"   -> 🎯 [DEBUG] TOTAL datos en fixed_income_trades: {len(all_data)} registros")
        if not all_data:
            print(f"   -> ⚠️ [DEBUG] No hay datos en fixed_income_trades para el instrument_id {fi_def_res.data['id']}")
            return None
        
        df = pd.DataFrame(all_data)
        df.rename(columns={'trade_date': 'date', 'average_yield': 'close'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        df = df[~df.index.duplicated(keep='first')]
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
        
        # Paginación para time_series_data
        all_data = []
        offset = 0
        while True:
            batch_num = offset // BATCH_SIZE + 1
            print(f"   -> 📦 [DEBUG] Obteniendo batch #{batch_num} (offset: {offset})...")
            response = supabase.table('time_series_data').select('timestamp, value').eq('series_id', series_def_res.data['id']).gte('timestamp', start_date_str).order('timestamp', desc=False).range(offset, offset + BATCH_SIZE - 1).execute()
            
            if not response.data or len(response.data) == 0:
                break
            
            all_data.extend(response.data)
            print(f"   -> ✅ [DEBUG] Batch #{batch_num}: {len(response.data)} registros obtenidos")
            
            if len(response.data) < BATCH_SIZE:
                break
            
            offset += BATCH_SIZE
        
        print(f"   -> 🎯 [DEBUG] TOTAL datos en time_series_data: {len(all_data)} registros")
        if not all_data:
            print(f"   -> ⚠️ [DEBUG] No hay datos en time_series_data para la serie {series_def_res.data['id']}")
            return None
        
        df = pd.DataFrame(all_data)
        df.rename(columns={'timestamp': 'date', 'value': 'close'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df.set_index('date', inplace=True)
        df = df[~df.index.duplicated(keep='first')]
        print(f"   -> ✅ [DEBUG] DataFrame creado exitosamente con {len(df)} filas")
        return df[['close']]
    else:
        print(f"   -> ❌ [DEBUG] No se encontró '{identifier}' en series_definitions")

    print(f"   -> ❌ [Error] No se encontró el identificador '{identifier}' en ninguna tabla de definiciones.")
    return None
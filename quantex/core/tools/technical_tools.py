# quantex/core/technical_tools.py (Versión 100% Estandarizada y Final)

# --- Bloque de Configuración de Matplotlib (LA SOLUCIÓN) ---
import matplotlib
matplotlib.use('Agg')
# --- Fin del Bloque ---

import os
import sys
import pandas as pd
from quantex.config import Config
import io
import requests
import re
from datetime import datetime, timedelta
import mplfinance as mpf
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importaciones de Quantex ---
from quantex.core import database_manager as db
from quantex.core.tool_registry import registry

# --- MAPA DE TICKERS ---
EODHD_TICKER_MAP = {
    "clp": "USDCLP.FOREX",
    "dxy": "DXY.INDX",
    "cny": "USDCNY.FOREX",
    "us_5_year_treasury": "US5Y.INDX", 
    
}

load_dotenv()

# --- FUNCIONES ORIGINALES (INTACTAS Y MODIFICADAS) ---



@registry.register(name="add_technical_indicators")
def add_technical_indicators(workspace: dict, params: dict) -> None:
    """
    Toma una serie de datos, calcula indicadores y guarda el resultado en una nueva clave.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    source_key = params.get("source_key")
    output_key = params.get("output_key") # <-- Lee la nueva clave de salida
    if not source_key or not output_key:
        print("    -> ⚠️  'add_technical_indicators' requiere 'source_key' y 'output_key'.")
        return

    # Extraer datos numéricos de series enriquecidas
    raw_data = workspace.get(source_key)
    if not raw_data:
        print(f"    -> ⚠️  No se encontraron datos en el workspace para la clave '{source_key}'.")
        return
    
    # Si es una serie enriquecida con metadatos, extraer solo los datos numéricos
    if isinstance(raw_data, dict) and 'data' in raw_data:
        print(f"    -> 🔍 Detectada serie enriquecida con metadatos para '{source_key}'. Extrayendo datos numéricos...")
        numeric_data = raw_data['data']
    else:
        numeric_data = raw_data
    
    df_raw = pd.DataFrame(numeric_data)
    if df_raw.empty:
        print(f"    -> ⚠️  No se encontraron datos numéricos para la clave '{source_key}'.")
        return
        
    # (Aquí va toda la lógica de cálculo de indicadores que ya tienes...)
    df_indicators = calculate_all_indicators(df_raw) # Asumiendo que esta función devuelve el DF
    
    # --- Cambio Clave ---
    # Guarda el resultado en la clave especificada en el output_key
    workspace[output_key] = df_indicators.reset_index().to_dict('records')
    print(f"    -> ✅ Indicadores añadidos a la clave '{output_key}'.")



def fetch_stock_data(ticker: str, api_key: str, period_days: int = 365) -> pd.DataFrame | None:
    """
    (Versión Corregida)
    Usa el EODHD_TICKER_MAP para traducir alias antes de llamar a la API.
    Siempre devuelve un DataFrame con columnas en minúsculas.
    """
    # --- INICIO DE LA CORRECCIÓN ---
    # Busca el alias en el mapa. Si no lo encuentra, usa el ticker original.
    api_ticker = EODHD_TICKER_MAP.get(ticker.lower(), ticker)
    print(f"  -> 🛠️ [Fetch Data] Ticker original: '{ticker}', Ticker para API: '{api_ticker}'")
    # --- FIN DE LA CORRECCIÓN ---
    
    to_date = datetime.now()
    from_date = to_date - timedelta(days=period_days)
    
    # Ahora usamos el 'api_ticker' correcto en la URL
    # ✅ SEGURO: Obtener URL desde configuración
    api_url = f"{Config.get_eodhd_url()}/{api_ticker}?api_token={api_key}&fmt=json&from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data or not isinstance(data, list): return None
        df = pd.DataFrame(data)
        
        df.columns = [col.lower() for col in df.columns]
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'adjusted_close']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"  -> ❌ Error en fetch_stock_data para {api_ticker}: {e}")
        return None

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    (Versión Flexible)
    Calcula un conjunto completo de indicadores técnicos.
    Ahora es compatible con DataFrames que usan 'close' o 'value'.
    """
    print("  -> 🛠️ Ejecutando 'calculate_all_indicators'...")
    
    # --- INICIO DE LA CORRECCIÓN ---
    # 1. Determinar qué columna de precios usar
    if 'close' in df.columns:
        price_col = 'close'
    elif 'value' in df.columns:
        price_col = 'value'
    else:
        raise ValueError("El DataFrame debe contener una columna 'close' o 'value'.")
    
    print(f"    -> Usando la columna '{price_col}' para los cálculos.")
    # --- FIN DE LA CORRECCIÓN ---

    # 2. Usar la columna de precios seleccionada para todos los cálculos
    df['SMA_20'] = df[price_col].rolling(window=20).mean()
    df['SMA_50'] = df[price_col].rolling(window=50).mean()
    df['SMA_200'] = df[price_col].rolling(window=200).mean()
    
    delta = df[price_col].diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-9) # Evitar división por cero
    df['RSI'] = 100.0 - (100.0 / (1.0 + rs))
    
    ema_12 = df[price_col].ewm(span=12, adjust=False).mean()
    ema_26 = df[price_col].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    df['BB_Middle'] = df['SMA_20']
    df['BB_Std'] = df[price_col].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    
    # Es correcto eliminar las filas iniciales donde los indicadores no se pueden calcular
    df.dropna(inplace=True) 
    print("    -> ✅ Todos los indicadores calculados exitosamente.")
    return df

def _parse_offset_to_relativedelta(offset_str: str) -> relativedelta:
    """
    Convierte un string como '7d', '3m', '2y' a un objeto relativedelta.
    """
    match = re.match(r"(\d+)([dmy])", offset_str)
    if not match:
        raise ValueError(f"El formato del offset '{offset_str}' no es válido.")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 'd':
        return relativedelta(days=value)
    elif unit == 'm':
        return relativedelta(months=value)
    elif unit == 'y':
        return relativedelta(years=value)

@registry.register(name="calculate_offset_value")
def calculate_offset_value(series_data: list, offset: str, calculation_mode: str = 'percentage', **kwargs) -> dict | None:
    """
    (Herramienta Unificada y Robusta)
    Calcula una variación para un 'offset' de tiempo.
    - calculation_mode='percentage': Devuelve la variación porcentual.
    - calculation_mode='absolute': Devuelve la diferencia absoluta (delta).
    Maneja automáticamente series enriquecidas con metadatos.
    """
    print(f"  -> 🛠️ Ejecutando 'calculate_offset_value' (Modo: {calculation_mode}) para offset '{offset}'...")
    try:
        # Extraer datos numéricos de series enriquecidas
        if isinstance(series_data, dict) and 'data' in series_data:
            print(f"    -> 🔍 Detectada serie enriquecida con metadatos en calculate_offset_value. Extrayendo datos numéricos...")
            numeric_data = series_data['data']
        else:
            numeric_data = series_data
            
        if len(numeric_data) < 2: return {"value": 0 if calculation_mode == 'absolute' else "N/A"}
        
        df = pd.DataFrame(numeric_data)
        value_col = 'close' if 'close' in df.columns else 'value'
        df['timestamp'] = pd.to_datetime(df.get('date', df.get('timestamp'))).dt.tz_localize(None)
        df.set_index('timestamp', inplace=True); df.sort_index(inplace=True)
        df[value_col] = pd.to_numeric(df[value_col])

        delta = _parse_offset_to_relativedelta(offset)
        if not delta: raise ValueError(f"El offset '{offset}' no es válido.")

        last_date = df.index[-1]
        last_value = df[value_col].iloc[-1]
        target_date = last_date - delta

        index_position = df.index.get_indexer([target_date], method='nearest')[0]
        period_ago_value = df[value_col].iloc[index_position]

        if pd.isna(last_value) or pd.isna(period_ago_value):
            return {"value": 0 if calculation_mode == 'absolute' else "N/A"}

        if calculation_mode == 'absolute':
            variation = last_value - period_ago_value
            return {"value": variation}
        else: # percentage por defecto
            if period_ago_value == 0: return {"value": "inf%"}
            variation = ((last_value / period_ago_value) - 1)
            return {"value": f"{variation:.2%}"}
        
    except Exception as e:
        print(f"    -> ❌ Error en calculate_offset_value para offset '{offset}': {e}")
        return {"value": "Error"}



@registry.register(name="apply_unit_conversion")
def apply_unit_conversion(workspace: dict, params: dict) -> None:
    """
    (Versión Corregida con Soporte para Series Enriquecidas)
    Aplica conversión de unidades usando la columna 'close'.
    Maneja tanto series simples como series enriquecidas con metadatos.
    """
    source_keys = params.get("source_series_keys", [])
    factor = params.get("conversion_factor")
    
    if not factor or not source_keys:
        return

    print(f"  -> 🛠️ Ejecutando 'apply_unit_conversion' para las claves: {source_keys}...")
    for key in source_keys:
        if key in workspace:
            # Extraer datos numéricos de series enriquecidas
            def extract_numeric_data(data):
                if isinstance(data, dict) and 'data' in data:
                    print(f"    -> 🔍 Detectada serie enriquecida con metadatos en apply_unit_conversion. Extrayendo datos numéricos...")
                    return data['data']
                return data

            numeric_data = extract_numeric_data(workspace[key])
            
            for point in numeric_data:
                try:
                    point['close'] = float(point['close']) * factor
                except (ValueError, TypeError, KeyError):
                    continue
    print(f"    -> ✅ Conversión de unidades completada.")

@registry.register(name="apply_currency_conversion")
def apply_currency_conversion(workspace: dict, params: dict) -> None:
    """
    (Versión Corregida y Robusta)
    Aplica conversión de moneda, manejando de forma flexible la columna de fecha.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    source_key = params.get("source_series_key")
    rate_key = params.get("rate_series_key")
    
    # La cláusula de guarda sigue siendo importante
    if not all([source_key, rate_key, workspace.get(source_key), workspace.get(rate_key)]):
        print(f"    -> ⚠️  Advertencia en 'apply_currency_conversion': Faltan datos para {source_key} o {rate_key}. Omitiendo.")
        return

    print(f"  -> 🛠️ Ejecutando 'apply_currency_conversion' para '{source_key}'...")
    try:
        # Extraer datos numéricos de series enriquecidas
        def extract_numeric_data(data):
            if isinstance(data, dict) and 'data' in data:
                print(f"    -> 🔍 Detectada serie enriquecida con metadatos en apply_currency_conversion. Extrayendo datos numéricos...")
                return data['data']
            return data

        source_numeric_data = extract_numeric_data(workspace[source_key])
        rate_numeric_data = extract_numeric_data(workspace[rate_key])

        df_source = pd.DataFrame(source_numeric_data)
        df_rate = pd.DataFrame(rate_numeric_data)

        # --- INICIO DE LA CORRECCIÓN CLAVE ---
        # Hacemos que la herramienta sea inteligente y busque 'date' o 'timestamp'
        for df in [df_source, df_rate]:
            if 'date' in df.columns:
                df.rename(columns={'date': 'timestamp'}, inplace=True)
            
            if 'timestamp' not in df.columns:
                raise KeyError("DataFrame no contiene una columna de fecha ('date' o 'timestamp').")
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        # --- FIN DE LA CORRECCIÓN CLAVE ---
        
        df_rate = df_rate[['timestamp', 'close']].rename(columns={'close': 'rate_value'})
        df_merged = pd.merge(df_source, df_rate, on='timestamp', how='left').ffill()
        
        # Se asegura de que las columnas a operar sean numéricas
        df_merged['close'] = pd.to_numeric(df_merged['close'], errors='coerce')
        df_merged['rate_value'] = pd.to_numeric(df_merged['rate_value'], errors='coerce')
        
        # Realiza la conversión y crea la columna 'close' estandarizada
        df_merged['close'] = df_merged['close'] / df_merged['rate_value']
        
        # Devuelve el DataFrame al workspace en el formato correcto (lista de dicts)
        # y renombrando 'timestamp' de vuelta a 'date' para mantener el estándar.
        final_df = df_merged[['timestamp', 'close']].dropna().rename(columns={'timestamp': 'date'})
        workspace[source_key] = final_df.to_dict('records')
        print(f"    -> ✅ Conversión de moneda para '{source_key}' completada.")

    except Exception as e:
        print(f"    -> ❌ Error en apply_currency_conversion para '{source_key}': {e}")

@registry.register(name="convert_cents_to_dollars")
def convert_cents_to_dollars(workspace: dict, params: dict) -> None:
    source_keys = params.get("source_series_keys", [])
    for key in source_keys:
        if key in workspace:
            for point in workspace.get(key, []):
                try:
                    # CORRECCIÓN: Usa 'close' en minúsculas, que es el estándar del sistema.
                    if 'close' in point:
                        point['close'] = float(point['close']) / 100
                    elif 'value' in point:
                         point['value'] = float(point['value']) / 100
                except (ValueError, TypeError):
                    continue

@registry.register(name="calculate_rate_differential")
def calculate_rate_differential(workspace: dict, params: dict) -> None:
    """
    (Versión Corregida con Parámetros Flexibles)
    Calcula el diferencial de tasas, aceptando claves de parámetros variables.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    print("  -> 🛠️ Ejecutando 'calculate_rate_differential'...")
    try:
        # --- INICIO DE LA CORRECCIÓN ---
        # Busca la clave de tasa de EEUU (estándar) y la otra tasa (que puede ser clp o eu)
        us_key = params.get("us_rate_data_key")
        other_key = params.get("clp_rate_data_key") or params.get("eu_rate_data_key")
        output_key = params.get("output_key")
        # --- FIN DE LA CORRECCIÓN ---

        if not all([us_key, other_key, output_key]):
            raise ValueError("La receta no especificó los parámetros necesarios (us_rate_data_key, [clp/eu]_rate_data_key, output_key).")

        us_rate_data = workspace.get(us_key)
        other_rate_data = workspace.get(other_key)

        if not us_rate_data or not other_rate_data:
            print(f"    -> ⚠️  Advertencia: No se encontraron los datos para '{us_key}' o '{other_key}'. Omitiendo cálculo.")
            return

        # Extraer datos numéricos de series enriquecidas
        def extract_numeric_data(data):
            if isinstance(data, dict) and 'data' in data:
                print(f"    -> 🔍 Detectada serie enriquecida con metadatos. Extrayendo datos numéricos...")
                return data['data']
            return data

        us_numeric_data = extract_numeric_data(us_rate_data)
        other_numeric_data = extract_numeric_data(other_rate_data)

        df_us = pd.DataFrame(us_numeric_data)
        df_other = pd.DataFrame(other_numeric_data)

        for df in [df_us, df_other]:
            if 'date' in df.columns: df.rename(columns={'date': 'timestamp'}, inplace=True)
            if 'timestamp' not in df.columns: raise KeyError("Falta la columna 'timestamp' o 'date'.")

        us_val_col = 'close' if 'close' in df_us.columns else 'value'
        other_val_col = 'close' if 'close' in df_other.columns else 'value'

        df_us_final = df_us[['timestamp', us_val_col]].rename(columns={us_val_col: 'value_us'})
        df_other_final = df_other[['timestamp', other_val_col]].rename(columns={other_val_col: 'value_other'})
        
        df_us_final['timestamp'] = pd.to_datetime(df_us_final['timestamp']).dt.tz_localize(None)
        df_other_final['timestamp'] = pd.to_datetime(df_other_final['timestamp']).dt.tz_localize(None)

        df_merged = pd.merge(df_us_final, df_other_final, on='timestamp', how='outer').sort_index().ffill().dropna()
        
        for col in ['value_us', 'value_other']:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')

        df_merged['value'] = df_merged['value_us'] - df_merged['value_other']
        result_list = df_merged[['timestamp', 'value']].rename(columns={'timestamp':'date'}).to_dict('records')

        workspace[output_key] = result_list
        print(f"    -> ✅ Diferencial de tasas calculado y guardado en la clave '{output_key}'.")

    except Exception as e:
        print(f"    -> ❌ Error en calculate_rate_differential: {e}")

@registry.register(name="calculate_moving_average")
def calculate_moving_average(workspace: dict, params: dict) -> None:
    """
    (Versión con Espía de Depuración)
    Calcula la media móvil para una serie y guarda el resultado en el workspace.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    try:
        source_key = params.get("source_series_key")
        window = params.get("window")
        output_key = params.get("output_key")

        if not all([source_key, window, output_key]):
            raise ValueError("La receta no especificó 'source_series_key', 'window' o 'output_key'.")

        series_data = workspace.get(source_key)
        if not series_data:
            raise ValueError(f"No se encontraron datos para la clave '{source_key}' en el workspace.")

        # Extraer datos numéricos de series enriquecidas
        if isinstance(series_data, dict) and 'data' in series_data:
            print(f"    -> 🔍 Detectada serie enriquecida con metadatos para '{source_key}'. Extrayendo datos numéricos...")
            numeric_data = series_data['data']
        else:
            numeric_data = series_data

        # --- INICIO DEL ESPÍA ---
        print(f"    -> 🕵️ ESPÍA SMA ({window}d): Recibidos {len(numeric_data)} puntos de datos para '{source_key}'.")
        # --- FIN DEL ESPÍA ---

        df = pd.DataFrame(numeric_data)
        value_col = 'close' if 'close' in df.columns else 'value'
        df['sma'] = df[value_col].rolling(window=window).mean()
        
        # OJO: Asegúrate de que la siguiente línea NO tenga .dropna()
        result_list = df[['timestamp', 'sma']].to_dict('records')
        
        # --- INICIO DEL ESPÍA ---
        print(f"    -> 🕵️ ESPÍA SMA ({window}d): Se van a guardar {len(result_list)} puntos en el workspace para '{output_key}'.")
        # --- FIN DEL ESPÍA ---

        workspace[output_key] = result_list
        print(f"    -> ✅ Media móvil ({window}d) calculada para '{source_key}' y guardada en '{output_key}'.")

    except Exception as e:
        print(f"    -> ❌ Error en calculate_moving_average: {e}")

def create_indicator_dataframe(ticker: str, api_key: str, period_days: int) -> pd.DataFrame | None:
    print(f"  -> ⚙️  Creando DataFrame de indicadores para {ticker}...")
    df = fetch_stock_data(ticker, api_key, period_days=period_days)
    if df is None or df.empty:
        print(f"    -> ❌ Fallo en fetch_stock_data.")
        return None
    
    print("    -> 💧 Estandarizando y limpiando datos...")
    
    if 'adjusted_close' in df.columns:
        df = df.drop(columns=['adjusted_close'])
        print("    -> Columna 'adjusted_close' eliminada para priorizar 'close'.")
    
    required_cols = ['open', 'high', 'low', 'close']
    df.dropna(subset=required_cols, inplace=True)
    
    if df.empty:
        print("    -> ❌ DataFrame vacío después de la limpieza final.")
        return None
        
    df_with_indicators = calculate_all_indicators(df)
    print("    -> ✅ DataFrame de indicadores creado y limpio.")
    return df_with_indicators        






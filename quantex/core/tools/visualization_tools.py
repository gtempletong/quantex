# --- Bloque de Configuración de Matplotlib ---
import matplotlib
matplotlib.use('Agg')
# --- Fin del Bloque ---

import os
import sys
import pandas as pd
import io
import re
import mplfinance as mpf
import matplotlib.pyplot as plt
import traceback
from datetime import datetime
import matplotlib.dates as mdates
from PIL import Image, ImageDraw
import io

def _extract_numeric_data(data):
    """
    Extrae datos numéricos de series enriquecidas con metadatos.
    """
    if isinstance(data, dict) and 'data' in data:
        print(f"    -> 🔍 Detectada serie enriquecida con metadatos en visualización. Extrayendo datos numéricos...")
        return data['data']
    return data



# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importaciones de Quantex ---
from quantex.core import database_manager as db

def standardize_image_size(image_bytes: bytes, target_size: tuple = (1200, 600)) -> bytes:
    """
    Estandariza el tamaño de una imagen manteniendo aspect ratio
    """
    try:
        # Abrir imagen desde bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Calcular nuevo tamaño manteniendo aspect ratio
        original_width, original_height = image.size
        target_width, target_height = target_size
        
        # Calcular ratio de escalado
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        
        # Usar el ratio menor para mantener aspect ratio
        scale_ratio = min(width_ratio, height_ratio)
        
        new_width = int(original_width * scale_ratio)
        new_height = int(original_height * scale_ratio)
        
        # Redimensionar imagen
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crear imagen con fondo blanco del tamaño objetivo
        final_image = Image.new('RGB', target_size, 'white')
        
        # Centrar la imagen redimensionada
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        final_image.paste(resized_image, (x_offset, y_offset))
        
        # Convertir a bytes
        output_buffer = io.BytesIO()
        final_image.save(output_buffer, format='PNG', dpi=(120, 120))
        
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"❌ Error estandarizando imagen: {e}")
        return image_bytes  # Devolver original si hay error
from quantex.core.tool_registry import registry


@registry.register(name="generate_chart")
def generate_chart(evidence_workspace: dict, params: dict) -> dict | None:
    """
    (Versión Definitiva)
    Función despachadora que maneja todos los tipos de gráficos.
    """
    chart_type = params.get("chart_type")
    print(f"🏭 [Fábrica de Gráficos] Petición recibida para generar un gráfico de tipo: '{chart_type}'")

    safe_title = re.sub(r'[^a-zA-Z0-9_]', '', params.get("html_title", "chart")).lower()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = f"{safe_title}_{timestamp}.png"
    
    chart_url = None
    
    if chart_type == "custom_line_chart":
        chart_url = generate_custom_line_chart(params, evidence_workspace, file_name)
    
    elif chart_type == "contribution_stack_chart":
        chart_url = _generate_contribution_stack_chart(params, evidence_workspace, file_name)

    elif chart_type == "candlestick":
        # Extraemos la serie de datos que el gráfico necesita
        source_key = params.get("source_series_key")
        ohlc_data = evidence_workspace.get(source_key)
        chart_url = generate_candlestick_chart(ohlc_data, params)    
    
    else:
        print(f"    -> ❌ Error: Tipo de gráfico '{chart_type}' no es reconocido por la fábrica.")
        return None

    if chart_url:
        print(f"   -> ✅ Gráfico generado exitosamente.")
        print(f"   -> ⚠️ Estandarización DESACTIVADA para preservar ajustes manuales")
        
        return {
            "title": params.get("html_title", "Gráfico sin título"),
            "html": f'<img src="{chart_url}" alt="{params.get("html_title", "Gráfico")}" width="560" height="auto" style="max-width: 100%; height: auto; border-radius: 8px; display: block; margin: 0 auto; object-fit: contain;">',
            "url": chart_url
        }
    
    print(f"   -> ⚠️  Advertencia: La función especialista para '{chart_type}' no devolvió una URL.")
    return None

def _generate_contribution_stack_chart(chart_config: dict, evidence_workspace: dict, file_name: str) -> str | None:
    title = chart_config.get("html_title", "Gráfico de Contribución")
    data_key = chart_config.get("data_key")
    print(f"  -> 🛠️ Generando gráfico de contribución: '{title}'")

    if not data_key or not evidence_workspace.get(data_key):
        print(f"    -> ❌ Error: No se encontró la clave de datos '{data_key}' en el workspace.")
        return None
    
    try:
        numeric_data = _extract_numeric_data(evidence_workspace[data_key])
        df = pd.DataFrame(numeric_data)

        # --- INICIO DE LA CORRECCIÓN ---
        # La columna de fecha se llama 'date', no 'timestamp'.
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        # --- FIN DE LA CORRECCIÓN ---
        
        # Excluimos la columna de fecha (que ahora es el índice) de los datos a graficar
        columns_to_plot = [col for col in df.columns if col not in ['date', 'timestamp', 'index']]

        figsize = chart_config.get("figsize", (12, 6))
        # Convertir lista a tupla si es necesario
        if isinstance(figsize, list):
            figsize = tuple(figsize)
        fig, ax = plt.subplots(figsize=figsize)
        ax.stackplot(df.index, df[columns_to_plot].T, labels=columns_to_plot) # Usamos las columnas filtradas
        
        ax.legend(loc='upper right')
        ax.set_title(title, fontsize=16)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Fecha')
        fig.autofmt_xdate()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        plt.close(fig)
        buf.seek(0)
        
        # La función add_rounded_corners no está en este archivo, asumo que existe en otra parte
        # Si no existe, puedes remover la línea y usar 'buf.getvalue()' directamente.
        # rounded_image_bytes = add_rounded_corners(buf, radius=20) 
        public_url = db.upload_file_to_storage("report-charts", file_name, buf.getvalue())
        print(f"  -> ✅ Archivo '{file_name}' subido a Supabase Storage.")
        return public_url
    except KeyError as e:
        print(f"    -> ❌ Error de Clave creando gráfico de contribución: La columna {e} no se encontró en los datos.")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"    -> ❌ Error creando o subiendo gráfico de contribución: {e}")
        traceback.print_exc()
        return None

def generate_custom_line_chart(chart_config: dict, evidence_workspace: dict, file_name: str) -> str | None:
    """
    (Versión Universal 2.0)
    Genera un gráfico de línea personalizado capaz de manejar uno o múltiples ejes Y,
    y múltiples series por cada eje.
    """
    # --- 1. CONFIGURACIÓN INICIAL ---
    title = chart_config.get("html_title", "Gráfico Personalizado")
    days_to_plot = chart_config.get("chart_period_days")
    axes_definitions = chart_config.get("axes", [])
    
    print(f"  -> 🛠️ Generando gráfico de línea: '{title}' con {len(axes_definitions)} eje(s) definidos.")

    if not axes_definitions:
        print("    -> ❌ Error: No se encontraron definiciones de 'axes' en la configuración.")
        return None

    try:
        # --- 2. PREPARACIÓN DE LA FIGURA Y EJES ---
        figsize = chart_config.get("figsize", (12, 6))
        # Convertir lista a tupla si es necesario
        if isinstance(figsize, list):
            figsize = tuple(figsize)
        fig, ax1 = plt.subplots(figsize=figsize)
        
        # Creamos una lista de los ejes que usaremos
        axes_list = [ax1]
        if len(axes_definitions) > 1:
            # Si se define más de un eje, creamos un "gemelo" en el lado derecho
            ax2 = ax1.twinx()
            axes_list.append(ax2)

        # Paleta de colores para que las series se vean distintas
        colors = ['#007BFF', '#DC3545', '#28A745', '#FFA500', '#6f42c1', '#17A2B8']
        color_index = 0

        # --- 3. BUCLE PRINCIPAL PARA DIBUJAR SERIES ---
        # Iteramos sobre cada definición de eje (ej: primero el del DXY, luego el del Diferencial)
        for i, axis_def in enumerate(axes_definitions):
            if i >= len(axes_list): continue # Seguridad por si hay más definiciones que ejes
            
            current_axis = axes_list[i] # ax1 para i=0, ax2 para i=1
            axis_name = axis_def.get("name", f"Eje {i+1}")
            
            # Asignamos color y etiqueta al nombre del eje
            axis_color = colors[color_index % len(colors)]
            current_axis.set_ylabel(axis_name, color=axis_color, fontsize=12)
            current_axis.tick_params(axis='y', labelcolor=axis_color)

            # Iteramos sobre cada serie dentro de la definición de este eje
            for series_info in axis_def.get("series", []):
                data_key = series_info.get("data_key")
                col_name = series_info.get("column_name", "value")
                label = series_info.get("display_name")
                style = series_info.get("style", "solid")
                
                series_data = evidence_workspace.get(data_key)
                if not series_data:
                    print(f"    -> ⚠️  Advertencia: No se encontró la fuente de datos '{data_key}' en el workspace.")
                    continue

                numeric_data = _extract_numeric_data(series_data)
                df = pd.DataFrame(numeric_data)
                # Usamos .get() para manejar la posible ausencia de 'date' o 'timestamp'
                df['timestamp'] = pd.to_datetime(df.get('date', df.get('timestamp')))
                df = df.set_index('timestamp')
                df.sort_index(ascending=True, inplace=True)

                df_to_plot = df.loc[df.index > (df.index.max() - pd.Timedelta(days=days_to_plot))] if days_to_plot else df

                if col_name in df_to_plot.columns:
                    current_axis.plot(
                        df_to_plot.index, 
                        df_to_plot[col_name], 
                        label=label, 
                        color=colors[color_index % len(colors)], 
                        linestyle=style
                    )
                    # Solo avanzamos el color si la serie se dibujó
                    color_index += 1
            
            # Si el primer eje solo tiene una serie, forzamos un color diferente para el segundo
            if i == 0 and len(axis_def.get("series", [])) > 0 :
                 color_index = 1


        # --- 4. LEYENDA Y ESTILO FINAL ---
        lines1, labels1 = axes_list[0].get_legend_handles_labels()
        lines2, labels2 = (axes_list[1].get_legend_handles_labels() if len(axes_list) > 1 else ([], []))
        
        # Combinamos las leyendas y las mostramos en la esquina superior izquierda
        axes_list[0].legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        axes_list[0].grid(True, alpha=0.3)
        axes_list[0].xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%y'))
        
        plt.xlabel('Fecha')
        fig.autofmt_xdate()
        plt.tight_layout()

        # --- 5. GUARDADO DE LA IMAGEN ---
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        plt.close(fig)
        buf.seek(0)
        
        rounded_image_bytes = add_rounded_corners(buf, radius=20)
        public_url = db.upload_file_to_storage("report-charts", file_name, rounded_image_bytes)
        print(f"  -> ✅ Archivo '{file_name}' subido a Supabase Storage.")
        return public_url

    except Exception as e:
        import traceback
        print(f"  -> ❌ Error crítico creando el gráfico personalizado: {e}")
        traceback.print_exc()
        return None
    
def add_rounded_corners(image_bytes: io.BytesIO, radius: int) -> bytes:
    """
    Toma una imagen en bytes, le añade esquinas redondeadas y la devuelve en bytes.
    """
    try:
        img = Image.open(image_bytes).convert("RGBA")
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0) + img.size, radius=radius, fill=255)
        img.putalpha(mask)
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    except Exception as e:
        print(f"    -> ⚠️  Advertencia: No se pudo aplicar el redondeo de esquinas. Devolviendo imagen original. Error: {e}")
        image_bytes.seek(0)
        return image_bytes.read()  
    
def generate_and_upload_clean_price_chart(df: pd.DataFrame, ticker: str, tech_params: dict) -> str | None:
    print(f"  -> 🛠️ Generando gráfico LIMPIO para el Chartista ({ticker})...")
    try:
        df_chart = df.copy()
        analysis_date = df_chart.index[-1].strftime('%Y-%m-%d')

        additional_plots = []
        for period in tech_params.get("moving_averages", []):
            ma_col = f'SMA_{period}'
            if ma_col in df_chart.columns:
                # Añade la media móvil al gráfico solo si la columna existe
                additional_plots.append(mpf.make_addplot(df_chart[ma_col]))

        buf = io.BytesIO()
        mpf.plot(df_chart, 
                 type='candle', 
                 style='charles', 
                 title=f'Acción del Precio para {ticker} ({analysis_date})', 
                 ylabel='Precio', 
                 addplot=additional_plots,  # Usa la lista dinámica de plots
                 figsize=(12, 7), 
                 savefig=dict(fname=buf, dpi=120))
        
        buf.seek(0)
        rounded_image_bytes = add_rounded_corners(buf, radius=20)
        file_name = f"clean_chart_{ticker.replace('.', '_')}_{analysis_date}.png"
        public_url = db.upload_file_to_storage("report-charts", file_name, rounded_image_bytes)
        print(f"    -> ✅ Gráfico limpio subido exitosamente.")
        return public_url
    except Exception as e:
        print(f"    -> ❌ Error generando gráfico limpio: {e}")
        return None

def generate_and_upload_full_indicator_chart(df: pd.DataFrame, ticker: str, tech_params: dict) -> str | None:
    print(f"  -> 🛠️ Generando gráfico COMPLETO para el Quant ({ticker})...")
    try:
        df_chart = df.copy()
        analysis_date = df_chart.index[-1].strftime('%Y-%m-%d')
        price_plots = [mpf.make_addplot(df_chart[['BB_Upper', 'BB_Lower']], color='gray', alpha=0.3), mpf.make_addplot(df_chart['SMA_20'], color='orange')]
        indicator_panels = [mpf.make_addplot(df_chart['RSI'], panel=1, color='purple', ylabel='RSI'), mpf.make_addplot(df_chart['MACD'], panel=2, color='blue', ylabel='MACD'), mpf.make_addplot(df_chart['MACD_Signal'], panel=2, color='orange', linestyle='--'), mpf.make_addplot(df_chart['MACD_Hist'], type='bar', panel=2, color='gray', alpha=0.5)]
        buf = io.BytesIO()
        mpf.plot(df_chart, type='candle', style='yahoo', title=f'Análisis de Indicadores para {ticker} ({analysis_date})', ylabel='Precio', addplot=price_plots + indicator_panels, panel_ratios=(4, 2, 2), figsize=(12, 10), savefig=dict(fname=buf, dpi=120))
        buf.seek(0)
        rounded_image_bytes = add_rounded_corners(buf, radius=20)
        file_name = f"indicator_chart_{ticker.replace('.', '_')}_{analysis_date}.png"
        public_url = db.upload_file_to_storage("report-charts", file_name, rounded_image_bytes)
        print(f"    -> ✅ Gráfico de indicadores subido exitosamente.")
        return public_url
    except Exception as e:
        print(f"    -> ❌ Error generando gráfico de indicadores: {e}")
        return None    
    
def generate_candlestick_chart(ohlc_data: list, chart_def: dict) -> str | None:
    """
    (Versión Corregida y Robusta)
    Genera un gráfico de velas, manejando la columna 'date' estandarizada.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    print(f"  -> 🛠️ Generando gráfico de velas...")
    try:
        if not ohlc_data: return None
        
        # Extraer datos numéricos de series enriquecidas
        if isinstance(ohlc_data, dict) and 'data' in ohlc_data:
            print(f"    -> 🔍 Detectada serie enriquecida con metadatos en candlestick. Extrayendo datos numéricos...")
            numeric_data = ohlc_data['data']
        else:
            numeric_data = ohlc_data
            
        df = pd.DataFrame(numeric_data)

        # --- INICIO DE LA CORRECCIÓN FINAL ---
        # Hacemos que la herramienta sea inteligente y busque 'date' primero.
        if 'date' not in df.columns:
            if 'timestamp' not in df.columns:
                raise KeyError(f"Falta una columna de fecha ('date' o 'timestamp'). Columnas: {df.columns.tolist()}")
            else:
                # Si encuentra 'timestamp' (legado), lo renombra a 'date'
                df.rename(columns={'timestamp': 'date'}, inplace=True)
        
        # La librería mplfinance espera que el índice se llame 'Date' (con mayúscula)
        df = df.rename(columns={'date': 'Date'})
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        # --- FIN DE LA CORRECCIÓN FINAL ---

        required_cols = {'open', 'high', 'low', 'close'}
        if not required_cols.issubset(df.columns):
            raise KeyError(f"Faltan columnas OHLC. Columnas: {df.columns.tolist()}")
        
        # Renombramos el resto de columnas a mayúsculas como espera mplfinance
        df = df.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low',
            'close': 'Close', 'volume': 'Volume'
        })

        additional_plots = []
        ma_periods = chart_def.get("moving_averages", [])
        if ma_periods:
            print(f"    -> Calculando y añadiendo medias móviles: {ma_periods}")
            for period in ma_periods:
                ma_col = f'SMA_{period}'
                df[ma_col] = df['Close'].rolling(window=period).mean()
                additional_plots.append(mpf.make_addplot(df[ma_col]))
        
        style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='-.')
        buf = io.BytesIO()
        
        html_title = chart_def.get("html_title", "Gráfico de Velas")
        safe_title = re.sub(r'[^a-zA-Z0-9_]', '', html_title).lower()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"{safe_title}_{timestamp}.png"
        # USAR PARÁMETRO DE LA BASE DE DATOS
        figsize = chart_def.get("figsize", (12, 6))
        # Convertir lista a tupla si es necesario
        if isinstance(figsize, list):
            figsize = tuple(figsize)

        # AJUSTAR MÁRGENES PARA CENTRAR EL CONTENIDO
        mpf.plot(df, type='candle', style=style, title="", addplot=additional_plots, volume=False, 
                figsize=figsize, 
                savefig=dict(fname=buf, dpi=120, bbox_inches='tight', pad_inches=0.1))
        buf.seek(0)
        
        rounded_image_bytes = add_rounded_corners(buf, radius=20)
        public_url = db.upload_file_to_storage("report-charts", file_name, rounded_image_bytes)
        print(f"  -> ✅ Archivo '{file_name}' subido a Supabase Storage.")
        return public_url

    except Exception as e:
        print(f"  -> ❌ Error creando o subiendo gráfico de velas: {e}")
        traceback.print_exc()
        return None


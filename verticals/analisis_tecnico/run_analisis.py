# experimentos/run_analysis.py
import os
import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import PIL.Image
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv
from quantex.config import Config
import google.generativeai as genai

# --- 1. CONFIGURACIÓN INICIAL ---
# Ajustamos la ruta para que encuentre el .env en la carpeta raíz de Quantex
print("--- Cargando configuración ---")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    EODHD_API_KEY = os.getenv("EODHD_API_KEY")
    if not GEMINI_API_KEY or not EODHD_API_KEY:
        raise ValueError("API Keys no encontradas en el archivo .env raíz.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    MODEL = genai.GenerativeModel('gemini-1.5-pro-latest')
    print("✅ Configuración cargada y modelo Gemini listo.")
except Exception as e:
    print(f"❌ Error en la configuración inicial: {e}")
    exit()

# --- 2. FUNCIONES AUXILIARES ---

def fetch_stock_data(ticker: str, api_key: str) -> pd.DataFrame | None:
    to_date = datetime.now()
    from_date = to_date - timedelta(days=365 * 2)
    # ✅ SEGURO: Obtener URL desde configuración
    api_url = f"{Config.get_eodhd_url()}/{ticker}?api_token={api_key}&fmt=json&from={from_date.strftime('%Y-%m-%d')}&to={to_date.strftime('%Y-%m-%d')}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        if not data: return None
        df = pd.DataFrame(data)
        df.columns = [col.capitalize() for col in df.columns]
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"  -> ❌ Error en fetch_stock_data para {ticker}: {e}")
        return None

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    delta = df['Close'].diff(1)
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100.0 - (100.0 / (1.0 + rs))
    return df

def generate_chart(df: pd.DataFrame, ticker: str, analysis_date: str) -> PIL.Image.Image | None:
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'Análisis Técnico para {ticker} ({analysis_date})', fontsize=16)
        
        ax1.plot(df.index, df['Close'], label='Precio de Cierre', color='blue')
        ax1.plot(df.index, df['SMA_20'], label='SMA 20', color='orange', linestyle='--')
        ax1.plot(df.index, df['SMA_50'], label='SMA 50', color='green', linestyle='--')
        ax1.set_ylabel('Precio')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(df.index, df['RSI'], label='RSI 14', color='purple')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylabel('RSI')
        ax2.set_ylim(0, 100)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return PIL.Image.open(buf)
    except Exception as e:
        print(f"  -> ❌ Error generando gráfico para {ticker}: {e}")
        return None

# --- 3. FLUJO PRINCIPAL DE EJECUCIÓN ---

def main():
    print("\n--- Iniciando Proceso de Análisis Autónomo ---")
    TICKERS_A_ANALIZAR = ['SQM-B.SN', 'CENCOSUD.SN', 'FALABELLA.SN']
    
    try:
        script_dir = os.path.dirname(__file__)
        prompt_path = os.path.join(script_dir, 'prompt_technical_analyst.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        print(f"❌ Error: No se encuentra el prompt en la ruta esperada: {prompt_path}")
        return

    for ticker in TICKERS_A_ANALIZAR:
        print(f"\n--- 📈 Analizando {ticker} ---")
        
        df_raw = fetch_stock_data(ticker, EODHD_API_KEY)
        if df_raw is None: continue
        
        df_indicators = calculate_indicators(df_raw)
        analysis_date = df_indicators.index[-1].strftime('%Y-%m-%d')

        chart_image = generate_chart(df_indicators.tail(252), ticker, analysis_date)
        if chart_image is None: continue

        prompt_text = prompt_template.replace("{{TICKER}}", ticker).replace("{{ANALYSIS_DATE}}", analysis_date)
        prompt_parts = [prompt_text, chart_image]
        
        print(f"  -> 🧠 Enviando prompt y gráfico a Gemini para {ticker}...")
        try:
            response = MODEL.generate_content(prompt_parts)
            report_text = response.text
            
            # --- LÍNEA CORREGIDA ---
            # Construimos la ruta completa para guardar el archivo en la misma carpeta del script
            file_name = f"analisis_{ticker.replace('.', '_')}_{analysis_date}.txt"
            output_filename = os.path.join(script_dir, file_name)
            
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"  -> ✅ Reporte para {ticker} guardado en '{output_filename}'")

        except Exception as e:
            print(f"  -> ❌ Error en la llamada a Gemini para {ticker}: {e}")

    print("\n--- Proceso de Análisis Finalizado ---")

if __name__ == "__main__":
    main()
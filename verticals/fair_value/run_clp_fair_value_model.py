# lab_fair_value.py (Versión 3.2 con Configuración Centralizada)

import os
import sys
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.data_fetcher import get_data_series

# --- CONFIGURACIÓN DEL MODELO (MODIFICA AQUÍ PARA EXPERIMENTAR) ---
MODEL_CONFIG = {
    "target_variable": "USDCLP.FOREX",
    "predictor_variables": [
        
        "lme",
        "LATAM Currencies",
        "EEM Currencies",
        "chile_country_risk_10y",
        "Rate_Spread_2Y"  # Este es un campo calculado, no se busca directamente
    ],
    "spread_calculation": {
        "output_name": "Rate_Spread_2Y",
        "component_1": "Benchmark BTP 2 años",
        "component_2": "US2Y.GBOND"
    },
    "days_of_history": 1300
}
# ---------------------------------------------------------------------

def get_clp_model_data():
    """
    Recolecta y prepara los datos para el modelo basado en MODEL_CONFIG.
    """
    print("--- ⚙️  Fase 1: Recolectando datos del modelo... ---")
    
    # Construye la lista de series a buscar dinámicamente desde la configuración
    series_to_fetch = [MODEL_CONFIG["target_variable"]] + \
                      [p for p in MODEL_CONFIG["predictor_variables"] if p != MODEL_CONFIG["spread_calculation"]["output_name"]] + \
                      [MODEL_CONFIG["spread_calculation"]["component_1"], MODEL_CONFIG["spread_calculation"]["component_2"]]
    
    all_series_dfs = []
    for name in set(series_to_fetch): # Usamos set para evitar duplicados
        print(f"    -> 📥 Obteniendo datos para: '{name}'")
        df = get_data_series(identifier=name, days=MODEL_CONFIG["days_of_history"])
        if df is not None and not df.empty:
            all_series_dfs.append(df[['close']].rename(columns={'close': name}))
    
    if not all_series_dfs: return None
    
    master_df = pd.concat(all_series_dfs, axis=1, join='outer').ffill().dropna()
    
    # Calcula el spread usando los nombres de la configuración
    spread_config = MODEL_CONFIG["spread_calculation"]
    master_df[spread_config["output_name"]] = master_df[spread_config["component_1"]] - master_df[spread_config["component_2"]]
    
    print("--- ✅ Fase 1 Completada: Datos listos para el modelo. ---")
    return master_df

def generate_model_report_html(model, X, Y, last_predictors):
    """
    Genera un reporte HTML completo a partir de los resultados del modelo.
    """
    print(" -> 📄 Generando reporte HTML del modelo...")
    
    predicted_value = model.predict(last_predictors)[0]
    last_real_value = Y.iloc[-1]
    
    coefficients = model.params
    contrib_html = "<table><tr><th>Variable</th><th>Contribución</th><th>Valor Actual</th><th>Coeficiente</th></tr>"
    total_contribution = 0
    for var in coefficients.index:
        value = last_predictors.get(var, 1) # Usamos .get para manejar 'const' de forma segura
        contribution = value * coefficients[var]
        contrib_html += f"<tr><td>{var}</td><td>{contribution:.2f}</td><td>{value:.2f}</td><td>{coefficients[var]:.4f}</td></tr>"
        total_contribution += contribution
    contrib_html += f"<tr><td><b>Fair Value (Suma)</b></td><td><b>{total_contribution:.2f}</b></td><td></td><td></td></tr></table>"

    # --- GRÁFICO 1: FAIR VALUE VS. PRECIO REAL ---
    df_chart_fv = pd.DataFrame({'Precio Mercado': Y, 'Fair Value (Modelo)': model.fittedvalues})
    
    plt.style.use('dark_background')
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(df_chart_fv.index, df_chart_fv['Precio Mercado'], label='Precio de Mercado', color='#007BFF', linewidth=2)
    ax1.plot(df_chart_fv.index, df_chart_fv['Fair Value (Modelo)'], label='Fair Value (Modelo)', color='#FFA500', linestyle='--')
    
    ax1.set_title('Precio de Mercado vs. Fair Value del Modelo', fontsize=16)
    ax1.set_ylabel('Precio USD/CLP', fontsize=12)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.3)
    fig1.autofmt_xdate()
    
    chart_path_fv = 'reporte_fair_value_chart.png'
    fig1.savefig(chart_path_fv, dpi=100, bbox_inches='tight')
    plt.close(fig1)

    # --- INICIO DE LA CORRECCIÓN: GRÁFICO DE LÍNEAS DE CONTRIBUCIONES ---
    print(" -> 📊 Generando gráfico de contribuciones (versión de líneas)...")
    contrib_df = pd.DataFrame(index=X.index)
    for var in coefficients.index:
        contrib_df[var] = X[var] * coefficients[var] if var != 'const' else coefficients[var]

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    
    # Graficamos cada contribución como una línea separada
    for column in contrib_df.columns:
        ax2.plot(contrib_df.index, contrib_df[column], label=column)
    
    ax2.set_title('Contribución Histórica de Variables al Fair Value', fontsize=16)
    ax2.set_ylabel('Impacto en Precio USD/CLP', fontsize=12)
    ax2.legend(loc='upper left')
    ax2.grid(True, linestyle='--', alpha=0.3)
    fig2.autofmt_xdate()
    
    chart_path_contrib = 'reporte_contribuciones_chart.png'
    fig2.savefig(chart_path_contrib, dpi=100, bbox_inches='tight')
    plt.close(fig2)
    # --- FIN DE LA CORRECCIÓN ---

    summary_html = model.summary().as_html()
    html_template = f"""
    <html><head><title>Reporte de Regresión Fair Value</title>
    <style>
        body {{ font-family: sans-serif; background-color: #1a1a1a; color: #e0e0e0; padding: 20px; }}
        h1, h2 {{ color: #007BFF; border-bottom: 2px solid #007BFF; padding-bottom: 10px; }}
        .summary-box {{ border: 1px solid #444; padding: 15px; margin-bottom: 20px; background-color: #2c2c2c; border-radius: 8px; }}
        .summary-box p {{ margin: 5px 0; font-size: 1.2em; }}
        table {{ border-collapse: collapse; width: auto; margin: 20px 0; font-size: 0.9em; }}
        th, td {{ border: 1px solid #444; padding: 8px; text-align: right; }}
        th {{ background-color: #007BFF; color: white; text-align: center; }}
        td:first-child {{ text-align: left; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin-top: 10px; }}
    </style></head><body>
        <h1>🔬 Reporte de Laboratorio: Modelo Fair Value CLP</h1>
        <p>Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="summary-box">
            <h2>Veredicto (Último Día)</h2>
            <p><b>Precio de Mercado Actual:</b> {last_real_value:.2f}</p>
            <p><b>Fair Value (Modelo):</b> {predicted_value:.2f}</p>
        </div>
        <h2>Gráfico de Desempeño del Modelo</h2>
        <img src="{chart_path_fv}" alt="Gráfico de Fair Value">
        <h2>Gráfico de Contribución de Variables</h2>
        <img src="{chart_path_contrib}" alt="Gráfico de Contribuciones">
        <h2>Tabla de Contribuciones (Último Día)</h2>
        {contrib_html}
        <h2>Resumen Estadístico Completo (OLS)</h2>
        {summary_html}
    </body></html>
    """
    
    report_filename = "reporte_regresion.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"\n--- ✅ Reporte Finalizado. Abre el archivo '{report_filename}' en tu navegador. ---")

def run_and_analyze_model(model_df: pd.DataFrame):
    """
    Ejecuta la regresión OLS y genera los resultados leyendo desde MODEL_CONFIG.
    """
    print("\n--- ⚙️  Fase 2: Ejecutando Regresión OLS... ---")
    
    # Lee la configuración del modelo desde el diccionario
    Y = model_df[MODEL_CONFIG["target_variable"]]
    X = model_df[MODEL_CONFIG["predictor_variables"]]
    X = sm.add_constant(X)

    model = sm.OLS(Y, X).fit()
    
    print("\n--- 📊 RESUMEN DEL MODELO (CONSOLA) 📊 ---")
    print(model.summary())
    print("------------------------------------------")

    last_predictors = X.iloc[-1]
    generate_model_report_html(model, X, Y, last_predictors)


if __name__ == "__main__":
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    dataframe_modelo = get_clp_model_data()
    if dataframe_modelo is not None and not dataframe_modelo.empty:
        run_and_analyze_model(dataframe_modelo)
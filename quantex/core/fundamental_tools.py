# quantex/core/fundamental_tools.py (Versión Definitiva con Gráficos y Resumen)

import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import io
import requests
import PIL.Image

from datetime import datetime
from . import database_manager as db # Usamos el import relativo
from . import llm_manager



def _get_standardized_betas(model_results, X_df, Y_series) -> list:
    """Calcula los coeficientes beta estandarizados y los devuelve como una lista de diccionarios."""
    std_dev_x = X_df.std()
    std_dev_y = Y_series.std()
    unstandardized_coeffs = model_results.params
    
    betas = {
        var: coeff * (std_dev_x[var] / std_dev_y) 
        for var, coeff in unstandardized_coeffs.items() if var != 'const'
    }
    
    betas_list = [{"variable": var, "beta_estandarizado": beta} for var, beta in betas.items()]
    # Ordenar por el valor absoluto del beta, de mayor a menor
    betas_list.sort(key=lambda x: abs(x["beta_estandarizado"]), reverse=True)
    return betas_list

def _generate_fair_value_chart(df: pd.DataFrame, model_results, X) -> str | None:
    """Genera un gráfico de Real vs. Estimado y lo sube a Supabase."""
    try:
        print("    -> 📊 Generando gráfico de Fair Value...")
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['CLP'], label='CLP Observado', color='blue', alpha=0.8, linewidth=1.5)
        ax.plot(df.index, model_results.predict(X), label='CLP Estimado (Fair Value)', color='red', linestyle='--', linewidth=1.5)
        ax.set_title('CLP: Valor Observado vs. Fair Value Estimado por Modelo', fontsize=16)
        ax.set_ylabel('Valor (USD/CLP)')
        ax.legend()
        fig.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        plt.close(fig)
        
        file_name = f"fair_value_clp_{datetime.now().strftime('%Y%m%d')}.png"
        chart_url = db.upload_file_to_storage("report-charts", file_name, buf.getvalue())
        print("    -> ✅ Gráfico de Fair Value subido exitosamente.")
        return chart_url
    except Exception as e:
        print(f"    -> ❌ Error generando gráfico de Fair Value: {e}")
        return None
    
def _generate_contribution_chart(df: pd.DataFrame, model_results, X_df) -> str | None:
    """Genera un gráfico de contribución de componentes y lo sube a Supabase."""
    try:
        print("    -> 📊 Generando gráfico de Contribución de Componentes...")
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(12, 6))

        # Crear un DataFrame con la contribución de cada variable
        contrib_df = pd.DataFrame(index=X_df.index)
        for var in model_results.params.index:
            if var == 'const':
                contrib_df[var] = model_results.params[var]
            else:
                contrib_df[var] = X_df[var] * model_results.params[var]
        
        # Graficar el stackplot
        ax.stackplot(contrib_df.index, contrib_df.T, labels=contrib_df.columns)
        
        ax.set_title('Contribución de cada Variable al Fair Value del CLP', fontsize=16)
        ax.set_ylabel('Valor (USD/CLP)')
        ax.legend(loc='upper left')
        fig.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        plt.close(fig)
        
        file_name = f"contribution_clp_{datetime.now().strftime('%Y%m%d')}.png"
        chart_url = db.upload_file_to_storage("report-charts", file_name, buf.getvalue())
        print("    -> ✅ Gráfico de Contribución subido exitosamente.")
        return chart_url
    except Exception as e:
        print(f"    -> ❌ Error generando gráfico de Contribución: {e}")
        return None

def run_clp_fair_value_analysis(evidence_workspace: dict) -> dict | None:
    """
    Ejecuta un modelo de regresión para el CLP y devuelve un análisis conciso
    con texto, los dos gráficos solicitados y métricas clave.
    """
    print("  -> 🤖 Ejecutando Especialista de Fair Value para el CLP (v5 - dos gráficos)...")
    try:
        # --- PASO 1: Consolidar datos y ejecutar modelo OLS (Lógica sin cambios) ---
        print("    -> ⚙️  Consolidando datos y ejecutando modelo OLS...")
        required_series = ['LME', 'DXY', 'BTU 2027', 'US 2 Year Treasury', 'Chile Country Risk 5Y', 'CLP']
        all_series_dfs = []
        for series_name in required_series:
            series_data = evidence_workspace.get(f"data_{series_name}")
            if not series_data: continue
            df = pd.DataFrame(series_data)
            if df.empty: continue
            date_col = 'timestamp' if 'timestamp' in df.columns else 'Date'
            value_col = 'value' if 'value' in df.columns else 'Close'
            if date_col not in df.columns or value_col not in df.columns: continue
            df.rename(columns={date_col: 'timestamp', value_col: series_name}, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
            df.set_index('timestamp', inplace=True)
            all_series_dfs.append(df[[series_name]])
        if not all_series_dfs: raise ValueError("La lista de DataFrames está vacía.")
        master_df = pd.concat(all_series_dfs, axis=1, join='outer').ffill().dropna()
        master_df.rename(columns={'LME': 'Copper_Price', 'BTU 2027': 'Chilean_Rate_2Y', 'US 2 Year Treasury': 'US_Rate_2Y', 'Chile Country Risk 5Y': 'Country_Risk_CDS_5Y'}, inplace=True)
        master_df['Rate_Spread_2Y'] = master_df['Chilean_Rate_2Y'] - master_df['US_Rate_2Y']
        master_df.dropna(inplace=True)
        Y = master_df['CLP']
        X = master_df[['Copper_Price', 'DXY', 'Chilean_Rate_2Y', 'Country_Risk_CDS_5Y', 'Rate_Spread_2Y']]
        X = sm.add_constant(X)
        model_results = sm.OLS(Y, X).fit()
        print("    -> ✅ Modelo OLS ejecutado.")
        
        # --- PASO 2: Generar y subir AMBOS gráficos ---
        grafico_fv_url = _generate_fair_value_chart(master_df, model_results, X)
        grafico_contrib_url = _generate_contribution_chart(master_df, model_results, X)
        
        # --- PASO 3: Construir el texto de resumen y la fórmula ---
        predicted_value = model_results.predict(X.iloc[[-1]])[0]
        last_real_value = Y.iloc[-1]
        
        fair_value_text = (
            f"El modelo de Fair Value estima un valor para el CLP de ${predicted_value:,.2f}. "
            f"El valor de mercado actual es ${last_real_value:,.2f}, lo que sugiere que el peso chileno está "
            f"actualmente un {abs(1 - last_real_value/predicted_value):.2%} "
            f"{'por debajo de (subvaluado)' if last_real_value > predicted_value else 'por encima de (sobrevaluado)'} "
            f"su valor fundamental estimado."
        )

        formula = f"CLP = {model_results.params['const']:.2f} "
        for var, coeff in model_results.params.items():
            if var != 'const':
                sign = "+" if coeff >= 0 else "-"
                formula += f"{sign} {abs(coeff):.2f} * {var} "

        # --- PASO 4: Construir el resultado final con el nuevo formato ---
        final_result = {
            "resumen_modelo": fair_value_text,
            "formula_del_modelo": formula.strip(),
            "grafico_fair_value_url": grafico_fv_url,
            "grafico_contribucion_url": grafico_contrib_url, # <-- NUEVO CAMPO
            "metricas_clave": {
                "valor_real": round(last_real_value, 2),
                "valor_estimado_modelo": round(predicted_value, 2)
            }
        }
        
        print("    -> ✅ Análisis de Fair Value (v5) con dos gráficos completado.")
        return final_result

    except Exception as e:
        print(f"    -> ❌ Error en run_clp_fair_value_analysis: {e}")
        traceback.print_exc()
        return {"error": str(e)}
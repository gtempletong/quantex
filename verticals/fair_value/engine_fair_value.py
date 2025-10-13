# quantex/verticals/fair_value/engine_fair_value.py

import os
import sys
import json
import traceback
import pandas as pd
import statsmodels.api as sm
import dpath.util
from flask import jsonify
from jinja2 import Environment, FileSystemLoader

# --- Importaciones de Servicios Centrales y Herramientas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core import llm_manager
from quantex.core.data_fetcher import get_data_series
from quantex.core.tool_registry import registry
from quantex.core.dossier import Dossier
from quantex.core.agent_tools import get_file_content

# --- Herramienta Específica de esta Vertical (El Modelo) ---

@registry.register(name="run_clp_fair_value_model")
def run_clp_fair_value_model(evidence_workspace: dict, params: dict) -> dict:
    """
    (Versión Dinámica)
    Ejecuta el modelo OLS leyendo todos los parámetros desde la receta.
    """
    print("  -> 🛠️  [Herramienta Fair Value] Ejecutando el modelo de regresión OLS...")
    try:
        master_df = evidence_workspace.get("master_df").copy()
        report_def = evidence_workspace.get("report_def")
        
        if master_df is None or report_def is None:
            raise ValueError("El workspace no contiene 'master_df' o 'report_def'.")

        data_reqs = report_def.get("data_requirements", {})
        predictor_tickers = data_reqs.get("predictor_series", [])
        target_ticker = data_reqs.get("target_series")
        
        # --- INICIO DE LA CORRECCIÓN ---
        # Leemos los componentes del spread desde la receta
        spread_config = data_reqs.get("spread_components", {})
        series_1_ticker = spread_config.get("series_1")
        series_2_ticker = spread_config.get("series_2")

        if not all([predictor_tickers, target_ticker, series_1_ticker, series_2_ticker]):
            raise ValueError("La receta no define 'predictor_series', 'target_series' o 'spread_components'.")

        # Calculamos el spread usando los nombres leídos de la receta
        master_df['Rate_Spread_2Y'] = master_df[series_1_ticker] - master_df[series_2_ticker]
        # --- FIN DE LA CORRECCIÓN ---
        
        Y = master_df[target_ticker]
        
        predictor_cols_for_model = [t for t in predictor_tickers if t in master_df.columns] + ['Rate_Spread_2Y']
        X = sm.add_constant(master_df[predictor_cols_for_model])
        
        model_results = sm.OLS(Y, X).fit()
        print("    -> ✅ Modelo OLS ejecutado exitosamente.")

        results_packet = {}
        last_real_value = Y.iloc[-1]
        predicted_value = model_results.predict(X.iloc[-1:])[0]
        
        results_packet['summary_fair_value_summary'] = {
            "last_close": round(last_real_value, 2),
            "last_fair_value": round(predicted_value, 2)
        }

        master_df['fair_value'] = model_results.predict(X)
        df_fv_chart = master_df[[target_ticker, 'fair_value']].rename(columns={target_ticker: 'Precio de Mercado'})
        df_fv_chart.reset_index(inplace=True)
        df_fv_chart['date'] = pd.to_datetime(df_fv_chart['date']).dt.strftime('%Y-%m-%dT%H:%M:%S')
        results_packet['fair_value_model_results'] = df_fv_chart.to_dict('records')
        
        return results_packet

    except Exception as e:
        print(f"    -> ❌ Error en run_clp_fair_value_model: {e}")
        traceback.print_exc()
        return {"error": str(e)}

# --- FUNCIÓN DE ENTRADA PÚBLICA DE LA VERTICAL ---

def run(parameters: dict) -> dict:
    """
    Función principal de la vertical Fair Value (Versión Línea de Ensamblaje Completa).
    """
    print("✅ [Vertical Fair Value] Iniciando ejecución completa...")
    workspace = {}
    try:
        # --- ESTACIÓN 1: LEER LA RECETA ---
        report_keyword = parameters.get("report_keyword")
        report_def = db.get_report_definition_by_topic(report_keyword)
        if not report_def: raise Exception(f"No se encontró definición para '{report_keyword}'.")
        workspace['report_def'] = report_def

        # --- ESTACIÓN 2: OBTENER MATERIA PRIMA ---
        print("  -> 🚚 [Fair Value] Obteniendo materia prima con data_fetcher...")
        market_data_series = report_def.get("market_data_series", [])
        all_series_dfs = []
        for series_req in market_data_series:
            ticker = series_req.get("name")
            if not ticker: continue
            
            df = get_data_series(identifier=ticker, days=1095)
            if df is not None and not df.empty:
                all_series_dfs.append(df[['close']].rename(columns={'close': ticker}))
        
        if not all_series_dfs: raise ValueError("No se pudieron cargar los datos de las series.")
        
        master_df = pd.concat(all_series_dfs, axis=1, join='outer').ffill().dropna()
        workspace['master_df'] = master_df
        print("  -> ✅ Materia prima consolidada.")

        # --- ESTACIÓN 3: TALLER (PROCESAMIENTO DEL MODELO) ---
        print("  -> 🏭 [Fair Value] Ejecutando processing_pipeline...")
        # Espía de receta cargada en runtime
        try:
            data_requirements_spy = report_def.get("data_requirements", {})
            print(f"    -> 🕵️ data_requirements: {json.dumps(data_requirements_spy, ensure_ascii=False)}")
        except Exception:
            pass

        processing_pipeline = report_def.get("processing_pipeline", [])
        try:
            print(f"    -> 🕵️ processing_pipeline: {json.dumps(processing_pipeline, ensure_ascii=False)}")
        except Exception:
            print("    -> 🕵️ processing_pipeline: [objeto no serializable]")
        for step in processing_pipeline:
            tool_name = step.get("tool_name")
            params = step.get("parameters", {})
            output_key = step.get("output_key")
            
            tool_function = registry.get(tool_name)
            if tool_function:
                # Compatibilidad: herramientas pueden aceptar 'evidence_workspace' o 'workspace'.
                try:
                    result = tool_function(evidence_workspace=workspace, params=params)
                except TypeError:
                    result = tool_function(workspace=workspace, params=params)
                if result and output_key:
                    workspace[output_key] = result
        print("  -> ✅ Modelo procesado y resultado guardado en workspace.")

        # --- ESTACIÓN 4: SÍNTESIS IA ---
        print("  -> 🧠 [Fair Value] Ejecutando synthesis_pipeline...")
        dossier = Dossier()
        synthesis_pipeline = report_def.get("synthesis_pipeline", [])
        for step in synthesis_pipeline:
            agent_name = step.get("agent_name")
            prompt_file = step.get("prompt_file")
            inputs = step.get("inputs", [])
            
            context_for_agent = {key: workspace.get(key) for key in inputs}
            prompt_context = context_for_agent.get('fair_value_results', {}).get('summary_fair_value_summary', {})

            prompt_template = get_file_content(prompt_file)
            source_data_str = json.dumps(prompt_context, indent=2, default=str)
            user_prompt = prompt_template.replace('{source_data}', source_data_str)

            output_schema = report_def.get("output_schema", {})
            
            synthesis_result = llm_manager.generate_structured_output(
                system_prompt=get_file_content("prompts/core_identity.txt"),
                user_prompt=user_prompt,
                model_name=llm_manager.MODEL_CONFIG['complex']['primary'],
                output_schema=output_schema
            )
            if not synthesis_result: raise Exception("La síntesis de IA falló.")
            dossier.ai_content = synthesis_result
        print("  -> ✅ Síntesis de IA completada.")

        # --- ESTACIÓN 5: VISUALIZACIÓN (LÓGICA CORREGIDA Y SEGURA) ---
        print("  -> 🎨 [Fair Value] Ejecutando visualization_pipeline...")
        visualization_pipeline = report_def.get("visualization_pipeline", [])
        for step in visualization_pipeline:
            tool_name = step.get("tool_name")
            params = step.get("parameters", {}).copy() # Usamos .copy() para modificar los parámetros de forma segura
            tool_function = registry.get(tool_name)
            
            if tool_function:
                # Preparamos un workspace limpio para cada herramienta de visualización
                viz_workspace = {}
                
                # Para el gráfico custom_line_chart, que necesita datos anidados
                if params.get("chart_type") == "custom_line_chart":
                    for axis in params.get("axes", []):
                        for series in axis.get("series", []):
                            data_key_anidada = series.get("data_key")
                            if data_key_anidada and '.' in data_key_anidada:
                                try:
                                    nested_data = dpath.util.get(workspace, data_key_anidada, separator='.')
                                    # Creamos una clave simple en el workspace temporal
                                    clave_simple = data_key_anidada.replace('.', '_')
                                    viz_workspace[clave_simple] = nested_data
                                    # Actualizamos la receta al vuelo para usar la clave simple
                                    series['data_key'] = clave_simple
                                except KeyError:
                                    pass # La herramienta interna manejará el dato faltante

                viz_result = tool_function(evidence_workspace=viz_workspace, params=params)
                if viz_result:
                    dossier.add_visualization(viz_result)

        print("  -> ✅ Gráficos generados.")
        
        # --- ESTACIÓN 6: ENSAMBLAJE FINAL Y GUARDADO ---
        template_path = report_def.get("template_file")
        template_dir = os.path.dirname(os.path.join(PROJECT_ROOT, template_path))
        template_name = os.path.basename(template_path)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)
        
        # Agregamos los resúmenes numéricos al dossier para la plantilla
        if workspace.get("fair_value_results"):
            dossier.add_summary("summary_fair_value_summary", workspace["fair_value_results"].get("summary_fair_value_summary", {}))
        
        # Preparamos el contexto y renderizamos el HTML final
        template_context = dossier.to_dict()
        template_context.update(dossier.ai_content)
        final_html = template.render(template_context)
        
        # Preparamos el paquete de resultados DEFINITIVO Y ÚNICO
        # llamando a nuestro método to_dict() que empaqueta todo correctamente.
        final_results_packet = dossier.to_dict()

        # Realizamos UNA ÚNICA LLAMADA para guardar el artefacto
        new_artifact = db.insert_generated_artifact(
            report_keyword=report_keyword, artifact_content=final_html,
            artifact_type=f'report_{report_keyword.replace(" ", "_")}_final',
            results_packet=final_results_packet # <-- Usamos el paquete completo y correcto
        )
        
      
        return jsonify({
            "response_blocks": [
                {"type": "html", "content": final_html, "display_target": "panel"},
                {"type": "text", "content": f"✅ Análisis de Fair Value para '{report_keyword}' completado.", "display_target": "chat"}
            ], "artifact_id": new_artifact['id'] if new_artifact else None
        })

    except Exception as e:
        error_message = f"❌ [Vertical Fair Value] Error crítico: {e}"
        print(error_message)
        traceback.print_exc()
        return jsonify({"response_blocks": [{"type": "text", "content": error_message}]})
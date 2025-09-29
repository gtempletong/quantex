# quantex/verticals/analisis_tecnico/engine_technical_committee.py

import os
import sys
import json
import pandas as pd
import requests
import PIL.Image
import io
import traceback
from flask import jsonify
from jinja2 import Environment, FileSystemLoader

# --- Importaciones de Servicios Centrales y Herramientas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core import llm_manager
from quantex.core.data_fetcher import get_data_series 
from quantex.core.tools.technical_tools import calculate_all_indicators
from quantex.core.tools.visualization_tools import generate_and_upload_clean_price_chart, generate_and_upload_full_indicator_chart

# --- Lógica Interna de la Vertical ---

def _prepare_technical_dossier(ticker: str, report_definition: dict) -> dict | None:
    """Prepara un portafolio de gráficos estratégicos y tácticos para el comité."""
    print(f"  -> 🕵️  [Vertical Tec] Preparando portafolio de gráficos para {ticker}...")
    try:
        # --- INICIO DE LA MODIFICACIÓN: Definir periodos ---
        strategic_days = 500
        tactical_days = 120
        # --- FIN DE LA MODIFICACIÓN ---

        data_reqs_str = report_definition.get("data_requirements", "{}")
        data_reqs = json.loads(data_reqs_str) if isinstance(data_reqs_str, str) else data_reqs_str
        
        tech_params = data_reqs.get("technical_analysis_params", {})
        moving_averages = tech_params.get("moving_averages", [])
        longest_ma_period = max(moving_averages) if moving_averages else 0
        
        # Obtenemos datos una sola vez usando el periodo más largo
        days_to_fetch = strategic_days + longest_ma_period

        df_raw = get_data_series(identifier=ticker, days=days_to_fetch)
        if df_raw is None or df_raw.empty: 
            raise Exception(f"No se pudieron obtener los datos para '{ticker}' desde el data_fetcher.")
            
        df_indicators = calculate_all_indicators(df_raw)
        if df_indicators is None or df_indicators.empty: 
            raise Exception(f"El cálculo de indicadores resultó en un DataFrame vacío para {ticker}.")

        # --- INICIO DE LA MODIFICACIÓN: Generar ambos gráficos ---
        
        # 1. Gráfico Estratégico (Usa todos los datos de 'strategic_days')
        df_strategic_chart_data = df_indicators.tail(strategic_days)
        strategic_chart_url = generate_and_upload_full_indicator_chart(df_strategic_chart_data, f"{ticker}_Strategic", tech_params)

        # 2. Gráfico Táctico (Usa solo los últimos 'tactical_days')
        df_tactical_chart_data = df_indicators.tail(tactical_days)
        tactical_chart_url = generate_and_upload_full_indicator_chart(df_tactical_chart_data, f"{ticker}_Tactical", tech_params)
        
        # --- FIN DE LA MODIFICACIÓN ---

        if not strategic_chart_url or not tactical_chart_url:
            raise Exception("Fallo en la generación o subida de uno o más gráficos.")

        # --- INICIO DE LA MODIFICACIÓN: Actualizar el dossier de salida ---
        dossier = {
            "ticker": ticker,
            "analysis_date": df_indicators.index[-1].strftime('%Y-%m-%d'),
            "numerical_data": df_indicators.iloc[-1].to_dict(),
            "chart_url_strategic": strategic_chart_url,
            "chart_url_tactical": tactical_chart_url
        }
        # --- FIN DE LA MODIFICACIÓN ---
        
        print(f"  -> ✅ [Vertical Tec] Dossier con gráficos para {ticker} preparado.")
        return dossier
    except Exception as e:
        print(f"  -> ❌ Error en _prepare_technical_dossier: {e}")
        traceback.print_exc()
        return None

def _run_investment_committee(dossier: dict, report_definition: dict) -> dict | None:
    """Ejecuta el pipeline de especialistas de IA (Chartista, Quant, CIO)."""
    print(f"  -> 🤖 [Vertical Tec] Ejecutando comité para {dossier.get('ticker')}...")
    try:
        synthesis_pipeline_str = report_definition.get("synthesis_pipeline", "[]")
        synthesis_pipeline = json.loads(synthesis_pipeline_str) if isinstance(synthesis_pipeline_str, str) else synthesis_pipeline_str
        
        output_schema_str = report_definition.get('output_schema', '{}')
        output_schema = json.loads(output_schema_str) if isinstance(output_schema_str, str) else output_schema_str

        if not synthesis_pipeline:
            raise ValueError("Pipeline de síntesis no definido en la receta.")

        chained_context = dossier.copy()

        for specialist in synthesis_pipeline:
            specialist_name = specialist.get("specialist_name")
            prompt_file_path = specialist.get("prompt_file")
            inputs = specialist.get("inputs", [])
            
            print(f"    -> 🗣️  Llamando al especialista: '{specialist_name}'...")
            
            context_for_specialist = {key: chained_context.get(key) for key in inputs}

            # --- INICIO DE LA MODIFICACIÓN: Añadir contexto explícito para el CIO ---
            if specialist_name in ["Jefe de Mesa (CIO)", "CIO"]:
                context_for_specialist['ticker'] = chained_context.get('ticker')
                context_for_specialist['analysis_date'] = chained_context.get('analysis_date')
                
                # Cargar expert_view_anterior para el CIO
                ticker = chained_context.get('ticker')
                if ticker:
                    # Detectar tipo de comité basado en el ticker
                    if ticker == "USDCLP.FOREX":
                        cio_key = "cio_clp"
                        comite_type = "CLP"
                    elif ticker == "HG=F":
                        cio_key = "cio_cobre"
                        comite_type = "Cobre"
                    else:
                        cio_key = f"cio_{ticker}"
                        comite_type = "Mercado"
                    
                    expert_context = db.get_expert_context(cio_key)
                    if expert_context:
                        context_for_specialist['expert_view_anterior'] = {
                            "current_view_label": expert_context.get("current_view_label"),
                            "core_thesis_summary": expert_context.get("core_thesis_summary")
                        }
                        print(f"    -> 🧠 Cargando memoria del CIO para {comite_type} ({ticker})")
                    else:
                        print(f"    -> 🟡 No se encontró memoria anterior del CIO para {comite_type} ({ticker})")
            # --- FIN DE LA MODIFICACIÓN ---
            
            full_prompt_path = os.path.join(PROJECT_ROOT, prompt_file_path)
            with open(full_prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            source_data_str = json.dumps(context_for_specialist, indent=2, default=str)
            user_prompt = prompt_template.replace('{source_data}', source_data_str)
            
            images_for_prompt = []
            # --- INICIO DE LA MODIFICACIÓN: Lógica de asignación de gráficos ---
            if specialist_name == "Chartista" and "chart_url_strategic" in chained_context:
                print("    -> 🖼️  Adjuntando gráfico estratégico para el Chartista...")
                response = requests.get(chained_context["chart_url_strategic"])
                if response.status_code == 200:
                    images_for_prompt.append(PIL.Image.open(io.BytesIO(response.content)))

            elif specialist_name == "Quant" and "chart_url_tactical" in chained_context:
                print("    -> 🖼️  Adjuntando gráfico táctico para el Quant Visual...")
                response = requests.get(chained_context["chart_url_tactical"])
                if response.status_code == 200:
                    images_for_prompt.append(PIL.Image.open(io.BytesIO(response.content)))
            # --- FIN DE LA MODIFICACIÓN ---                    

            structured_data = llm_manager.generate_structured_output(
                system_prompt=None, 
                user_prompt=user_prompt,
                model_name=llm_manager.MODEL_CONFIG.get('committee_synthesis', {}).get('primary'),
                output_schema=output_schema,
                images=images_for_prompt,
                force_json_output=False
            )

            if not structured_data:
                raise Exception(f"El especialista '{specialist_name}' no pudo generar una salida válida.")

            chained_context.update(structured_data)
        
        print(f"  -> ✅ [Vertical Tec] Veredicto del comité para {dossier.get('ticker')} finalizado.")
        return chained_context
    except Exception as e:
        print(f"  -> ❌ Error en _run_investment_committee: {e}")
        traceback.print_exc()
        return None

def _create_committee_html_report(committee_results: dict, template_path: str) -> str:
    """
    (Versión Corregida)
    Renderiza el resultado del comité, buscando las nuevas claves de URL de los gráficos
    estratégico y táctico.
    """
    print("  -> 🎨 [Vertical Tec] Ensamblando informe final con estructura de gráficos corregida...")
    try:
        full_template_path = os.path.join(PROJECT_ROOT, template_path)
        template_dir = os.path.dirname(full_template_path)
        template_name = os.path.basename(full_template_path)
        
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)

        # --- INICIO DE LA CORRECCIÓN ---
        # Construimos el diccionario para la plantilla, asegurando que todos los
        # campos, incluyendo las nuevas URLs de los gráficos, estén presentes.
        contenido_para_plantilla = {
            "ticker": committee_results.get("ticker", "N/A"),
            "analysis_date": committee_results.get("analysis_date", "N/A"),
            
            # Datos del CIO
            "recomendacion_final": committee_results.get("recomendacion_final", "No concluyente"),
            "confianza_final": committee_results.get("confianza_final", "No definida"),
            "resumen_cio": committee_results.get("resumen_cio", "Sin resumen."),
            "niveles_operativos": committee_results.get("niveles_operativos", {}),

            # Datos de los especialistas
            "analisis_chartista": committee_results.get("analisis_chartista", {}),
            "analisis_quant": committee_results.get("analisis_quant", {}),
            
            # URLs de los gráficos (buscando las claves nuevas y correctas)
            "chart_url_strategic": committee_results.get("chart_url_strategic", ""),
            "chart_url_tactical": committee_results.get("chart_url_tactical", "")
        }
        # --- FIN DE LA CORRECCIÓN ---
        
        template_context = { "contenido_del_informe": contenido_para_plantilla }
        html_report = template.render(template_context)
        return html_report
    except Exception as e:
        print(f"  -> ❌ Error al renderizar la plantilla del comité: {e}")
        traceback.print_exc()
        return f"<html><body><h1>Error generando el informe</h1><p>{e}</p></body></html>"


# --- FUNCIÓN DE ENTRADA PÚBLICA DE LA VERTICAL ---

def run(parameters: dict) -> dict:
    """Función principal de la vertical de Análisis Técnico."""
    print("✅ [Vertical Análisis Técnico] Iniciando ejecución completa...")
    try:
        report_keyword = parameters.get("report_keyword")
        report_def = db.get_report_definition_by_topic(report_keyword)
        if not report_def: raise Exception(f"No se encontró definición para '{report_keyword}'.")
        
        # --- LECTURA DE TODOS LOS TICKERS Y LOOP ---
        market_data_reqs = report_def.get("market_data_series", [])
        if not market_data_reqs:
            raise Exception("La receta no define activos en 'market_data_series'.")

        tickers = [s.get("name") for s in market_data_reqs if s.get("name")]
        if not tickers:
            raise Exception("No se encontró un 'name' de ticker válido en 'market_data_series'.")

        template_path = report_def.get("template_file")

        per_ticker_status = []
        last_html_report = None
        last_artifact = None

        for ticker in tickers:
            try:
                dossier = _prepare_technical_dossier(ticker, report_def)
                if not dossier:
                    per_ticker_status.append({"ticker": ticker, "status": "error", "reason": "prep_failed"})
                    continue

                committee_results = _run_investment_committee(dossier, report_def)
                if not committee_results:
                    per_ticker_status.append({"ticker": ticker, "status": "error", "reason": "committee_failed"})
                    continue

                # Espía opcional para depuración por ticker
                # import pprint
                # print("\n🕵️  ESPÍA (PRE-REPORTE) - Datos finales para la plantilla de", ticker)
                # pprint.pprint(committee_results)
                # print("---------------------------------\n")

                # Render HTML individual del comité técnico
                html_report = _create_committee_html_report(committee_results, template_path)

                # Guardar UN SOLO artifact por ticker (HTML + JSON en una fila)
                artifact = db.insert_generated_artifact(
                    report_keyword=report_keyword,
                    artifact_content=html_report,
                    artifact_type=f"report_{report_keyword}_final",
                    results_packet=committee_results,
                    ticker=ticker  # <-- AÑADIMOS EL TICKER
                )

                # Guardar memoria del CIO después de crear el artefacto
                if artifact and committee_results.get('expert_context_output'):
                    # Detectar tipo de comité basado en el ticker
                    if ticker == "USDCLP.FOREX":
                        cio_key = "cio_clp"
                        comite_type = "CLP"
                    elif ticker == "HG=F":
                        cio_key = "cio_cobre"
                        comite_type = "Cobre"
                    else:
                        cio_key = f"cio_{ticker}"
                        comite_type = "Mercado"
                    
                    expert_vision = committee_results.get('expert_context_output')
                    if expert_vision and expert_vision.get('current_view_label') and expert_vision.get('core_thesis_summary'):
                        db.update_expert_context(
                            report_keyword=cio_key,
                            view_label=expert_vision['current_view_label'],
                            thesis_summary=expert_vision['core_thesis_summary'],
                            artifact_id=artifact.get('id')
                        )
                        print(f"    -> 🧠 Memoria del CIO guardada para {comite_type} ({ticker})")
                    else:
                        print(f"    -> 🟡 No se encontró una 'Visión Experta' válida para guardar para {comite_type} ({ticker})")

                per_ticker_status.append({"ticker": ticker, "status": "ok", "artifact_id": (artifact or {}).get("id")})
                last_html_report = html_report
                last_artifact = artifact
            except Exception as inner_e:
                print(f"❌ [Vertical Análisis Técnico] Falló el procesamiento de {ticker}: {inner_e}")
                traceback.print_exc()
                per_ticker_status.append({"ticker": ticker, "status": "error", "reason": str(inner_e)})

        # Construir respuesta resumida
        summary_lines = ["### ✅ Datos base generados - Comité Técnico"]
        for r in per_ticker_status:
            if r.get("status") == "ok":
                summary_lines.append(f"- {r['ticker']}: OK (Artifact: {r.get('artifact_id')})")
            else:
                summary_lines.append(f"- {r['ticker']}: ERROR ({r.get('reason')})")

        response_blocks = [
            {"type": "markdown", "content": "\n".join(summary_lines), "display_target": "chat"}
        ]

        # MOSTRAR SOLO EL ÚLTIMO HTML INDIVIDUAL (NO CONSOLIDADO)
        if last_html_report:
            response_blocks.append({"type": "html", "content": last_html_report, "display_target": "panel"})
            print(f"  -> ✅ [Comité] Mostrando último HTML individual")
        else:
            response_blocks.append({"type": "markdown", "content": "⚠️ No se generó ningún HTML individual", "display_target": "panel"})

        return jsonify({
            "response_blocks": response_blocks,
            "artifact_id": (last_artifact or {}).get('id') if last_artifact else None
        })

    except Exception as e:
        print(f"❌ [Vertical Análisis Técnico] Error crítico: {e}")
        traceback.print_exc()
        return jsonify({"response_blocks": [{"type": "text", "content": f"Error en el flujo de Análisis Técnico: {e}"}]})
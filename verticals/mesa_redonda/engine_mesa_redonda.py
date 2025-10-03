import os
import sys
import json
from flask import jsonify
from jinja2 import Environment, FileSystemLoader
import traceback
import inspect
import uuid
import math
import re
import datetime
from flask import render_template_string
import sys
import pprint
import yaml
import pprint
import dpath.util
import pandas as pd 
from datetime import datetime, timezone, timedelta

# --- Importaciones de Servicios Centrales y Herramientas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core import llm_manager
from quantex.core.dossier import Dossier
from quantex.core.tool_registry import registry
from quantex.core.agent_tools import get_market_data, get_file_content
from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine
from quantex.core.web_tools import get_perplexity_synthesis
from quantex.core.llm_manager import MODEL_CONFIG
from quantex.core.report_builder import retrieve_relevant_knowledge
from quantex.core.ai_services import ai_services
from quantex.core.agent_tools import get_expert_opinion
from quantex.core.handler_registry import register_handler
import logging, os

# --- Logger persistente para diagnóstico de load_data ---
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
    os.makedirs(LOGS_DIR, exist_ok=True)
    _ld_logger = logging.getLogger('quantex.load_data')
    if not _ld_logger.handlers:
        _ld_logger.setLevel(logging.INFO)
        _fh = logging.FileHandler(os.path.join(LOGS_DIR, 'load_data.log'), encoding='utf-8')
        _fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        # También enviar a consola para ver en terminal
        _sh = logging.StreamHandler(sys.stdout)
        _sh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        _ld_logger.addHandler(_fh)
        _ld_logger.addHandler(_sh)
except Exception:
    _ld_logger = logging.getLogger('quantex.load_data')
from quantex.core import agent_tools
from quantex.core.data_fetcher import get_data_series

def _run_news_editor(raw_evidence_categorized: dict) -> dict | None:
    """
    (Versión 2.0 - Editor de Noticias con Prompt Dinámico)
    Toma un diccionario de inteligencia categorizada y construye un prompt dinámico
    para que un LLM estructure cada categoría en un briefing individual.
    """
    print("    -> ✍️  [Editor de Noticias] Iniciando con prompt dinámico...")
    try:
        # --- 1. Construcción Dinámica del Prompt ---
        base_prompt_template = get_file_content("verticals/mesa_redonda/editor_de_noticias.md")
        if not base_prompt_template:
            raise ValueError("No se pudo cargar la plantilla base del Editor de Noticias.")

        # Prepara el input para la IA y las instrucciones dinámicas
        source_data_for_llm = {}
        dynamic_instructions = ""
        output_schema_properties = {}

        for key, text_list in raw_evidence_categorized.items():
            if text_list: # Solo procesa si hay contenido
                source_data_for_llm[key] = text_list
                
                # Instrucción para la TAREA - CORRECCIÓN: solo reemplazar el primer "noticias_"
                if key.startswith("noticias_"):
                    output_key = key.replace("noticias_", "briefing_", 1)  # Solo el primer reemplazo
                else:
                    output_key = f"briefing_{key}"
                dynamic_instructions += f"- Para la categoría de entrada `{key}`, debes crear una categoría de salida llamada `{output_key}`.\n"
                
                # Propiedad para el CONTRATO DE SALIDA
                output_schema_properties[output_key] = {
                    "type": "object",
                    "properties": {
                        "tesis_del_dia": {"type": "string"},
                        "puntos_de_evidencia_clave": {"type": "array", "items": {"type": "object"}}
                    }
                }

        if not source_data_for_llm:
            print("      -> 🟡 No hay datos para enviar al Editor de Noticias.")
            return {}

        # --- ESPÍA: Log de entrada para el Editor ---
        try:
            os.makedirs(os.path.join(PROJECT_ROOT, "logs"), exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            spy_input_path = os.path.join(PROJECT_ROOT, "logs", f"editor_input_{ts}.json")
            with open(spy_input_path, "w", encoding="utf-8") as f:
                json.dump(raw_evidence_categorized, f, ensure_ascii=False, indent=2, default=str)
            print(f"      -> 🕵️  [ESPÍA] Guardado input del Editor: {spy_input_path}")
        except Exception as _e:
            print(f"      -> ⚠️  [ESPÍA] No se pudo guardar el input del Editor: {_e}")

        # Helper para deduplicar puntos de evidencia (por texto normalizado)
        def _dedupe_points(items: list[dict]) -> list[dict]:
            seen = set()
            result = []
            for it in items or []:
                key_txt = " | ".join([
                    str(it.get("punto","")),
                    str(it.get("dato","")),
                    str(it.get("cita_relevante","")),
                    str(it.get("impacto",""))
                ]).strip().lower()
                key_txt = " ".join(key_txt.split())
                if key_txt and key_txt not in seen:
                    seen.add(key_txt)
                    result.append(it)
            return result

        CHUNK_SIZE = 25
        needs_chunking = any(len(v) > CHUNK_SIZE for v in source_data_for_llm.values())

        if not needs_chunking:
            # Ruta original (un solo lote para todo)
            final_user_prompt = base_prompt_template.replace('{dynamic_instructions}', dynamic_instructions)
            source_data_str = json.dumps(source_data_for_llm, indent=2, ensure_ascii=False, default=str)
            final_user_prompt = final_user_prompt.replace('{source_data}', source_data_str)

            final_output_schema = {
                "type": "object",
                "properties": output_schema_properties,
                "required": list(output_schema_properties.keys())
            }

            structured_synthesis = llm_manager.generate_structured_output(
                system_prompt=get_file_content("prompts/core_identity.txt"),
                user_prompt=final_user_prompt,
                model_name=MODEL_CONFIG['simple']['primary'],
                output_schema=final_output_schema
            )

            if not structured_synthesis:
                raise Exception("El Editor de Noticias no pudo generar una salida JSON válida.")

            # Espía salida
            try:
                spy_output_path = os.path.join(PROJECT_ROOT, "logs", f"editor_output_{ts}.json")
                with open(spy_output_path, "w", encoding="utf-8") as f:
                    json.dump(structured_synthesis, f, ensure_ascii=False, indent=2)
                print(f"      -> 🕵️  [ESPÍA] Guardado output del Editor: {spy_output_path}")
            except Exception as _e:
                print(f"      -> ⚠️  [ESPÍA] No se pudo guardar el output del Editor: {_e}")

            print("    -> ✅ [Editor de Noticias] Briefings categóricos generados exitosamente.")
            return structured_synthesis

        # Ruta con chunking por categoría
        print("      -> 📦 Activando chunking por categoría (25 ítems por sublote)...")
        merged_result: dict = {}

        for key, text_list in source_data_for_llm.items():
            # CORRECCIÓN: solo reemplazar el primer "noticias_"
            if key.startswith("noticias_"):
                output_key = key.replace("noticias_", "briefing_", 1)  # Solo el primer reemplazo
            else:
                output_key = f"briefing_{key}"

            # Categorías no-noticias (ej. inteligencia_estrategica) se procesan en un solo lote
            if not key.startswith("noticias_") or len(text_list) <= CHUNK_SIZE:
                single_source = { key: text_list }
                single_instr = f"- Para la categoría de entrada `{key}`, debes crear una categoría de salida llamada `{output_key}`.\n"
                user_prompt = base_prompt_template.replace('{dynamic_instructions}', single_instr)
                user_prompt = user_prompt.replace('{source_data}', json.dumps(single_source, indent=2, ensure_ascii=False, default=str))
                single_schema = {
                    "type": "object",
                    "properties": {
                        output_key: { "type": "object", "properties": { "tesis_del_dia": {"type": "string"}, "puntos_de_evidencia_clave": {"type": "array", "items": {"type": "object"}} }, "required": ["tesis_del_dia","puntos_de_evidencia_clave"] }
                    },
                    "required": [output_key]
                }
                partial = llm_manager.generate_structured_output(
                    system_prompt=get_file_content("prompts/core_identity.txt"),
                    user_prompt=user_prompt,
                    model_name=MODEL_CONFIG['simple']['primary'],
                    output_schema=single_schema
                )
                if partial and output_key in partial:
                    merged_result[output_key] = partial[output_key]
                continue

            # Chunking para categorías de noticias con muchos ítems
            merged_points = []
            chosen_thesis = None
            total_chunks = (len(text_list) + CHUNK_SIZE - 1) // CHUNK_SIZE
            print(f"        -> 📦 Procesando {total_chunks} chunks para '{key}' ({len(text_list)} documentos)")
            
            for start in range(0, len(text_list), CHUNK_SIZE):
                chunk = text_list[start:start+CHUNK_SIZE]
                chunk_num = (start // CHUNK_SIZE) + 1
                chunk_source = { key: chunk }
                chunk_instr = f"- Para la categoría de entrada `{key}`, debes crear una categoría de salida llamada `{output_key}`.\n"
                user_prompt = base_prompt_template.replace('{dynamic_instructions}', chunk_instr)
                user_prompt = user_prompt.replace('{source_data}', json.dumps(chunk_source, indent=2, ensure_ascii=False, default=str))
                chunk_schema = {
                    "type": "object",
                    "properties": {
                        output_key: { "type": "object", "properties": { "tesis_del_dia": {"type": "string"}, "puntos_de_evidencia_clave": {"type": "array", "items": {"type": "object"}} }, "required": ["tesis_del_dia","puntos_de_evidencia_clave"] }
                    },
                    "required": [output_key]
                }
                
                try:
                    print(f"          -> 🧠 Chunk {chunk_num}/{total_chunks} ({len(chunk)} documentos)...")
                    partial = llm_manager.generate_structured_output(
                        system_prompt=get_file_content("prompts/core_identity.txt"),
                        user_prompt=user_prompt,
                        model_name="claude-3-haiku-20240307",  # Usar Haiku para chunking (rápido y barato)
                        output_schema=chunk_schema
                    )
                    
                    if partial and output_key in partial:
                        brief = partial[output_key]
                        puntos = brief.get("puntos_de_evidencia_clave", [])
                        tesis = brief.get("tesis_del_dia", "")
                        
                        print(f"          -> ✅ Chunk {chunk_num} exitoso: {len(puntos)} puntos, tesis: {'Sí' if tesis else 'No'}")
                        
                        if not chosen_thesis and tesis:
                            chosen_thesis = tesis
                        merged_points.extend(puntos)
                    else:
                        print(f"          -> ❌ Chunk {chunk_num} falló: output inválido")
                        print(f"          -> 🔍 Debug - partial: {type(partial)}, keys: {list(partial.keys()) if partial else 'None'}")
                        if partial:
                            print(f"          -> 🔍 Debug - output_key '{output_key}' en partial: {output_key in partial}")
                            print(f"          -> 🔍 Debug - partial content: {str(partial)[:200]}...")
                        
                except Exception as e:
                    print(f"          -> ❌ Chunk {chunk_num} error: {e}")
                    continue

            merged_points = _dedupe_points(merged_points)
            final_points_count = len(merged_points)
            print(f"        -> 🎯 Resultado final para '{key}': {final_points_count} puntos únicos")
            
            merged_result[output_key] = {
                "tesis_del_dia": chosen_thesis or "Resumen integrado de noticias",
                "puntos_de_evidencia_clave": merged_points
            }

        # Espía salida combinada
        try:
            spy_output_path = os.path.join(PROJECT_ROOT, "logs", f"editor_output_{ts}.json")
            with open(spy_output_path, "w", encoding="utf-8") as f:
                json.dump(merged_result, f, ensure_ascii=False, indent=2)
            print(f"      -> 🕵️  [ESPÍA] Guardado output del Editor (merge): {spy_output_path}")
        except Exception as _e:
            print(f"      -> ⚠️  [ESPÍA] No se pudo guardar el output del Editor (merge): {_e}")

        print("    -> ✅ [Editor de Noticias] Briefings categóricos generados (con chunking) exitosamente.")
        return merged_result
        
    except Exception as e:
        print(f"      -> ❌ Error crítico en el Editor de Noticias: {e}")
        traceback.print_exc()
        return None

def _run_dossier_curator(report_keyword: str, report_def: dict) -> dict:
    """
    (Versión 16.0 - Modelo "Espejo" con Editor de Noticias)
    Implementa el pipeline de curación cualitativa final.
    """
    print(f"  -> 🚜 [Curador de Dossier v16.0] Ejecutando modelo 'Espejo'...")
    
    data_for_editor = {}
    final_qualitative_context = {}

    # --- ETAPA 1: RECOLECCIÓN Y CLASIFICACIÓN TÁCTICA ---
    tactical_sources_config = report_def.get('fuentes_tacticas', [])
    if isinstance(tactical_sources_config, str):
        try: tactical_sources_config = json.loads(tactical_sources_config)
        except json.JSONDecodeError: tactical_sources_config = []

    print("    -> 🚚 Recolectando y clasificando inteligencia táctica...")
    if tactical_sources_config:
        for source_job in tactical_sources_config:
            source_name = source_job.get("source")
            topic = source_job.get("topic", report_keyword)
            days = source_job.get("days_ago", 3)
            processing_type = source_job.get("processing_type", "default")

            try:
                time_filter = _get_start_date_n_business_days_ago(days)
                response = db.supabase.table('nodes').select('content').eq('type', 'Documento').ilike('properties->>source', f"%{source_name}%").ilike('properties->>topic', f"%{topic}%").gte('properties->>timestamp', time_filter.isoformat()).order('properties->>timestamp', desc=True).limit(100).execute()

                if response.data:
                    content_list = [item['content'] for item in response.data if item.get('content')]
                    
                    if processing_type == "raw":
                        key = f"inteligencia_tactica_raw_{topic.lower().replace(' ', '_')}"
                        final_qualitative_context[key] = content_list
                    else:
                        key = f"noticias_{source_name.lower()}_{topic.lower().replace(' ', '_')}"
                        if key not in data_for_editor:
                            data_for_editor[key] = []
                        data_for_editor[key].extend(content_list)
            except Exception as e:
                print(f"        -> ❌ Error recolectando para '{source_name}/{topic}': {e}")

  # --- CORRECCIÓN: ESTA ETAPA AHORA VA AQUÍ, ANTES DE LLAMAR AL EDITOR ---
    # --- ETAPA 2 (NUEVA): RECOLECCIÓN ESTRATÉGICA ---
    print("    -> 🏛️  Cosechando inteligencia estratégica...")
    try:
        topic_node_res = db.supabase.table('nodes').select('id').eq('type', 'Tópico Principal').eq('label', report_keyword).maybe_single().execute()
        if topic_node_res.data:
            topic_node_id = topic_node_res.data['id']
            edges_res = db.supabase.table('edges').select('target_id').eq('source_id', topic_node_id).eq('relationship_type', 'generó_aprendizaje').execute()
            if edges_res.data:
                learning_node_ids = [edge['target_id'] for edge in edges_res.data]
                learnings_res = db.supabase.table('nodes').select('content').in_('id', learning_node_ids).order('created_at', desc=True).limit(15).execute()
                if learnings_res.data:
                    all_learnings = [node['content'] for node in learnings_res.data if node.get('content')]
                    # Se añaden al paquete de trabajo para el Editor.
                    data_for_editor["inteligencia_estrategica"] = list(dict.fromkeys(all_learnings))
    except Exception as e:
        print(f"      -> ⚠️  No se pudieron cosechar los aprendizajes estratégicos: {e}")

    # --- CORRECCIÓN: ESTA ETAPA AHORA ES LA ÚLTIMA ANTES DE RETORNAR ---
    # --- ETAPA 3 (NUEVA): SÍNTESIS TÁCTICA (LLAMADA AL EDITOR) ---
    if data_for_editor:
        structured_briefings = _run_news_editor(data_for_editor)
        if structured_briefings:
            final_qualitative_context.update(structured_briefings)
    
    print("\n    -> ✅ Dossier cualitativo final ensamblado y listo para el Oráculo.")
    return final_qualitative_context


def _prepare_evidence_dossier(report_def: dict) -> tuple[Dossier, dict]:
    """
    (Versión Línea de Ensamblaje)
    Prepara el dossier de evidencia cuantitativa.
    Devuelve tanto el objeto Dossier como el workspace crudo.
    """
    print("-> ⚙️  Ejecutando preparador de evidencia (Línea de Ensamblaje)...")
    workspace = {}
    dossier = Dossier()
    
    # ESTACIÓN 1: OBTENER MATERIA PRIMA
    print("  -> 🚚 Obteniendo materia prima con data_fetcher...")
    market_data_series = report_def.get("market_data_series", [])
    for series_req in market_data_series:
        ticker = series_req.get("name")
        if not ticker: continue
        
        df = get_data_series(identifier=ticker, days=730)
        if df is not None and not df.empty:
            # Enriquecer con metadatos si es una serie de expectativas TPM
            from quantex.core.series_metadata import enrich_series_with_metadata
            enriched_data = enrich_series_with_metadata(ticker, df.reset_index().to_dict('records'))
            workspace[f"data_{ticker}"] = enriched_data
    print("  -> ✅ Materia prima consolidada en workspace.")

    # ESTACIÓN 2: TRANSFORMACIÓN DE DATOS
    print("  -> 🏭 Ejecutando processing_pipeline...")
    processing_pipeline = report_def.get("processing_pipeline", [])
    for step in processing_pipeline:
        tool_name = step.get("tool_name")
        params = step.get("parameters", {})
        tool_function = registry.get(tool_name)
        if tool_function:
            tool_function(workspace=workspace, params=params)
    print("  -> ✅ Transformaciones completadas.")

    # ESTACIÓN 3: ANÁLISIS CUANTITATIVO (BLOQUES DE ANÁLISIS)
    print("  -> 📈 Ejecutando data_requirements (Bloques de Análisis)...")
    data_reqs = report_def.get("data_requirements", {})
    bloques = data_reqs.get("bloques_de_analisis", [])
    
    # --- INICIO DEL CAMBIO QUIRÚRGICO ---
    logica_bloques = {
        "analisis_de_precio_commodity": [
            {"name": "get_last_value", "params": {"output_key": "last_close", "value_key": "close"}},
            {"name": "calculate_offset_value", "params": {"offset": "1d", "output_key": "daily_variation_pct"}},
            {"name": "calculate_offset_value", "params": {"offset": "7d", "output_key": "weekly_variation_pct"}},
            {"name": "calculate_offset_value", "params": {"offset": "1m", "output_key": "monthly_variation_pct"}},
            {"name": "calculate_offset_value", "params": {"offset": "3m", "output_key": "quarterly_variation_pct"}},
            {"name": "calculate_offset_value", "params": {"offset": "1y", "output_key": "annual_variation_pct"}}
        ],
        "analisis_de_inventario": [
            {"name": "get_last_value", "params": {"output_key": "last_close", "value_key": "close"}},
            {"name": "calculate_offset_value", "params": {"offset": "7d", "calculation_mode": "absolute", "output_key": "weekly_delta_tonnes"}},
            {"name": "calculate_offset_value", "params": {"offset": "1y", "calculation_mode": "absolute", "output_key": "annual_delta_tonnes"}}
        ]
    }

    for bloque in bloques:
        nombre_bloque = bloque.get("nombre_bloque")
        series_a_aplicar = bloque.get("series_a_aplicar", [])
        calculos = logica_bloques.get(nombre_bloque, [])
        
        for series_name in series_a_aplicar:
            source_key = f"data_{series_name}"
            if source_key in workspace:
                summary_key = f"{series_name}_summary"
                dossier.summaries[summary_key] = {}
                for calc in calculos:
                    tool_name = calc.get("name")
                    tool_params = calc.get("params", {}).copy()
                    tool_function = registry.get(tool_name)
                    if tool_function:
                        result = tool_function(series_data=workspace[source_key], **tool_params)
                        if result and result.get('value') is not None:
                            dossier.summaries[summary_key][tool_params['output_key']] = result['value']
    print("  -> ✅ Cálculos de data_requirements completados.")

    # ESTACIÓN 3.5: INCLUIR SERIES ENRIQUECIDAS CON METADATOS EN SUMMARIES
    print("  -> 📊 Incluyendo series enriquecidas con metadatos en summaries...")
    for key, value in workspace.items():
        if key.startswith('data_') and isinstance(value, dict) and 'data' in value and 'context_for_ai' in value:
            # Es una serie enriquecida con metadatos
            series_name = key.replace('data_', '')
            summary_key = f"{series_name}_enriched"
            dossier.summaries[summary_key] = {
                'display_name': value.get('display_name', series_name),
                'context_for_ai': value.get('context_for_ai', ''),
                'unit': value.get('unit', 'unknown'),
                'source': value.get('source', 'unknown'),
                'data_points': len(value.get('data', [])),
                'latest_value': value.get('data', [{}])[-1].get('close') or value.get('data', [{}])[-1].get('value') if value.get('data') else None
            }
            print(f"    -> ✅ Serie enriquecida '{series_name}' añadida a summaries con metadatos.")
    print("  -> ✅ Series enriquecidas procesadas.")

    # ESTACIÓN 4: VISUALIZACIÓN
    visualization_pipeline = report_def.get("visualization_pipeline", [])
    print("  -> 🎨 Ejecutando visualization_pipeline...")
    for step in visualization_pipeline:
        tool_name = step.get("tool_name")
        params = step.get("parameters", {})
        tool_function = registry.get(tool_name)
        if tool_function:
            # El workspace para los gráficos debe tener tanto los resúmenes como los datos crudos
            viz_workspace = {**workspace, **dossier.summaries}
            result = tool_function(evidence_workspace=viz_workspace, params=params)
            if result:
                dossier.add_visualization(result)
    print("  -> ✅ Visualizaciones generadas.")
    
    print("  -> ✅ Dossier de evidencia cuantitativa preparado exitosamente.")
    return dossier, workspace

def _run_synthesis_engine(dossier: Dossier, report_definition: dict, report_keyword: str) -> dict:
    """
    (Arquitectura Final)
    Toma el dossier de evidencia objetiva y aplica la directriz "just-in-time"
    del Briefing Estratégico antes de la síntesis final.
    """
    print(f"  -> ⚙️  [Motor de Síntesis - Final] Iniciando...")
    

    # PASO 1: BUSCAR Y VALIDAR EL BRIEFING ESTRATÉGICO (lógica ACTIVE/CONSUMED)
    print("    -> 🕵️  Evaluando estado del 'Briefing Estratégico' (ACTIVE/CONSUMED)...")

    # 1. Obtener timestamp del último informe final publicado (para referencia)
    last_final_report = db.get_latest_report(report_keyword, artifact_type_suffix='_final')
    last_final_report_ts = datetime.fromisoformat(last_final_report['created_at']) if last_final_report else datetime.min.replace(tzinfo=timezone.utc)

    # 2. Buscar briefing ACTIVE (sin fallbacks)
    briefing_content = None
    try:
        # Buscar el briefing completo (nuevo formato: Briefing_Estratégico_Completo)
        res_complete = db.supabase.table('nodes').select('id, content, properties').eq('type', 'Documento').eq('properties->>source', 'Strategic_Alignment_Session').eq('properties->>topic', report_keyword).eq('properties->>status', 'ACTIVE').eq('properties->>source_type', 'Briefing_Estratégico_Completo').order('properties->>timestamp', desc=True).execute()
        
        if res_complete and res_complete.data:
            # Tomar el briefing más reciente (debería ser solo uno)
            briefing_node = res_complete.data[0]
            briefing_content = briefing_node.get('content', '')
            session_length = briefing_node.get('properties', {}).get('session_length', 0)
            print(f"    -> ✅ Briefing COMPLETO ACTIVE detectado ({session_length} turnos de diálogo). Se incluirá en el análisis.")
        else:
            # Buscar briefings fragmentados (formato anterior) - SOLO si no hay briefing completo
            res_active = db.supabase.table('nodes').select('id, content, properties').eq('type', 'Documento').eq('properties->>source', 'Strategic_Alignment_Session').eq('properties->>topic', report_keyword).eq('properties->>status', 'ACTIVE').order('properties->>timestamp', desc=True).execute()
            
            if res_active and res_active.data:
                print(f"    -> ✅ Briefing ACTIVE detectado ({len(res_active.data)} fragmento(s)) - formato anterior. Concatenando...")
                briefing_content = "\n\n".join([b.get('content', '') for b in res_active.data if b.get('content')])
            
    except Exception as _e:
        print(f"    -> ❌ Error consultando briefing ACTIVE: {_e}")

    if briefing_content:
        print(f"    -> 🔍 [DEBUG] Briefing content length: {len(briefing_content)} caracteres")
        print(f"    -> 🔍 [DEBUG] Primeros 200 chars: {briefing_content[:200]}...")
        dossier.qualitative_context["briefing_del_estratega"] = briefing_content
    else:
        print("    -> 🟡 No hay briefing ACTIVE para incluir (o ya fue consumido).")


    # PASO 2: CONSTRUIR EL CONTEXTO FINAL PARA EL ORÁCULO
    prompt_context = dossier.to_dict_for_oracle()

    # PASO 3: LLAMAR AL ORÁCULO 
    synthesis_pipeline = report_definition.get('synthesis_pipeline', [])
    if isinstance(synthesis_pipeline, str):
        try: synthesis_pipeline = json.loads(synthesis_pipeline)
        except json.JSONDecodeError: synthesis_pipeline = []
    
    if not synthesis_pipeline:
        return {"error": "No se encontró un 'synthesis_pipeline' en la definición."}
    
    step = synthesis_pipeline[0]
    agent_name = step.get("agent_name")
    prompt_file = step.get("prompt_file")
    
    try:
        print(f"    -> 🧠 Llamando al agente: '{agent_name}'...")
        prompt_template = get_file_content(prompt_file)
        
        task_complexity = step.get("task_complexity", "simple")
        model_name = MODEL_CONFIG.get(task_complexity, {}).get('primary')
        
        source_data_context = json.dumps(prompt_context, indent=2, ensure_ascii=False, default=str)
        user_prompt = prompt_template.replace('{source_data}', source_data_context)
        
        output_schema = report_definition.get('output_schema')
        if isinstance(output_schema, str):
            output_schema = json.loads(output_schema)

        print("    -> 🎯 Aplicando schema de salida final estricto a este agente.")
        structured_data = llm_manager.generate_structured_output(
            system_prompt=get_file_content("prompts/core_identity.txt"),
            user_prompt=user_prompt,
            model_name=model_name,
            output_schema=output_schema
        )

        if not structured_data:
            raise Exception(f"El agente '{agent_name}' no pudo generar una salida JSON válida.")
            
        print(f"    -> ✅ Síntesis de IA completada.")
        return {"final_output": structured_data}

    except Exception as e:
        print(f"    -> ❌ Error en el agente '{agent_name}': {e}")
        raise e

def _build_html_from_template(template_file: str, synthesis_result: dict, dossier: Dossier, report_def: dict, new_artifact_id: str | None) -> str | None:
    """
    (Versión 2.5 - A Prueba de Balas)
    Renderiza la plantilla HTML, garantizando que los datos tengan la estructura correcta.
    """
    if not template_file:
        print("-> ⚠️  Advertencia: No se especificó 'template_file'.")
        return None
    try:
        full_template_path = os.path.join(PROJECT_ROOT, template_file)
        template_dir = os.path.dirname(full_template_path)
        template_name = os.path.basename(full_template_path)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)
        
        # --- INICIO DE LA CORRECCIÓN DEFINITIVA ---
        # El problema está aquí. En lugar de pasar el diccionario completo a la plantilla,
        # necesitamos "desenvolverlo" y pasar solo el contenido que está DENTRO
        # de 'borrador_sintetizado'.
        
        report_data = synthesis_result.get('borrador_sintetizado', {})
        if not report_data:
            # Si por alguna razón 'borrador_sintetizado' está vacío, buscamos en la siguiente clave
            report_data = synthesis_result.get('final_output', {}).get('borrador_sintetizado', {})
        
            print("   -> ✅ [Renderizador] Extrayendo contenido para la plantilla.")
            
        else:
            # Si no, asumimos que el resultado ya es el contenido (plan B).
            report_data = synthesis_result
            print("   -> ⚠️  [Renderizador] No se encontró 'borrador_sintetizado', usando el resultado completo.")
        # --- FIN DE LA CORRECCIÓN ---

        # Aseguramos que el porcentaje alcista sea un número
        sentimiento = report_data.get('sentimiento_mercado', {})
        if sentimiento and 'porcentaje_alcista' in sentimiento:
            try:
                sentimiento['porcentaje_alcista'] = int(sentimiento.get('porcentaje_alcista', 0))
            except (ValueError, TypeError):
                sentimiento['porcentaje_alcista'] = 0

        template_context = {
            "reporte": report_data, # <-- Ahora 'reporte' es GARANTIZADO el contenido interno.
            "summaries": dossier.summaries,
            "visualizations": dossier.visualizations,
            "titulo_informe": report_def.get("display_title", "Informe Quantex"),
            "fecha_informe": datetime.now().strftime('%d de %B, %Y'),
            "artifact_id": new_artifact_id
        }

        return template.render(template_context)
        
    except Exception as e:
        print(f"-> ❌ Error al renderizar la plantilla '{template_file}' con Jinja2: {e}")
        traceback.print_exc()
        return None

def _save_learnings_to_knowledge_graph(dossier: Dossier, topic: str):
    """
    (Versión 5.0 - Motor Centralizado)
    Extrae, filtra por novedad y guarda los aprendizajes clave en el grafo usando el nuevo motor.
    """
    if not dossier.ai_content:
        return

    final_output = dossier.ai_content.get('final_output', {})
    report_content = final_output.get("borrador_sintetizado", {})
    new_learnings = report_content.get("aprendizajes_clave", [])

    if not new_learnings or not isinstance(new_learnings, list):
        print("  -> 🟡 No se encontraron 'aprendizajes_clave' para guardar.")
        return
    
    try:
        # Inicializar el motor de ingesta centralizado
        print("  -> 🏭 Inicializando Motor de Ingesta Centralizado...")
        ingestion_engine = KnowledgeGraphIngestionEngine()
        
        # 1. Obtener los aprendizajes que ya existen en el grafo
        print("  -> 📚 Obteniendo aprendizajes existentes para evitar duplicados...")
        topic_node_res = db.supabase.table('nodes').select('id').eq('type', 'Tópico Principal').eq('label', topic).maybe_single().execute()
        existing_learnings = []
        if topic_node_res.data:
            topic_node_id = topic_node_res.data['id']
            edges_res = db.supabase.table('edges').select('target_id').eq('source_id', topic_node_id).eq('relationship_type', 'generó_aprendizaje').execute()
            if edges_res.data:
                learning_node_ids = [edge['target_id'] for edge in edges_res.data]
                learnings_res = db.supabase.table('nodes').select('content').in_('id', learning_node_ids).execute()
                if learnings_res.data:
                    existing_learnings = [node['content'] for node in learnings_res.data if node.get('content')]
        
        # 2. Llamar a nuestra nueva herramienta de filtrado
        novel_learnings = agent_tools._filter_for_novel_learnings(
            new_learnings=new_learnings,
            existing_learnings=existing_learnings
        )
        
        # 3. Guardar solo los aprendizajes que pasaron el filtro usando el nuevo motor
        if novel_learnings:
            print(f"  -> ✍️  Guardando {len(novel_learnings)} aprendizaje(s) verdaderamente nuevo(s) en el Grafo...")
            
            # Crear contenido combinado de todos los aprendizajes
            combined_content = "\n\n".join([f"Aprendizaje {i+1}: {learning}" for i, learning in enumerate(novel_learnings)])
            
            # Contexto de fuente para los aprendizajes
            source_context = {
                "source": "Mesa_Redonda_Engine",
                "topic": topic,
                "source_type": "Aprendizajes_Extraídos",
                "original_url": f"report_learnings_{datetime.now(timezone.utc).isoformat()}"
            }
            
            # Usar el nuevo motor de ingesta
            result = ingestion_engine.ingest_document(combined_content, source_context)
            if result.get("success"):
                print(f"  -> ✅ {result.get('nodes_created', 0)} nodo(s) de aprendizajes creado(s) con conexiones semánticas.")
            else:
                print(f"  -> ❌ Error en ingesta de aprendizajes: {result.get('reason', 'Desconocido')}")
        else:
            print("  -> ✅ No se encontraron aprendizajes nuevos para añadir al grafo.")

    except Exception as e:
        print(f"  -> ❌ Error crítico durante el proceso de guardado de aprendizajes: {e}")
        traceback.print_exc()

def _get_start_date_n_business_days_ago(n_days: int) -> datetime:
    """
    Calcula la fecha de inicio retrocediendo N días hábiles, saltándose los fines de semana.
    """
    print(f"      -> 🗓️  Calculando fecha de inicio para los últimos {n_days} días hábiles...")
    today = datetime.now(timezone.utc)
    business_days_to_subtract = n_days
    current_date = today
    while business_days_to_subtract > 0:
        current_date -= timedelta(days=1)
        # weekday() devuelve 5 para sábado y 6 para domingo
        if current_date.weekday() < 5:
            business_days_to_subtract -= 1
    print(f"      -> ✅ Fecha de inicio calculada: {current_date.strftime('%Y-%m-%d')}")
    return current_date        


@register_handler("publish_final_report")
def _handle_publish(parameters: dict, state: dict, **kwargs) -> dict:
    """
    (Versión Publicador 5.0 - Promoción Directa)
    Política: Al publicar el informe final NUNCA se re-sintetiza.
    Siempre se promueve el último borrador a final y se consumen los briefings ACTIVE.
    """
    topic = parameters.get("report_keyword")
    if not topic:
        return jsonify({"response_blocks": [{"type": "text", "content": "No se especificó un tópico para publicar."}]})

    print(f"🚀 [Publicador 5.0] Iniciando para: '{topic}'...")
    
    # 1. ENCONTRAR EL ÚLTIMO BORRADOR
    latest_draft = db.get_latest_draft_artifact(topic)
    if not latest_draft:
        return jsonify({"response_blocks": [{"type": "text", "content": f"No se encontró un borrador para '{topic}'. Genéralo primero."}]})
    
    draft_timestamp = datetime.fromisoformat(latest_draft['created_at'])
    print(f"  -> 📜 Borrador encontrado, creado en: {draft_timestamp}")

    # Política: siempre promoción directa del último borrador
    print("  -> ✅ DECISIÓN: Promoción directa del último borrador (sin re-síntesis).")
    try:
        final_artifact = db.promote_draft_to_final(latest_draft['id'])
        if not final_artifact:
            raise Exception("Fallo al promover el borrador.")

        # Consumir briefings ACTIVE al publicar
        try:
            final_artifact_id = final_artifact['id']
            published_ts = datetime.now(timezone.utc).isoformat()
            active_nodes = db.supabase.table('nodes').select('id, properties').eq('type', 'Documento').eq('properties->>source', 'Strategic_Alignment_Session').eq('properties->>topic', topic).eq('properties->>status', 'ACTIVE').execute()
            if active_nodes and active_nodes.data:
                for n in active_nodes.data:
                    props = n.get('properties', {}) or {}
                    props['status'] = 'CONSUMED'
                    props['consumed_by_artifact_id'] = final_artifact_id
                    props['consumed_at'] = published_ts
                    db.supabase.table('nodes').update({'properties': props}).eq('id', n['id']).execute()
                print(f"  -> ✅ {len(active_nodes.data)} briefing(s) marcado(s) como CONSUMED.")
            else:
                print("  -> ℹ️ No se encontraron briefings ACTIVE para consumir.")
        except Exception as _e:
            print(f"  -> ⚠️ No se pudo marcar briefing como CONSUMED: {_e}")

        return jsonify({
            "response_blocks": [
                {"type": "html", "content": final_artifact['full_content'], "display_target": "panel"},
                {"type": "text", "content": f"✅ Informe '{topic}' publicado exitosamente desde el borrador existente.", "display_target": "chat"}
            ], "artifact_id": final_artifact['id']
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"response_blocks": [{"type": "text", "content": f"Error en la promoción: {e}"}]})
    

def _handle_edit(state, reformulated_message, user_message, **kwargs):
    """(Temporalmente desactivado hasta que se refactorice a la nueva arquitectura)"""

    parent_artifact_id = state.get('artifact_id')
    if not parent_artifact_id: return jsonify({"response_blocks": [{"type": "text", "content": "No hay informe para editar."}]})
    original_artifact = db.get_artifact_by_id(parent_artifact_id)
    original_draft_text = original_artifact.get('full_content', '')
    editor_prompt_template = get_file_content("prompts/prompt_draft_editor.txt")
    system_prompt = f"{editor_prompt_template}\n### BORRADOR ORIGINAL ###\n{original_draft_text}\n### INSTRUCCIÓN ###\n{reformulated_message}"
    edited_content = llm_manager.generate_completion(system_prompt=system_prompt, user_prompt="Aplica la instrucción y devuelve el texto completo.")
    new_artifact_data = {'artifact_type': original_artifact.get('artifact_type', 'report_draft'), 'full_content': edited_content, 'user_prompt': user_message, 'source_dossier_id': original_artifact.get('source_dossier_id'), 'parent_artifact_id': parent_artifact_id}
    new_artifact = db.insert_generated_artifact(new_artifact_data)
    return jsonify({"response_blocks": [{"type": "markdown", "content": edited_content, "display_target": "panel"}], "artifact_id": new_artifact.get('id') if new_artifact else None})    

def load_data(parameters: dict) -> dict:
    """
    (Versión 3.0 - Refactorizada)
    Orquesta la preparación COMPLETA del dossier de evidencia, incluyendo
    la cosecha de informes de especialistas, y lo guarda como "materia prima".
    """
    print("✅ [Mesa Redonda] Iniciando flujo 'load_data' (Refactorizado)...")
    _ld_logger.info("INICIO load_data parameters=%s", str(parameters))
    try:
        report_keyword = parameters.get("report_keyword")
        if not report_keyword:
            raise ValueError("El 'report_keyword' es requerido.")

        report_def = db.get_report_definition_by_topic(report_keyword)
        _ld_logger.info("Definición cargada para topic=%s", report_keyword)
        if not report_def:
            raise Exception(f"No se encontró definición para '{report_keyword}'.")

        # PASO 1: PREPARAR EVIDENCIA CUANTITATIVA
        print("  -> PASO 1/3: Preparando evidencia cuantitativa (mercado, gráficos)...")
        dossier, workspace = _prepare_evidence_dossier(report_def)
        _ld_logger.info("PASO 1/3 completado: evidence preparada (series=%s)", 
                        ",".join([k for k in workspace.keys() if k.startswith('data_')]))

        # PASO 2: ENRIQUECER CON CONTEXTO CUALITATIVO CURADO
        print("  -> PASO 2/3: Cosechando inteligencia cualitativa del Grafo...")
        curated_context = _run_dossier_curator(report_keyword, report_def)
        _ld_logger.info("PASO 2/3 completado: contexto cualitativo curado=%s", bool(curated_context))
        if curated_context:
            dossier.qualitative_context = curated_context

        # PASO 3: COSECHAR Y RESUMIR INFORMES DE ESPECIALISTAS REQUERIDOS
        print("  -> PASO 3/3: Buscando y resumiendo informes de especialistas...")
        required_reports_def = report_def.get("required_reports", [])
        if required_reports_def:
            for report_req in required_reports_def:
                specialist_keyword = report_req.get("report_keyword")
                context_key = report_req.get("context_key")
                summary_mapping = report_req.get("summary_mapping") 

                print(f"    -> Procesando requisito: '{specialist_keyword}'...")
                latest_specialist_report = db.get_latest_report(specialist_keyword)
                _ld_logger.info("PASO 3/3 requisito=%s encontrado=%s", specialist_keyword, bool(latest_specialist_report))
                
                if latest_specialist_report and latest_specialist_report.get('content_dossier'):
                    full_content_dossier = latest_specialist_report['content_dossier']
                    
                    # Si la receta especifica un mapa de resumen, lo aplicamos
                    if summary_mapping:
                        print(f"      -> Aplicando mapa de resumen para generar informe conciso...")
                        summary_object = {}
                        for new_key, source_path in summary_mapping.items():
                            try:
                                value = dpath.util.get(full_content_dossier, source_path, separator='.')
                                summary_object[new_key] = value
                            except KeyError:
                                print(f"        -> 🟡 Advertencia: No se encontró la ruta '{source_path}' en el informe de {specialist_keyword}.")
                        
                        dossier.required_reports[context_key] = summary_object
                        print(f"      -> ✅ Resumen estratégico para '{context_key}' añadido al dossier.")
                    else:
                        # Si no se especifica mapa, se añade el informe completo
                        dossier.required_reports[context_key] = full_content_dossier
                        print(f"      -> ✅ Informe completo para '{context_key}' añadido al dossier.")
                else:
                    print(f"      -> 🟡 Advertencia: No se encontró un informe final para '{specialist_keyword}'.")
        else:
            print("    -> No se requieren informes de especialistas para este tópico.")
            _ld_logger.info("No hay required_reports para topic=%s", report_keyword)


        # PASO 4/4: BUSCAR Y FILTRAR LA MEMORIA DEL ORÁCULO
        print("  -> PASO 4/4: Buscando la visión experta anterior...")
        expert_vision_completa = db.get_expert_context(report_keyword)
        _ld_logger.info("Memoria del oráculo presente=%s", bool(expert_vision_completa))
        
        if expert_vision_completa:
            # Filtramos para quedarnos solo con las claves que necesita la IA
            dossier.expert_view_anterior = {
                "current_view_label": expert_vision_completa.get("current_view_label"),
                "core_thesis_summary": expert_vision_completa.get("core_thesis_summary")
            }
            print("    -> ✅ Visión anterior encontrada y filtrada. Añadida al dossier.")
        else:
            print("    -> 🟡 No se encontró una visión experta anterior para este tópico.")

        # PASO FINAL: GUARDAR EL DOSSIER COMPLETO COMO "MATERIA PRIMA"
        print("  -> 💾 Guardando el dossier de materia prima completo en la base de datos...")
        db.insert_materia_prima_dossier(
            topic=report_keyword,
            evidence=dossier.to_dict()
        )
        _ld_logger.info("Dossier de materia prima guardado para topic=%s", report_keyword)

        _ld_logger.info("FIN OK load_data topic=%s", report_keyword)
        return jsonify({
            "response_blocks": [
                {"type": "text", "content": f"✅ Dossier de materia prima para '{report_keyword}' creado y guardado exitosamente.", "display_target": "chat"}
            ]
        })

    except Exception as e:
        traceback.print_exc()
        _ld_logger.info("EXCEPCIÓN load_data: %s", str(e))
        return jsonify({"response_blocks": [{"type": "text", "content": f"Error en el flujo de carga de datos: {e}"}]})


def run(parameters: dict) -> dict:
    """
    (Versión Refactorizada - Solo Síntesis)
    Carga el dossier de materia prima (que ya debe estar completo), ejecuta la
    síntesis del Oráculo, y genera el artefacto final.
    """
    print("✅ [Mesa Redonda] Iniciando flujo de SÍNTESIS (Simplificado)...")
    try:
        report_keyword = parameters.get("report_keyword")
        if not report_keyword:
            raise ValueError("El 'report_keyword' es requerido.")

        report_def = db.get_report_definition_by_topic(report_keyword)
        if not report_def:
            raise Exception(f"No se encontró definición para '{report_keyword}'.")

        # PASO 1: CARGAR EL DOSSIER DE MATERIA PRIMA (AHORA COMPLETO)
        print(f"  -> 📂 Cargando último dossier de materia prima para '{report_keyword}'...")
        latest_materia_prima = db.get_latest_materia_prima_dossier(report_keyword)
        
        if not latest_materia_prima or not latest_materia_prima.get('dossier_content'):
            error_msg = f"No se encontró un dossier de materia prima para '{report_keyword}'. Por favor, ejecuta primero el flujo 'load_data'."
            return jsonify({"response_blocks": [{"type": "text", "content": error_msg}]})
        
        dossier_id = latest_materia_prima['id']      
        dossier = Dossier.from_dict(latest_materia_prima['dossier_content'])
        print("  -> ✅ Dossier cargado exitosamente.")

        # PASO 2: SÍNTESIS DE IA
        print("  -> 🤖 Pasando dossier al motor de síntesis de IA...")
        synthesis_result = _run_synthesis_engine(dossier, report_def, report_keyword)
        if not synthesis_result or "error" in synthesis_result:
            raise Exception(f"La síntesis de IA falló: {synthesis_result.get('error', 'Error desconocido')}")

        dossier.ai_content = synthesis_result
        
        # El resto del proceso para guardar, renderizar y actualizar el artefacto no cambia.
        print("  -> 💾 Guardando artefacto para obtener ID...")
        results_packet = dossier.to_dict()
        new_artifact = db.insert_generated_artifact(
            report_keyword=report_keyword,
            artifact_content="<p>Renderizando informe...</p>",
            artifact_type=f'report_{report_keyword.replace(" ", "_")}_draft',
            results_packet=results_packet,
            source_dossier_id=dossier_id
        )
        if not new_artifact: raise Exception("No se pudo crear el artefacto en la base de datos.")
        new_artifact_id = new_artifact.get('id')

        print(f"  -> 📄 Construyendo HTML final para el artefacto ID: {new_artifact_id}...")
        final_html = _build_html_from_template(
            template_file=report_def.get("template_file"),
            synthesis_result=dossier.ai_content,
            dossier=dossier,
            report_def=report_def,
            new_artifact_id=new_artifact_id
        )
        
        if final_html:
            print("  -> 🔄 Actualizando artefacto con el HTML renderizado...")
            db.supabase.table('generated_artifacts').update({'full_content': final_html}).eq('id', new_artifact_id).execute()
        
        _save_learnings_to_knowledge_graph(dossier, report_keyword)

        print("  -> 🧠 Guardando 'Visión Experta' en la memoria a largo plazo...")
        synthesis_output = dossier.ai_content.get('final_output', {})
        expert_vision = synthesis_output.get('expert_context_output')
        if expert_vision and expert_vision.get('current_view_label') and expert_vision.get('core_thesis_summary'):
            db.update_expert_context(
                report_keyword=report_keyword,
                view_label=expert_vision['current_view_label'],
                thesis_summary=expert_vision['core_thesis_summary'],
                artifact_id=new_artifact_id
            )
        else:
            print("    -> 🟡 No se encontró una 'Visión Experta' válida para guardar.")
        
        return jsonify({
            "response_blocks": [
                {"type": "html", "content": final_html, "display_target": "panel"},
                {"type": "text", "content": f"✅ Borrador del '{report_def.get('display_title', report_keyword)}' generado.", "display_target": "chat"}
            ], "artifact_id": new_artifact_id
        })    

    except Exception as e:
        traceback.print_exc()
        return jsonify({"response_blocks": [{"type": "text", "content": f"Error en el flujo de Mesa Redonda: {e}"}]})
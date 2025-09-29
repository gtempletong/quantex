# quantex/core/report_builder.py

import json
import os
import math
import traceback
import demjson3
from datetime import datetime, timedelta, timezone
import pytz
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from quantex.core.dossier import Dossier
from quantex.core.tool_registry import registry
from quantex.core import database_manager as db
from quantex.core.agent_tools import get_market_data, get_file_content, _extract_json_from_response
from quantex.core.web_tools import get_perplexity_synthesis
from quantex.core import llm_manager
from quantex.core.llm_manager import MODEL_CONFIG
from quantex.core.ai_services import ai_services


# En quantex/core/report_builder.py

def retrieve_relevant_knowledge(query_text: str, ai_services: object, top_k: int = 5, filters: dict = None, time_filter_days: int = None) -> list:
    """
    (Versión Final y Robusta)
    Realiza una búsqueda semántica en Pinecone, aplicando filtros de metadatos y tiempo,
    y luego recupera el contenido desde Supabase usando el alias 'db'.
    """
    print(f"  -> 🔍 Buscando conocimiento relevante para: '{query_text[:50]}...'")
    if not query_text:
        return []
    try:
        # 1. Convertir la consulta a un vector
        query_embedding = ai_services.embedding_model.encode(query_text).tolist()

        # 2. Construir los parámetros de la consulta para Pinecone
        def _build_query_params(days_back: int | None):
            params = { "vector": query_embedding, "top_k": top_k }
            final_filters = filters.copy() if filters else {}
            if days_back:
                # Ajuste especial de lunes: ampliar la ventana dos días extra
                weekday = datetime.now(timezone.utc).weekday()  # 0=lunes
                adjusted_days = days_back + 2 if weekday == 0 else days_back
                days_ago_epoch = int((datetime.now(timezone.utc) - timedelta(days=adjusted_days)).timestamp())
                final_filters["created_at"] = {"$gte": days_ago_epoch}
            if final_filters:
                params["filter"] = final_filters
                print(f"    -> Aplicando filtros a la búsqueda: {final_filters}")
            return params

        # 3. Realizar la búsqueda inicial
        query_params = _build_query_params(time_filter_days)
        search_results = ai_services.pinecone_index.query(**query_params)
        
        matches = search_results.get('matches', [])
        # 4. Si no hay resultados y hay filtro temporal, ampliar 1 día y reintentar (posible feriado)
        if not matches and time_filter_days:
            print("    -> 🟡 Sin resultados con la ventana inicial. Reintentando con +1 día (posible feriado)...")
            retry_params = _build_query_params(time_filter_days + 1)
            search_results = ai_services.pinecone_index.query(**retry_params)
            matches = search_results.get('matches', [])
            if not matches:
                print("    -> 🟡 Sin resultados tras el reintento.")
                return []

        # Obtenemos los IDs de los nodos desde Pinecone
        node_ids = [match['id'] for match in matches]
        
        # Consultamos la nueva tabla 'nodes' para recuperar el contenido completo
        response = db.supabase.table("nodes").select("id, content, label, type, properties").in_("id", node_ids).execute()
        
        if response.data:
            knowledge_list = response.data
            print(f"    -> ✅ Se recuperaron {len(knowledge_list)} nodos de conocimiento desde Supabase.")


            return knowledge_list
        
        return []
    
    except Exception as e:
        print(f"    -> ❌ Error en retrieve_relevant_knowledge: {e}")
        return []
    


def _run_reflexive_synthesis_cycle(initial_dossier, report_definition):
    """
    Ejecuta un ciclo de síntesis de dos pasadas.
    """
    print("-> 🧠 Ejecutando ciclo de síntesis reflexiva...")
    
    synthesis_pipeline_str = report_definition.get("synthesis_pipeline", "[]")
    synthesis_pipeline = json.loads(synthesis_pipeline_str) if isinstance(synthesis_pipeline_str, str) else synthesis_pipeline_str
    
    if not synthesis_pipeline:
        raise ValueError("El 'synthesis_pipeline' está vacío o no es válido.")
        
    # Asumimos que el "Editor en Jefe" es el primer especialista en este flujo
    editor_specialist_config = synthesis_pipeline[0]
    
    # --- LLAMADA 1: ANÁLISIS Y PREGUNTAS ---
    print("  -> 🧠 Llamada 1: Analizando y generando preguntas...")
    first_pass_json_str = call_single_specialist(
        specialist_config=editor_specialist_config,
        evidence_dossier=initial_dossier
    )
    
    first_pass_data = None
    try:
        first_pass_data = json.loads(first_pass_json_str)
    except json.JSONDecodeError:
        print("  -> ⚠️  [Ciclo Reflexivo] La IA no devolvió un JSON válido en la primera pasada.")

    # --- FASE DE INVESTIGACIÓN (SI ES NECESARIA) ---
    if first_pass_data and first_pass_data.get("status") == "needs_research":
        print("  -> La IA ha solicitado más investigación...")
        questions = first_pass_data.get("questions", [])
        perplexity_answers = {}

        for i, question in enumerate(questions):
            print(f"    -> ❓ Investigando pregunta {i+1}: '{question}'")
            answer = get_perplexity_synthesis(question=question)
            perplexity_answers[f"respuesta_pregunta_{i+1}"] = answer
        
        enriched_dossier = initial_dossier.copy()
        enriched_dossier["follow_up_analysis"] = perplexity_answers
        
        # --- LLAMADA 2: SÍNTESIS FINAL ---
        print("  -> 🧠 Llamada 2: Sintetizando informe final con dossier enriquecido...")
        final_pass_json_str = call_single_specialist(
            specialist_config=editor_specialist_config,
            evidence_dossier=enriched_dossier
        )
        
        final_content_data = None
        try:
            final_content_data = json.loads(final_pass_json_str)
        except json.JSONDecodeError:
            print("  -> ⚠️  [Ciclo Reflexivo] La IA no devolvió un JSON válido en la pasada final.")

        return final_content_data
    else:
        print("  -> La IA ha generado el informe en la primera pasada.")
        return first_pass_data
    

# Pega esta función en quantex/core/report_builder.py

def call_single_specialist(specialist_config: dict, evidence_dossier: dict) -> str:
    """
    (Herramienta de Report Builder)
    Prepara y ejecuta una llamada a un único agente de IA especialista.
    Devuelve la respuesta cruda del modelo.
    """
    try:
        prompt_path = specialist_config.get("prompt_file")
        if not prompt_path:
            raise ValueError(f"No se encontró 'prompt_file' en la configuración del especialista: {specialist_config}")
        
        # get_file_content ahora es una herramienta compartida que importamos
        prompt_template = get_file_content(prompt_path)
        if not prompt_template:
            raise FileNotFoundError(f"No se pudo cargar el archivo de prompt en la ruta: {prompt_path}")

        # Preparamos el dossier para inyectarlo en el prompt
        source_data_str = json.dumps(evidence_dossier, indent=2, default=str)
        system_prompt = prompt_template.replace('{source_data}', source_data_str)
        
        # Llamamos al LLM a través del manager
        response_dict = llm_manager.generate_completion(
            system_prompt=system_prompt,
            user_prompt="Genera tu respuesta en formato JSON según tus instrucciones.",
            task_type="complex" # Usamos un modelo potente para el análisis
        )
        
        # Devolvemos el texto crudo de la respuesta para que la función que llama lo procese
        return response_dict.get('raw_text', '')

    except Exception as e:
        print(f"❌ Error en call_single_specialist: {e}")
        # En caso de error, devolvemos un string vacío para no romper el flujo
        return ""    
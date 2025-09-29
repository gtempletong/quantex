# quantex/jobs/autonomous_researcher.py
import os
import sys
import yaml
import json
import time
import hashlib
from datetime import datetime, timedelta, timezone

# --- Lógica de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importaciones de Quantex ---
from quantex.core.ai_services import ai_services
from quantex.core import llm_manager
from quantex.core.web_tools import get_perplexity_synthesis
from quantex.core.agent_tools import get_file_content, _extract_json_from_response
from quantex.core import database_manager as db
from quantex.core.knowledge_graph.archivist import run_intelligent_archivist_agent
from quantex.core.report_builder import retrieve_relevant_knowledge 
from quantex.core import agent_tools
from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine

# --- Agentes Auxiliares ---

def _generate_research_questions(contexto_completo: dict) -> list:
    """Llama al Agente Generador de Preguntas, pasándole el contexto completo."""
    entity_name = contexto_completo.get("entity_data", {}).get("entity", "desconocida")
    print(f"  -> 🧠 Activando Generador de Preguntas para: '{entity_name}'...")
    
    prompt_template = get_file_content("quantex/core/autoconocimiento/generador_preguntas_investigacion.txt")
    if not prompt_template:
        return []

    # La fuente de datos ahora es el diccionario completo que recibimos.
    source_data_yaml = yaml.dump(contexto_completo, allow_unicode=True)
    
    response_dict = llm_manager.generate_completion(
        system_prompt=prompt_template.replace('{source_data}', source_data_yaml),
        user_prompt="Genera las preguntas de investigación en el formato JSON requerido, basándote en el briefing global y el conocimiento específico del activo.",
        task_complexity='content_synthesis'
    )
    
    json_string = response_dict.get('raw_text', '')
    questions_data = _extract_json_from_response(json_string)
    
    if questions_data and "preguntas_de_investigacion" in questions_data:
        questions = questions_data["preguntas_de_investigacion"]
        print(f"    -> ✅ Se generaron {len(questions)} preguntas dirigidas.")
        return questions
    
    return []

# --- Orquestador Principal ---

def run_curiosity_cycle():
    """
    (Versión Final - Basada en Manifiesto)
    Ejecuta el ciclo de inteligencia leyendo las instrucciones directamente
    desde el archivo 'driver_map.yaml'.
    """
    print("🤖 QUANTEX: Iniciando Ciclo de Inteligencia...")
    ai_services.initialize()
    
    # Inicializar el nuevo motor de ingesta centralizado
    print("🏭 Inicializando Motor de Ingesta Centralizado...")
    ingestion_engine = KnowledgeGraphIngestionEngine()

    # --- OLA 1: LECTURA DEL MANIFIESTO DE INVESTIGACIÓN ---
    print("\n--- 🌊 OLA 1: Leyendo el Manifiesto de Investigación ---")
    
    # La ruta al manifiesto ahora es fija y conocida
    drivers_path = "verticals/mesa_redonda/driver_map.yaml"
    full_path = os.path.join(PROJECT_ROOT, drivers_path)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            # Leemos directamente el plan de investigación desde el YAML
            plan_de_investigacion = yaml.safe_load(f)
    except Exception as e:
        print(f"  -> ❌ Error fatal: No se pudo leer el manifiesto de drivers en '{full_path}': {e}")
        return
        
    print(f"  -> ✅ Manifiesto cargado. Se investigarán {len(plan_de_investigacion)} entidades.")

    # Convertimos la configuración del YAML a la estructura que el resto del script espera.
    preguntas_de_contexto = []
    for entity_config in plan_de_investigacion:
        entity_name = entity_config.get("entity")
        question_text = entity_config.get("research_question_template")
        
        if entity_name and question_text:
            preguntas_de_contexto.append({
                "question_text": question_text,
                "question_type": "TIME_SENSITIVE",
                "entity_name": entity_name 
            })

    # --- OLA 2: INVESTIGACIÓN, DESTILACIÓN Y GUARDADO DEL CONTEXTO ---
    print(f"\n--- 🔎 OLA 2: Investigando y Guardando Contexto para {len(preguntas_de_contexto)} Entidad(es) ---")
    for i, question_obj in enumerate(preguntas_de_contexto):
        question_text = question_obj.get("question_text")
        question_type = question_obj.get("question_type")
        entity_name = question_obj.get("entity_name")
        if not question_text or not question_type or not entity_name: continue
        
        question_hash = hashlib.sha256(question_text.encode()).hexdigest()
        
        print(f"\n--- Procesando activo {i+1}/{len(preguntas_de_contexto)} ---")
        print(f"  -> ❓: {question_text}")

        try:
            # Solicitar respuesta enriquecida (texto + citas)
            resp = get_perplexity_synthesis(
                question_text,
                params={"return_citations": True},
                return_full=True
            )

            # --- INICIO DEL BLOQUE ESPÍA ---
            print("\n🕵️  --- RESPUESTA CRUDA DE PERPLEXITY --- 🕵️")
            print(resp.get("text") if isinstance(resp, dict) else resp)
            print("🕵️  ------------------------------------ 🕵️\n")
            # --- FIN DEL BLOQUE ESPÍA ---
            
            content_text = resp.get("text") if isinstance(resp, dict) else resp
            if content_text:
                source_context = {
                    "source": "Autonomous_Researcher",
                    "topic": entity_name,
                    "source_type": "Síntesis de IA",
                    "original_url": f"perplexity_query_{datetime.now(timezone.utc).isoformat()}",
                    # Guardar trazabilidad básica
                    "citations": (resp.get("citations") if isinstance(resp, dict) else None),
                    "related_questions": (resp.get("related_questions") if isinstance(resp, dict) else None),
                    "model": os.getenv("PERPLEXITY_MODEL", "sonar-pro"),
                    "query": question_text
                }
                
                # Usar el nuevo motor de ingesta centralizado
                result = ingestion_engine.ingest_document(content_text, source_context)
                if result.get("success"):
                    print(f"  -> ✅ {result.get('nodes_created', 0)} nodo(s) creado(s) con conexiones semánticas.")
                else:
                    print(f"  -> ❌ Error en ingesta: {result.get('reason', 'Desconocido')}")

            print("  -> ✅ Contexto para este activo guardado y memoria actualizada.")

        except Exception as e:
            print(f"  -> ❌ Error en el ciclo de curiosidad para '{entity_name}': {e}")


    print("\n🏁 QUANTEX: Ciclo de Inteligencia completado.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

    # La función ya no necesita parámetros, simplemente la ejecutamos.
    run_curiosity_cycle()




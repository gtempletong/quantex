# quantex/core/interactive_tools.py
import traceback
from flask import jsonify
from scipy.spatial.distance import cosine
import json

# Importamos los módulos centrales de Quantex
from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core.agent_tools import get_file_content
from quantex.core import llm_manager
from quantex.core.llm_manager import MODEL_CONFIG


# --- FASE 1: EL ESTRATEGA (Sin cambios) ---
def _run_strategist_agent(user_question: str) -> list:
    """
    (Versión de Alta Calidad v2)
    Usa un modelo potente (obtenido desde MODEL_CONFIG) para crear el plan.
    """
    print("  -> ♟️  [Estratega de Alta Calidad] Creando plan de investigación...")
    try:
        prompt_template = get_file_content("prompts/strategist_agent_prompt.txt")
        if not prompt_template:
            raise ValueError("No se encontró el prompt del Estratega.")

        # --- INICIO DE LA CORRECCIÓN DEFINITIVA ---
        # 1. Definimos la complejidad deseada
        task_complexity = "complex"
        
        # 2. Obtenemos el nombre del modelo desde la configuración central
        model_config = MODEL_CONFIG.get(task_complexity, MODEL_CONFIG['simple'])
        model_name_to_use = model_config.get('primary')
        print(f"    -> 🌡️  Estratega usando modelo de complejidad '{task_complexity}': '{model_name_to_use}'")

        # 3. Llamamos a la función con el parámetro correcto: 'model_name'
        response = llm_manager.generate_structured_output(
            system_prompt=prompt_template,
            user_prompt=f"Pregunta del Usuario: \"{user_question}\"",
            model_name=model_name_to_use, # <-- Usando el parámetro correcto
            output_schema={
                "type": "object",
                "properties": {"plan_de_investigacion": {"type": "array", "items": {"type": "string"}}},
                "required": ["plan_de_investigacion"]
            }
        )
        # --- FIN DE LA CORRECCIÓN DEFINITIVA ---
        
        plan = response.get("plan_de_investigacion", [])
        print(f"  -> ✅ Plan de alta calidad creado con {len(plan)} pasos.")
        return plan
    except Exception as e:
        print(f"  -> ❌ Error en el Estratega: {e}")
        return [user_question]

# --- FASE 2: EL EQUIPO DE INVESTIGACIÓN ---
def _execute_research_plan(plan: list, dossier_content: dict) -> str:
    """
    (Versión Inteligente)
    Ejecuta el plan de investigación, buscando evidencia tanto en la materia prima
    (qualitative_context) como en el razonamiento de la IA (agent_history).
    """
    print("  -> 👨‍💻 [Equipo de Investigación v3.0] Recolectando evidencia Y razonamientos...")
    
    evidence_pool = []
    
    # 1. Cargar la evidencia cruda desde la materia prima
    qualitative_context = dossier_content.get('qualitative_context', {})
    for key, items in qualitative_context.items():
        if isinstance(items, list):
            evidence_pool.extend(items)
        elif isinstance(items, str) and items:
            evidence_pool.extend(item.strip() for item in items.split('\n- ') if item.strip())

    # 2. Extraer los razonamientos del Oráculo desde el agent_history
    print("    -> 🧠 Analizando el 'agent_history' para extraer el razonamiento del Oráculo...")
    agent_history = dossier_content.get('ai_content', {}).get('agent_history', [])
    for step in agent_history:
        if "Oraculo" in step.get("agent_name", ""):
            oraculo_output = step.get("output", {}).get("borrador_sintetizado", {})
            for key, value in oraculo_output.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str):
                            evidence_pool.append(f"Conclusión del Oráculo sobre '{key} - {sub_key}': {sub_value}")
                elif isinstance(value, str):
                    evidence_pool.append(f"Conclusión del Oráculo sobre '{key}': {value}")
            print("    -> ✅ Razonamiento del Oráculo añadido al pool de evidencia.")

    if not evidence_pool:
        return "No se encontró evidencia cualitativa ni razonamientos en el dossier."

    # 3. Vectorizar y ejecutar plan
    evidence_vectors = ai_services.embedding_model.encode(evidence_pool)
    mini_dossier = ""
    for i, topic_to_research in enumerate(plan):
        print(f"    -> Buscando evidencia para: '{topic_to_research[:60]}...'")
        topic_vector = ai_services.embedding_model.encode(topic_to_research)
        
        similarities = [1 - cosine(topic_vector, ev_vec) for ev_vec in evidence_vectors]
        ranked_evidence = sorted(zip(evidence_pool, similarities), key=lambda item: item[1], reverse=True)
        top_evidence_for_topic = [item[0] for item in ranked_evidence[:2]]
        
        mini_dossier += f"\n--- Evidencia y Razonamientos sobre '{topic_to_research}' ---\n"
        mini_dossier += "\n- ".join(top_evidence_for_topic)

    print("  -> ✅ Mini-dossier de evidencia específica construido.")
    return mini_dossier

# --- FASE 3: EL ANALISTA PRINCIPAL ---
def _run_main_analyst_agent(user_question: str, original_conclusion: str, evidence: str, expert_context: dict | None) -> str:
    """
    (Versión con Memoria)
    Sintetiza la respuesta final, considerando la visión estratégica anterior.
    """
    print("  -> 👨‍💼 [Analista Principal v2.0 con Memoria] Sintetizando respuesta final...")
    try:
        prompt_template = get_file_content("prompts/main_analyst_prompt.txt")
        if not prompt_template:
            raise ValueError("No se encontró el prompt del Analista Principal.")

        contexto_memoria = "No se encontró una visión estratégica previa."
        if expert_context:
            contexto_memoria = (
                f"La visión estratégica anterior era '{expert_context.get('current_view_label', 'N/A')}' "
                f"con la tesis: '{expert_context.get('core_thesis_summary', 'N/A')}'"
            )
        
        system_prompt = prompt_template.format(
            pregunta_usuario=user_question,
            conclusion_original=original_conclusion,
            mini_dossier_de_evidencia=evidence,
            contexto_estrategico=contexto_memoria
        )

        # --- INICIO DE LA CORRECCIÓN ---
        response = llm_manager.generate_completion(
            system_prompt=system_prompt,
            user_prompt="Escribe tu respuesta final, como se te indicó.",
            task_complexity="complex"  # <-- Corregido de 'reasoning' a 'complex'
        )
        # --- FIN DE LA CORRECCiÖN ---

        print("  -> ✅ Respuesta final generada.")
        return response.get("raw_text", "No pude generar una respuesta.")
    except Exception as e:
        print(f"  -> ❌ Error en el Analista Principal: {e}")
        return f"Ocurrió un error al sintetizar la respuesta: {e}"

# --- FUNCIÓN ORQUESTADORA PRINCIPAL ---
def answer_report_question_with_reasoning(parameters: dict, user_message: str) -> dict:
    """
    (Orquestador v3.1 - Con Memoria Estratégica)
    Orquesta el proceso, cargando y pasando correctamente el 'expert_context' al equipo.
    """
    print("-> 🧠 [Equipo de Analistas v3.1 con Memoria] Iniciando proceso...")
    try:
        artifact_id = parameters.get("artifact_id")
        conclusion_text = parameters.get("conclusion_text") or user_message
        if not artifact_id or not conclusion_text:
            raise ValueError("Faltan artifact_id o el texto de la conclusión.")

        artifact = db.get_artifact_by_id(artifact_id)
        if not artifact:
            return jsonify({"error": f"No se encontró el artefacto con ID {artifact_id}."})

        dossier_content = artifact.get("content_dossier", {})
        if not dossier_content:
            return jsonify({"error": "Este informe no tiene un content_dossier trazable."})

        report_keyword = artifact.get("report_keyword")
        expert_context = db.get_expert_context(report_keyword)

        research_plan = _run_strategist_agent(user_question=user_message)
        specific_evidence = _execute_research_plan(plan=research_plan, dossier_content=dossier_content)
        
        final_answer = _run_main_analyst_agent(
            user_question=user_message,
            original_conclusion=conclusion_text,
            evidence=specific_evidence,
            expert_context=expert_context
        )

        response_payload = { "response_blocks": [{"type": "text", "content": final_answer, "display_target": "chat"}] }
        return jsonify(response_payload)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)})

# --- FUNCIÓN SECUNDARIA (Sin cambios desde la última vez) ---
def get_evidence_for_conclusion(parameters: dict) -> dict:
    """
    (El Detective v2.0 - Refactorizado)
    Busca evidencia relevante directamente en el 'content_dossier' del artefacto.
    """
    print("-> 🕵️  [Detective de Evidencia v2.0] Iniciando búsqueda...")
    try:
        artifact_id = parameters.get("artifact_id")
        conclusion_text = parameters.get("conclusion_text")
        if not artifact_id or not conclusion_text:
            raise ValueError("Faltan artifact_id o conclusion_text.")

        artifact = db.get_artifact_by_id(artifact_id)
        if not artifact:
            return jsonify({"error": f"No se encontró el artefacto con ID {artifact_id}."})

        dossier_content = artifact.get("content_dossier", {})
        if not dossier_content:
            return jsonify({"error": "Este informe no tiene un content_dossier trazable."})
        
        qualitative_context = dossier_content.get('qualitative_context', {})

        evidence_pool = []
        for key, items in qualitative_context.items():
            if isinstance(items, list):
                evidence_pool.extend(items)
            elif isinstance(items, str) and items:
                evidence_pool.extend(item.strip() for item in items.split('\n- ') if item.strip())

        if not evidence_pool:
             return jsonify({"error": "No se encontró contexto cualitativo en el dossier de origen."})

        print(f"  -> Buscando evidencia para: '{conclusion_text[:50]}...'")
        conclusion_vector = ai_services.embedding_model.encode(conclusion_text)
        evidence_vectors = ai_services.embedding_model.encode(evidence_pool)

        similarities = [1 - cosine(conclusion_vector, ev_vec) for ev_vec in evidence_vectors]
        ranked_evidence = sorted(zip(evidence_pool, similarities), key=lambda item: item[1], reverse=True)
        top_evidence = [item[0] for item in ranked_evidence[:3]]

        print("  -> ✅ Evidencia encontrada y clasificada.")

        evidence_string = "Basado en la evidencia del dossier:\n\n- " + "\n\n- ".join(top_evidence)
        
        response_payload = {
            "response_blocks": [
                {"type": "text", "content": evidence_string, "display_target": "chat"}
            ]
        }
        return jsonify(response_payload)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)})
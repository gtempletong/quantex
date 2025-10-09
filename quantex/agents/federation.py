# quantex/agents/federation.py (VERSIÓN 3.3 - FINAL Y LIMPIA)

import json
import os
import sys

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- INICIO DE LA MODIFICACIÓN: Importaciones Corregidas ---
from quantex.core import llm_manager
from quantex.core.tool_catalog_manager import build_tool_catalog
from quantex.grafo.interfaz_universal import get_grafo_interface
# La importación de get_evidence_for_conclusion ya no se usa directamente aquí, es manejada por el server.
# --- FIN DE LA MODIFICACIÓN ---

def get_file_content(relative_path):
    full_path = os.path.join(PROJECT_ROOT, relative_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo de prompt en {full_path}")
        return ""

def _classify_interactive_intent(user_message: str) -> dict:
    """
    Usa un LLM para clasificar la intención de un usuario después de ver un informe.
    """
    print("  -> 🤔 [Router] Clasificando intención interactiva...")
    try:
        prompt_template = get_file_content("prompts/interactive_intent_classifier.txt")
        
        response = llm_manager.generate_structured_output(
            system_prompt=prompt_template,
            user_prompt=f"Clasifica el siguiente mensaje de usuario:\n---\n{user_message}",
            model_name="claude-3-haiku-20240307",
            output_schema={
                "type": "object",
                "properties": {
                    "intencion": {"type": "string"},
                    "texto_a_rastrear": {"type": ["string", "null"]}
                },
                "required": ["intencion"]
            }
        )
        print(f"  -> ✅ Intención clasificada: {response}")
        return response
    except Exception as e:
        print(f"  -> ❌ Error al clasificar la intención: {e}")
        return {"intencion": "PREGUNTA_GENERAL"}

def run_router_agent(user_message: str, state: dict, dynamic_catalog: list, conversation_history: list) -> dict:
    """
    (Versión Definitiva con Graph Explorer)
    Intercepta las peticiones interactivas y crea un plan directamente.
    Si no es una petición interactiva, delega la decisión al Router de IA genérico.
    """
    
     # CAPA 0: Lógica de Sesión Activa (La Regla "No Molestar")
    active_session_flow = state.get('active_session')
    if active_session_flow:
        print(f"  -> 🚪 [Router] Sesión activa '{active_session_flow}' detectada. Cediendo control al manejador activo.")
        # Devolvemos el mismo flow_type para que el server lo re-enrute al handler correcto.
        return {
            "flow_type": active_session_flow,
            "parameters": state.get('active_session_params', {}) # Pasamos los parámetros originales
        }

    # CAPA 0.5: Detección de Comandos de Herramientas (PRIORIDAD ALTA)
    # Esta capa se ejecuta ANTES del grafo para evitar conflictos
    user_lower = user_message.lower()
    
    # Detectar comandos de herramientas específicos
    is_tool_command = any(cmd in user_lower for cmd in ["ejecuta", "genera", "corre", "run", "execute"])
    if is_tool_command:
        print("  -> 🛠️ [Router] Comando de herramienta detectado, saltando detección de grafo y noticias")
        # NO retornar aquí, continuar al siguiente nivel para procesar la herramienta específica



    # CAPA 0.6: Atajos para reportes técnicos específicos por lenguaje natural
    # - "Comité Técnico Mercado" -> comite_tecnico_mercado
    # - "Comité Técnico CLP"/"CLP" -> comite_tecnico_clp
    # - "Generar consolidado" -> generate_consolidated_report
    # - "Fair Value" -> run_fair_value_analysis
    try:
        # Detectar comando de Fair Value (PRIORIDAD ALTA)
        if "fair value" in user_lower or "fairvalue" in user_lower:
            if "clp" in user_lower or "peso chileno" in user_lower:
                print("  -> 🧭 [Router] Mapeo directo a 'run_fair_value_analysis' para CLP")
                return {
                    "flow_type": "run_fair_value_analysis",
                    "parameters": {"ticker": "SPIPSA.INDX", "report_keyword": "fair_value_clp"}
                }
            elif "cobre" in user_lower or "copper" in user_lower:
                print("  -> 🧭 [Router] Mapeo directo a 'run_fair_value_analysis' para Cobre")
                return {
                    "flow_type": "run_fair_value_analysis",
                    "parameters": {"ticker": "HG=F", "report_keyword": "fair_value_cobre"}
                }
            else:
                print("  -> 🧭 [Router] Mapeo directo a 'run_fair_value_analysis' (genérico)")
                return {
                    "flow_type": "run_fair_value_analysis",
                    "parameters": {}
                }
        
        # Detectar comando de consolidado independiente
        if "generar consolidado" in user_lower or "consolidado" in user_lower:
            if "comité técnico mercado" in user_lower or "comite tecnico mercado" in user_lower or "mercado" in user_lower:
                print("  -> 🧭 [Router] Mapeo directo a 'generate_consolidated_report' para mercado")
                return {
                    "flow_type": "generate_consolidated_report",
                    "parameters": {"report_keyword": "comite_tecnico_mercado"}
                }
            elif "comité técnico clp" in user_lower or "comite tecnico clp" in user_lower or "clp" in user_lower:
                print("  -> 🧭 [Router] Mapeo directo a 'generate_consolidated_report' para CLP")
                return {
                    "flow_type": "generate_consolidated_report",
                    "parameters": {"report_keyword": "comite_tecnico_clp"}
                }
        
        # Detectar comando de comité técnico completo
        if "comité técnico mercado" in user_lower or "comite tecnico mercado" in user_lower or ("mercado" in user_lower and "comité técnico" in user_lower):
            print("  -> 🧭 [Router] Mapeo directo a 'comite_tecnico_mercado'")
            return {
                "flow_type": "run_technical_committee",
                "parameters": {"report_keyword": "comite_tecnico_mercado"}
            }

        if "comité técnico clp" in user_lower or "comite tecnico clp" in user_lower or ("clp" in user_lower and "comité técnico" in user_lower):
            print("  -> 🧭 [Router] Mapeo directo a 'comite_tecnico_clp'")
            return {
                "flow_type": "run_technical_committee",
                "parameters": {"report_keyword": "comite_tecnico_clp"}
            }
    except Exception:
        pass

    # CAPA 1: Lógica de Interacción Contextual
    if state.get('artifact_id'):
        print("  -> [Router] Contexto de artefacto activo detectado. Analizando intención interactiva...")
        intent_data = _classify_interactive_intent(user_message)
        intent = intent_data.get("intencion")

        if intent == "RASTREAR_EVIDENCIA":
            print("  -> 🚀 [Router] Intención de Trazabilidad detectada. Creando plan para el 'Equipo de Analistas'...")
            
            # --- INICIO DE LA MODIFICACIÓN ---
            # El Router ahora solo extrae el texto. El artifact_id se manejará en el servidor.
            final_plan = {
                "flow_type": "trace_evidence_for_conclusion",
                "parameters": {
                    "conclusion_text": intent_data.get("texto_a_rastrear")
                }
            }
            # --- FIN DE LA MODIFICACIÓN ---

            print(f"     -> ✅ Plan Interactivo Corregido y Aceptado: {final_plan}")
            return final_plan

    # CAPA 2: Lógica de Selección de Herramientas (Si la Capa 1 no actuó)
    print("-> 🧠 [Router V3 - Tool-Use] Iniciando proceso de decisión...")
    
    try:
        tool_catalog = build_tool_catalog()
        if not tool_catalog:
            raise ValueError("El catálogo de herramientas está vacío. Revisa FLOW_REGISTRY.")

        system_prompt = (
            "Eres Quantex, un asistente de IA para análisis financiero. "
            "Tu misión es analizar la petición del usuario y seleccionar la herramienta "
            "más apropiada de la lista proporcionada para ejecutar la tarea. "
            "Responde únicamente seleccionando una herramienta."
        )

        router_decision = llm_manager.generate_completion(
            task_complexity='router',
            system_prompt=system_prompt,
            user_prompt=user_message,
            tools=tool_catalog
        )

        if 'error' in router_decision:
            raise ValueError(f"El LLM devolvió un error: {router_decision['error']}")

        if 'tool_name' in router_decision:
            final_plan = {
                "flow_type": router_decision.get("tool_name"),
                "parameters": router_decision.get("tool_input", {})
            }
            print(f"     -> ✅ Plan de IA Aceptado: {final_plan}")
            return final_plan
        else:
            print("     -> ⚠️ La IA respondió con texto, no seleccionó una herramienta. Usando fallback.")
            return {"flow_type": "out_of_domain_response", "parameters": {}}

    except Exception as e:
        print(f"\n     -> ❌ Fallo Crítico en el Router ({e}). Activando red de seguridad.")
        final_plan = {"flow_type": "out_of_domain_response", "parameters": {}}
        print(f"     -> Plan de Fallback Seguro: {final_plan}")
        return final_plan
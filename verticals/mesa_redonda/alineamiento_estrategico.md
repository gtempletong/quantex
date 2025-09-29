Plan de Implementación: Sesión de Alineamiento Estratégico (Human-in-the-Loop)
1. Objetivo y Visión General
El objetivo de esta funcionalidad es crear un nuevo flujo de trabajo en Quantex que permita al estratega humano (el usuario) tener una conversación de alineamiento con un agente de IA especializado. El propósito es analizar eventos de mercado de alto impacto, debatir sobre el pre-informe generado por el "Oráculo", e inyectar el juicio y la experiencia humana en el sistema.

La conclusión de este diálogo se registrará como una pieza de evidencia de máxima prioridad (un "Briefing Estratégico") que servirá como directiva principal para la generación del informe final, resolviendo así el "dilema del analista" y asegurando que los cambios de visión sean un proceso deliberado, auditable y robusto.

2. Componentes Clave
Archivos a Crear:

quantex/prompts/impact_analyst_prompt.md

Archivos a Modificar:

quantex/templates/index.html

quantex/core/flow_registry.py

quantex/api/server.py

quantex/core/database_manager.py

verticals/mesa_redonda/engine_mesa_redonda.py

prompts/prompt_oraculo_clp.md (y otros prompts de Oráculos)

3. Implementación Detallada por Fases
Fase 1: El Disparador (Iniciar la Sesión)
Le enseñamos al sistema a reconocer esta nueva tarea y le damos al usuario una forma de iniciarla después de ver un pre-informe.

1.1. Modificar la Interfaz de Usuario

Archivo: quantex/templates/index.html

Acción: Añadir nuevas opciones al menú para iniciar la sesión. Estas opciones deben aparecer idealmente después de que se ha generado un borrador.

HTML

<optgroup label="Análisis Estratégico">
    <option value="iniciar sesion de alineamiento para el clp">Alinear Tesis (CLP)</option>
    <option value="iniciar sesion de alineamiento para el cobre">Alinear Tesis (Cobre)</option>
</optgroup>
1.2. Registrar el Nuevo Flujo

Archivo: quantex/core/flow_registry.py

Acción: Añadir la definición del nuevo flujo strategic_alignment_session.

Python

# En flow_registry.py, dentro del diccionario FLOW_REGISTRY

"strategic_alignment_session": {
    "handler_name": "_handle_strategic_alignment_session",
    "description": "Inicia una conversación interactiva con un analista de IA para analizar y refinar la tesis de un informe borrador.",
    "parameters": {
        "type": "object",
        "properties": {
            "report_keyword": {
                "type": "string",
                "description": "El tópico (ej. 'clp' o 'cobre') para el cual se iniciará la sesión de alineamiento."
            }
        },
        "required": ["report_keyword"]
    }
},
Fase 2: El Agente Conversacional ("Analista de Impacto")
Creamos el agente de IA que conversará con el usuario y el manejador que orquestará el diálogo.

2.1. Crear el Prompt del Agente

Archivo a Crear: quantex/prompts/impact_analyst_prompt.md

Contenido:

Markdown

# ROL Y OBJETIVO
- Eres el "Analista de Alineamiento" de Quantex. Tu misión es actuar como un "sparring partner" para el estratega humano.
- Tu objetivo es dialogar sobre el informe borrador generado recientemente, incorporar la perspectiva del estratega y llegar a un consenso para la versión final.
- Tu tono debe ser colaborativo, analítico y socrático (hacer preguntas para profundizar).

# EXPEDIENTE DEL CASO (Contexto que has estudiado para esta reunión)
- **Visión Estratégica Actual:** {tesis_actual}
- **Prompt del Oráculo Original:** {prompt_oraculo}
- **Borrador a Discutir (Salida del Oráculo):** {borrador_actual}
- **Historial de esta Sesión de Alineamiento:**
{historial_conversacion}

# TU MISIÓN EN ESTA CONVERSACIÓN
1.  **Iniciar el Diálogo:** Comienza la conversación presentando un resumen muy breve del borrador actual y la tesis vigente, y pregunta al estratega cuál es su evaluación inicial.
2.  **Escuchar y Profundizar:** Analiza la respuesta del estratega. Usa tu conocimiento del expediente para hacer preguntas de seguimiento. Por ejemplo:
    - Si el estratega no está de acuerdo con una conclusión, pregunta: "¿Qué pieza de la evidencia original crees que el Oráculo subestimó o malinterpretó?".
    - Si el estratega quiere cambiar una regla, pregunta: "Entiendo. El prompt del Oráculo indica X. ¿Propones que para este informe ignoremos esa regla y la reemplacemos con Y?".
3.  **Buscar el Consenso:** Tu objetivo es llegar a un acuerdo. Cuando sientas que el análisis está completo, resume los puntos clave del nuevo enfoque en 2-3 directivas claras.
4.  **Pedir Aprobación:** Termina preguntando al estratega si está de acuerdo en guardar este resumen como el "Briefing Estratégico" para la versión final del informe. Responde de forma concisa.
2.2. Crear el Manejador de la Conversación

Archivo: quantex/api/server.py

Acción: Añadir la nueva función manejadora, que gestionará el estado de la conversación.

Python

# En server.py, junto a los otros manejadores

@register_handler("strategic_alignment_session")
def _handle_strategic_alignment_session(parameters: dict, state: dict, user_message: str, **kwargs) -> dict:
    topic = parameters.get("report_keyword")
    session_id = state.get("session_id")
    
    # Gestiona el historial de la sesión de alineamiento
    alignment_history = state.get("alignment_session_history", [])
    
    # Condición de salida: guardar el briefing y limpiar el estado
    if "guardar briefing" in user_message.lower() or "estamos alineados" in user_message.lower():
        # (Opcional, pero recomendado) Usar un último llamado a la IA para resumir la conversación
        final_briefing = "\n".join([f"{turn['role']}: {turn['content']}" for turn in alignment_history])
        db.save_briefing_node(topic, final_briefing)
        
        state.pop("alignment_session_history", None) # Limpiamos la memoria temporal
        return jsonify({
            "response_blocks": [{"type": "text", "content": f"✅ Briefing Estratégico para '{topic}' guardado. Ahora puedes generar el informe final para que lo utilice.", "display_target": "chat"}],
            "state": state
        })

    # Si la conversación está empezando, cargamos el contexto completo
    if not alignment_history:
        draft = db.get_latest_draft_artifact(topic)
        if not draft:
            return jsonify({"response_blocks": [{"type": "text", "content": f"No se encontró un pre-informe para '{topic}'. Por favor, genéralo primero.", "display_target": "chat"}]})
        
        report_def = db.get_report_definition_by_topic(topic)
        prompt_oraculo = get_file_content(report_def.get("prompt_file"))
        expert_context = db.get_expert_context(topic)
        
        state['alignment_context'] = {
            "tesis_actual": expert_context.get('core_thesis_summary', 'No definida') if expert_context else 'No definida',
            "prompt_oraculo": prompt_oraculo,
            "borrador_actual": json.dumps(draft.get('content_dossier', {}).get('ai_content', {}), indent=2)
        }

    # Continuación del diálogo
    alignment_history.append({"role": "Humano", "content": user_message})
    
    context = state['alignment_context']
    prompt_template = get_file_content("prompts/impact_analyst_prompt.md")
    prompt = prompt_template.format(
        tesis_actual=context['tesis_actual'],
        prompt_oraculo=context['prompt_oraculo'],
        borrador_actual=context['borrador_actual'],
        historial_conversacion="\n".join([f"{turn['role']}: {turn['content']}" for turn in alignment_history])
    )

    response = llm_manager.generate_completion(system_prompt=prompt, user_prompt="Continúa la conversación.", task_complexity='complex')
    ai_response_text = response.get('raw_text', 'No pude procesar la respuesta.')

    alignment_history.append({"role": "IA", "content": ai_response_text})
    state["alignment_session_history"] = alignment_history

    return jsonify({
        "response_blocks": [{"type": "text", "content": ai_response_text, "display_target": "chat"}],
        "state": state
    })
Fase 3: La Persistencia (Guardar el Briefing como un Nodo)
Añadimos la capacidad a nuestro database_manager de guardar la transcripción de la conversación como un Nodo de alta prioridad.

Archivo: quantex/core/database_manager.py

Acción: Añadir la nueva función (usando la versión que ya te había propuesto).

Python

# En database_manager.py

def save_briefing_node(topic: str, briefing_content: str) -> str:
    """
    Guarda un Briefing Estratégico como un Nodo de alta prioridad.
    """
    print(f"  -> 💾 Guardando 'Briefing Estratégico' para '{topic}' como Nodo...")
    try:
        node_id = str(uuid.uuid4())
        node_properties = {
            "source": "Human In The Loop",
            "source_type": "Briefing Estratégico",
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table('nodes').insert({
            "id": node_id,
            "type": "Briefing",
            "label": f"Briefing Estratégico - {topic}",
            "content": briefing_content,
            "properties": node_properties
        }).execute()

        print("    -> ✅ Briefing guardado exitosamente como Nodo.")
        return node_id
    except Exception as e:
        print(f"    -> ❌ Error guardando el Briefing como Nodo: {e}")
        return None
Fase 4: La Integración (Usar el Briefing)
Finalmente, le enseñamos al "Curador" y al "Oráculo" a usar esta nueva evidencia.

4.1. Modificar el "Curador de Dossier"

Archivo: verticals/mesa_redonda/engine_mesa_redonda.py

Acción: Añadir un bloque al principio de la función _run_dossier_curator para que busque activamente el briefing.

Python

# En engine_mesa_redonda.py, dentro de _run_dossier_curator

def _run_dossier_curator(report_keyword: str, report_def: dict) -> dict:
    # ... (inicio de la función)
    final_qualitative_context = {}
    
    # --- INICIO DE LA NUEVA LÓGICA ---
    print("    -> 🕵️  Buscando 'Briefing Estratégico' reciente...")
    # Buscamos en la tabla de nodos un briefing del último día
    response = db.supabase.table('nodes').select('content').eq('type', 'Briefing').eq('properties->>topic', report_keyword).gte('properties->>timestamp', (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()).order('properties->>timestamp', desc=True).limit(1).execute()
    
    if response.data:
        briefing_content = response.data[0]['content']
        final_qualitative_context["briefing_del_estratega"] = briefing_content
        print("    -> ✅ 'Briefing Estratégico' encontrado y añadido al dossier.")
    # --- FIN DE LA NUEVA LÓGICA ---
    
    # ... (el resto de la función que cosecha noticias, etc., continúa aquí) ...
4.2. Actualizar el Prompt del "Oráculo"

Archivo: prompts/prompt_oraculo_clp.md (y otros)

Acción: Añadir una nueva sección que le dé máxima prioridad al briefing.

Markdown

# ... (al principio del prompt, después del ROL Y OBJETIVO) ...

# EVIDENCIA PRIORITARIA: BRIEFING DEL ESTRATEGA
- Tu dossier puede contener una sección llamada `briefing_del_estratega`.
- Si existe, esta sección contiene la directriz estratégica final de un humano y es tu **fuente de verdad más importante**.
- Tu análisis principal DEBE estar alineado con la visión expresada en este briefing. Usa el resto de la evidencia para sustentar, complementar o matizar esta visión principal.
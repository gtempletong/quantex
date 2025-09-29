Implementación de Trazabilidad Explícita en Respuestas de IA (Quantex)
1. Objetivo
El objetivo de esta mejora es transformar el sistema de Preguntas y Respuestas (Q&A) de Quantex para que las respuestas generadas por la IA no solo sean una síntesis, sino un argumento auditable. Para lograrlo, se modificará el sistema para que la IA cite explícitamente las piezas de evidencia del dossier original que utiliza para formular cada una de sus afirmaciones.

Esto hace que el informe "viva", permitiendo al usuario interactuar y verificar el razonamiento detrás de las conclusiones.

2. Arquitectura de la Solución
La solución se implementa en dos pasos quirúrgicos que separan la preparación de los datos de las instrucciones a la IA:

Paso 1: Etiquetado de la Evidencia (Python): Se modifica el "Equipo de Investigación" (interactive_tools.py) para que, después de recolectar la evidencia relevante, la formatee y la numere de forma clara (ej. [EVIDENCIA 1], [EVIDENCIA 2]).

Paso 2: Exigencia de Citas (Prompt): Se actualiza el prompt del "Analista Principal" con una regla estricta que le obliga a utilizar las etiquetas numeradas de la evidencia al construir su respuesta.

3. Implementación Técnica
Paso 1: Modificar el "Equipo de Investigación" en Python
El objetivo es que la función _execute_research_plan entregue un "mini-dossier" con la evidencia numerada.

Archivo a modificar: quantex/core/interactive_tools.py

Instrucción: Reemplazar la función _execute_research_plan existente con el siguiente código:

Python

# quantex/core/interactive_tools.py

def _execute_research_plan(plan: list, dossier_content: dict) -> str:
    """
    (Versión 2.0 - Con Evidencia Numerada)
    Ejecuta el plan de investigación y construye un mini-dossier con
    evidencia única y numerada para ser citada.
    """
    print("  -> 👨‍💻 [Equipo de Investigación] Recolectando y etiquetando evidencia...")
    
    # 1. Construir el "lago" de evidencia desde el dossier
    evidence_pool = []
    qualitative_context = dossier_content.get('qualitative_context', {})
    for key, items in qualitative_context.items():
        if isinstance(items, list):
            evidence_pool.extend(items)
        elif isinstance(items, str) and items:
            evidence_pool.extend(item.strip() for item in items.split('\n- ') if item.strip())

    if not evidence_pool:
        return "No se encontró evidencia cualitativa en el dossier."

    # 2. Vectorizar toda la evidencia una sola vez para eficiencia
    evidence_vectors = ai_services.embedding_model.encode(evidence_pool)
    
    # 3. Recolectar la mejor evidencia para cada paso del plan
    dossier_items = []
    for topic_to_research in plan:
        print(f"    -> Buscando evidencia para: '{topic_to_research[:60]}...'")
        topic_vector = ai_services.embedding_model.encode(topic_to_research)
        
        similarities = [1 - cosine(topic_vector, ev_vec) for ev_vec in evidence_vectors]
        ranked_evidence = sorted(zip(evidence_pool, similarities), key=lambda item: item[1], reverse=True)
        
        # Añadimos la mejor evidencia a nuestra lista (top 2 por cada tema)
        dossier_items.extend([item[0] for item in ranked_evidence[:2]])

    # 4. Construir el mini-dossier final con evidencia numerada y única
    # Usamos dict.fromkeys para eliminar duplicados manteniendo el orden de aparición
    unique_evidence = list(dict.fromkeys(dossier_items))
    mini_dossier = ""
    for i, evidence_text in enumerate(unique_evidence):
        mini_dossier += f"[EVIDENCIA {i+1}]: \"{evidence_text.strip()}\"\n\n"

    print("  -> ✅ Mini-dossier de evidencia específica construido y numerado.")
    return mini_dossier
Paso 2: Actualizar el "Cerebro" del Analista Principal (Prompt)
El objetivo es darle al agente final la instrucción explícita de citar sus fuentes.

Archivo a modificar/crear: prompts/main_analyst_prompt.txt

Instrucción: Reemplazar todo el contenido del archivo con el siguiente texto:

Markdown

# ROL Y OBJETIVO
- Eres el "Analista Principal" del equipo de investigación de Quantex.
- Tu misión es responder de forma clara y razonada a la pregunta de un usuario sobre una conclusión específica de un informe.
- Tu respuesta debe basarse **única y exclusivamente** en la evidencia proporcionada en el "mini-dossier".

# CONTEXTO DE LA TAREA
- Pregunta del Usuario: "{pregunta_usuario}"
- Conclusión Original del Informe (sobre la cual se pregunta): "{conclusion_original}"
- Mini-Dossier de Evidencia (tu única fuente de verdad):
---
{mini_dossier_de_evidencia}
---

# REGLA DE ORO: CITACIÓN OBLIGATORIA
- Al redactar tu respuesta final, DEBES justificar tus afirmaciones citando la evidencia específica que se te proporcionó.
- Utiliza el formato [EVIDENCIA X] al final de cada oración o idea que se base en una pieza de evidencia.
- Si una idea se basa en múltiples piezas de evidencia, puedes citarlas juntas, por ejemplo: [EVIDENCIA 1, 3].
- Tu credibilidad depende de la trazabilidad de tu análisis. No hagas afirmaciones que no estén respaldadas por la evidencia proporcionada.

# MISIÓN
- Lee la pregunta del usuario.
- Lee toda la evidencia numerada en el mini-dossier.
- Sintetiza una respuesta directa y profesional a la pregunta, utilizando la evidencia para construir tu argumento.
- Asegúrate de seguir la REGLA DE ORO y citar tus fuentes en cada paso.
4. Resultado Esperado
Al implementar estos dos cambios, la salida del sistema de Q&A se transforma.

Antes:

"El sesgo del Cobre es bajista debido a un aumento en los inventarios y una menor demanda de China."

Después:

"El sesgo del Cobre es bajista, principalmente por dos factores. Primero, se ha observado un significativo aumento en los inventarios de la LME esta semana [EVIDENCIA 1]. Segundo, los últimos datos apuntan a una contracción en el sector manufacturero de China, lo que reduce las expectativas de demanda [EVIDENCIA 2]."

Con esta modificación, el sistema pasa de ser un generador de texto a ser una verdadera herramienta de razonamiento auditable.
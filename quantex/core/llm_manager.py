import os
import io
import json
import base64
import re
import PIL
from dotenv import load_dotenv
import google.generativeai as genai
from quantex.core.ai_services import ai_services

# --- Cargar variables de entorno ---
load_dotenv()

# --- Importaciones de clientes de IA ---
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- CONFIGURACIÓN DE CLIENTES DE IA ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CLIENTS = {}

if anthropic and ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    CLIENTS['claude-sonnet-4-20250514'] = { "client": anthropic_client, "name": "Anthropic" }
    CLIENTS['claude-3-haiku-20240307'] = { "client": anthropic_client, "name": "Anthropic" }
    CLIENTS['claude-3-5-haiku-20241022'] = { "client": anthropic_client, "name": "Anthropic" }

if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Añadimos todos los modelos de Gemini que usamos en nuestras recetas
    CLIENTS['gemini-2.5-pro'] = { "client": genai.GenerativeModel('gemini-2.5-pro'), "name": "Google" }
    CLIENTS['gemini-2.5-flash'] = { "client": genai.GenerativeModel('gemini-2.5-flash'), "name": "Google" }
    CLIENTS['gemini-2.0-flash'] = { "client": genai.GenerativeModel('gemini-2.0-flash'), "name": "Google" }


# --- CONFIGURACIÓN DE MODELOS POR TAREA ---
MODEL_CONFIG = {
    'router': {
        'primary': 'claude-3-haiku-20240307',
        'fallback': 'gemini-2.0-flash',
        'temperature': 0.1,
        'max_tokens': 1024,
    },
    'content_synthesis': {
        'primary': 'claude-3-haiku-20240307',
        'fallback': 'gemini-2.0-flash',
        'temperature': 0.5,
        'max_tokens': 4096,
    },

    'committee_synthesis': { 
        'primary': 'gemini-2.5-flash',
        'fallback': 'claude-sonnet-4-20250514',
        'temperature': 0.5,
        'max_tokens': 4096,
    },

    'complex': {
        'primary': 'claude-sonnet-4-20250514',
        'fallback': 'gemini-2.5-pro',
        'temperature': 0.5,
        'max_tokens': 4096,
    },

        'simple': {
        'primary': 'claude-3-haiku-20240307',
        'fallback': 'gemini-2.0-flash',
        'temperature': 0.1,
        'max_tokens': 4096,
    },

    # 'claude-sonnet-4-20250514'#
    #'gemini-2.5-pro'#

    'reasoning': {
        'primary': 'claude-sonnet-4-20250514',
        'fallback': 'gemini-2.5-pro',
        'temperature': 0.3, 
        'max_tokens': 2048,
    },

    'default': {
        'primary': 'claude-3-haiku-20240307',
        'fallback': 'gemini-2.0-flash',
        'temperature': 0.7,
        'max_tokens': 2048,
    },
    
    'relationship_analysis': { 
        'primary': 'claude-3-haiku-20240307',
        'fallback': 'gemini-2.0-flash',
    'temperature': 0.1, 
    'max_tokens': 1024,
    }
}

def generate_completion(
    task_complexity: str,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    tools: list | None = None,
    **kwargs
) -> dict:
    """
    (Versión 6.0 - Con Fallback Inteligente Restaurado)
    Genera una completación, intentando primero con el modelo primario y, si falla,
    automáticamente intenta con el modelo de respaldo (fallback).
    """
    model_config = MODEL_CONFIG.get(task_complexity, MODEL_CONFIG['default'])
    models_to_try = [model_config['primary'], model_config.get('fallback')]

    for model_name in models_to_try:
        if not model_name or model_name not in CLIENTS:
            continue

        client_info = CLIENTS[model_name]
        client = client_info['client']
        api_provider = client_info['name']

        api_params = {
            "model": model_name,
            "max_tokens": model_config.get('max_tokens', 4096),
            "temperature": model_config.get('temperature', 0.5),
            "messages": [{"role": "user", "content": user_prompt}]
        }
        if system_prompt:
            api_params["system"] = system_prompt
        
        # Lógica para el modo de herramientas (solo para Anthropic por ahora)
        if tools and api_provider == "Anthropic":
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "any"}
            print(f"-> Llamando a {api_provider} ({model_name}) en MODO HERRAMIENTA...")
        else:
            print(f"-> Llamando a {api_provider} ({model_name}) en MODO TEXTO...")

        try:
            # --- INTENTO DE LLAMADA A LA API ---
            if api_provider == "Anthropic":
                response = client.messages.create(**api_params)
                if response.stop_reason == "tool_use":
                    tool_call = next((block for block in response.content if block.type == 'tool_use'), None)
                    if tool_call:
                        print(f"   -> ✅ Herramienta seleccionada por la IA: '{tool_call.name}'")
                        return {"tool_name": tool_call.name, "tool_input": tool_call.input}
                else:
                    raw_text = response.content[0].text
                    return {"raw_text": raw_text}
            
            elif api_provider == "Google":
                # La API de Gemini no usa 'system' prompt, lo añadimos al contenido
                full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
                response = client.generate_content(full_prompt)
                return {"raw_text": response.text}

        except Exception as e:
            print(f"    -> ⚠️  Fallo en la llamada a la API ({model_name}): {e}")
            # Si falló el primario, el bucle continuará con el fallback.
            # Si falla el fallback, el bucle terminará y se devolverá el error final.
            continue 

    # Si salimos del bucle sin éxito, es que todos los modelos fallaron.
    return {"error": f"Fallo en la llamada a todos los modelos de IA configurados."}

# Esta función ya no es necesaria para el router, pero la dejamos por si 
# otras partes del sistema la usan. La renombramos para ser más claros.
def _legacy_extract_and_parse_json(text: str) -> dict:
    """
    (LEGACY) Extrae un bloque de código JSON de un string y lo parsea.
    """
    json_match = re.search(r'```json\n({.*?})\n```', text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'({.*?})', text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Error al decodificar JSON de la IA: {e}", "raw_text": json_str}
    else:
        return {"error": "No se encontró un bloque JSON en la respuesta de la IA.", "raw_text": text}
    
def _clean_and_extract_json(raw_text: str) -> str:
    """
    Busca y extrae el primer bloque JSON completo de una cadena de texto.
    Es robusto contra texto introductorio o final que a veces añaden los LLMs.
    """
    if not isinstance(raw_text, str):
        return ""

    # Encontrar el índice de la primera llave de apertura
    start_index = raw_text.find('{')
    # Encontrar el índice de la última llave de cierre
    end_index = raw_text.rfind('}')

    # Si se encuentran ambas, extraer la subcadena
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return raw_text[start_index:end_index + 1]
    
    # Si no se encuentra un JSON válido, devolver la cadena original para que falle en el parseo
    return raw_text    
    

# Reemplaza tu función entera con esta versión final y multimodal en quantex/core/llm_manager.py

def generate_structured_output(
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    output_schema: dict,
    images: list | None = None,
    force_json_output: bool = True  # <-- PARÁMETRO NUEVO
) -> dict | None:
    """
    (Versión 6.0 - Híbrida)
    Genera una salida JSON. Si 'force_json_output' es True, usa los modos
    de alta fiabilidad de las APIs. Si es False, confía en la instrucción
    del prompt y permite mayor flexibilidad (ej. imágenes en Gemini).
    """
    task_config = next(
        (config for config in MODEL_CONFIG.values() if config.get('primary') == model_name),
        MODEL_CONFIG['default']
    )
    models_to_try = [task_config.get('primary'), task_config.get('fallback')]
    
    instruction_with_schema = f"""
{user_prompt}

Tu salida DEBE ser un único objeto JSON que se valide contra el siguiente esquema.
No incluyas texto, explicaciones o comentarios adicionales.

<output_schema>
{json.dumps(output_schema, indent=2)}
</output_schema>
"""
    
    for current_model in models_to_try:
        if not current_model or current_model not in CLIENTS:
            continue

        print(f"-> 🤖 [Motor Estructurado] Intentando con '{current_model}'...")
        try:
            client_info = CLIENTS[current_model]
            client = client_info['client']
            api_provider = client_info['name']

            # --- LÓGICA MODIFICADA PARA GOOGLE GEMINI ---
            if api_provider == "Google":
                # Se construye el prompt como una lista de partes
                full_prompt_parts = []
                if system_prompt:
                    full_prompt_parts.append(system_prompt)
                full_prompt_parts.append(instruction_with_schema)

                # Se añaden las imágenes si existen
                if images:
                    for img in images:
                        full_prompt_parts.append(img)
                
                # Se decide el modo de operación basado en el nuevo parámetro
                if force_json_output:
                    print("    -> ⚙️  Activando MODO JSON ESTRICTO para Gemini...")
                    if images:
                        print("    -> ⚠️  Advertencia: Las imágenes serán ignoradas en modo JSON estricto.")
                        full_prompt_parts = [p for p in full_prompt_parts if not isinstance(p, PIL.Image.Image)]

                    config = genai.types.GenerationConfig(response_mime_type="application/json")
                    response = client.generate_content(full_prompt_parts, generation_config=config)
                else:
                    print("    -> ✍️  Activando MODO FLEXIBLE (multimodal) para Gemini...")
                    # En modo flexible, se envía el prompt con imágenes sin configuración especial
                    response = client.generate_content(full_prompt_parts)

                json_string = response.text

            # --- LÓGICA PARA ANTHROPIC CLAUDE (no cambia) ---
            elif api_provider == "Anthropic":
                # ... (la lógica existente para Claude se mantiene sin cambios) ...
                print("    -> ⚙️  Aplicando técnica de pre-llenado JSON para Claude...")
                
                user_content = [{"type": "text", "text": instruction_with_schema}]
                
                if images:
                    print(f"    -> 🖼️  Adjuntando {len(images)} imagen(es) para el análisis de Claude...")
                    for img in images:
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG")
                        image_data = buffer.getvalue()
                        encoded_image_data = base64.b64encode(image_data).decode('utf-8')
                        user_content.append({
                            "type": "image",
                            "source": { "type": "base64", "media_type": "image/png", "data": encoded_image_data }
                        })
                
                api_params = {
                    "model": current_model,
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": "{"}
                    ]
                }
                if system_prompt:
                    api_params["system"] = system_prompt
                
                response = client.messages.create(**api_params)
                json_string = "{" + response.content[0].text
            
            # PARSEO Y RETORNO
            if not json_string:
                print("    -> ❌ Error: El modelo no devolvió contenido.")
                continue
            
            cleaned_json_string = _clean_and_extract_json(json_string)
            return json.loads(cleaned_json_string)

        except Exception as e:
            print(f"    -> ❌ CRÍTICO: Fallo al usar el modelo '{current_model}': {e}")
            continue
    
    print("    -> ❌ CRÍTICO: Todos los modelos (primario y de respaldo) han fallado.")
    return None


def extract_entities_from_text(content: str) -> list:
    """
    Usa un LLM para analizar un texto y extraer una lista de entidades clave.
    Devuelve una lista de diccionarios, ej: [{"name": "Codelco", "type": "Empresa"}]
    """
    print("   -> 🤖 Activando Extractor de Entidades...")
    
    # Este prompt es específico para la tarea de extracción.
    system_prompt = """
    Tu única tarea es analizar el texto proporcionado y extraer las entidades clave
    (organizaciones, lugares, conceptos económicos, personas).
    Ignora entidades genéricas y enfócate en las más importantes.
    """
    
    # Le pedimos al modelo que devuelva un JSON con un formato específico.
    output_schema = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nombre de la entidad"},
                        "type": {"type": "string", "description": "Tipo de entidad (ej: Empresa, País, Persona, Concepto)"}
                    },
                    "required": ["name", "type"]
                }
            }
        },
        "required": ["entities"]
    }
    
    # Usamos tu función existente 'generate_structured_output'
    response = generate_structured_output(
        system_prompt=system_prompt,
        user_prompt=f"Extrae las entidades del siguiente texto:\n---\n{content}",
        model_name=MODEL_CONFIG['reasoning']['primary'], # Usamos un modelo rápido para esta tarea
        output_schema=output_schema
    )
    
    if response and "entities" in response:
        entities_found = response["entities"]
        print(f"      -> ✅ Extracción completada. Se encontraron {len(entities_found)} entidades.")
        return entities_found
        
    print("      -> ⚠️  El extractor no encontró entidades válidas.")
    return []
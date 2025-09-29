# quantex/core/web_tools.py (Versión Completa y Final)

import os
import requests
import json
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Importar configuración centralizada
from quantex.config import Config

# quantex/core/web_tools.py

# ... (otras importaciones)
import pprint # <-- Añade esta importación para ver el JSON de forma ordenada

def get_firecrawl_scrape(url: str, timeout_seconds: int = 60) -> dict:
    """
    (Versión 5.0 - Alineada con Documentación Oficial)
    Usa 'requests' para llamar a la API de Firecrawl con el cuerpo (body)
    del JSON en el formato oficial correcto.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("    -> ❌ ERROR: La clave de API de Firecrawl (FIRECRAWL_API_KEY) no está definida.")
        return {}

    # ✅ SEGURO: Obtener URL desde configuración
    firecrawl_api_url = Config.get_firecrawl_url()
    
    # --- El Payload Correcto (según la documentación) ---
    payload = {
        'url': url,
        'pageOptions': {
            'timeout': timeout_seconds * 1000
        }
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    print(f"    -> 🔥 Realizando scrapeo profundo de: {url}")
    
    try:
        response = requests.post(firecrawl_api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        scraped_data = response.json()
        
        return {
            "html": scraped_data.get('data', {}).get('html', ''),
            "markdown": scraped_data.get('data', {}).get('markdown', '')
        }

    except requests.exceptions.HTTPError as e:
        print(f"    -> ❌ Error HTTP en la llamada a Firecrawl (Código: {e.response.status_code})")
        print(f"    ->    Detalle del error: {e.response.text}")
        return {}
    except Exception as e:
        print(f"    -> ❌ Ocurrió un error inesperado durante el scrapeo: {e}")
        return {}
    

def get_firecrawl_scrape_for_tables(url: str, timeout_seconds: int = 60) -> dict:
    """
    (NUEVA FUNCIÓN)
    Usa Firecrawl para scrapear una URL, solicitando explícitamente el HTML
    necesario para la extracción de tablas con Pandas.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("    -> ❌ ERROR: La clave de API de Firecrawl (FIRECRAWL_API_KEY) no está definida.")
        return {}

    # ✅ SEGURO: Obtener URL desde configuración
    firecrawl_api_url = Config.get_firecrawl_url()
    
    # El payload ahora pide explícitamente el HTML
    payload = {
        'url': url,
        'pageOptions': {
            'timeout': timeout_seconds * 1000,
            'includeHtml': True 
        }
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    print(f"    -> 🔥 Realizando scrapeo profundo para tablas en: {url}")
    
    try:
        response = requests.post(firecrawl_api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        scraped_data = response.json()
        
        # Devolvemos solo el HTML, que es lo que necesita el cliente de la bolsa
        return { "html": scraped_data.get('data', {}).get('html', '') }

    except requests.exceptions.HTTPError as e:
        print(f"    -> ❌ Error HTTP en la llamada a Firecrawl (Código: {e.response.status_code})")
        print(f"    ->    Detalle del error: {e.response.text}")
        return {}
    except Exception as e:
        print(f"    -> ❌ Ocurrió un error inesperado durante el scrapeo: {e}")
        return {}    

# ... (el resto de las funciones en web_tools.py se mantienen igual) ...
    
def web_search(query: str) -> str:
    """
    Realiza una búsqueda web utilizando la API de Serper y devuelve los resultados.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: La clave de API de Serper (SERPER_API_KEY) no está configurada en el entorno."

    # ✅ SEGURO: Obtener URL desde configuración
    url = Config.get_serper_url()
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        results = response.json()
        return results
    
    except requests.exceptions.RequestException as e:
        return f"Error en la conexión con la API de búsqueda: {e}"
    except Exception as e:
        return f"Error al procesar la búsqueda: {e}"
    
def get_perplexity_synthesis(
    question: str,
    params: dict | None = None,
    return_full: bool = False
) -> str | dict:
    """
    Envía una pregunta a la API de Perplexity.

    Compatibilidad hacia atrás:
    - Por defecto devuelve solo el texto (string) como antes.
    - Si return_full=True, devuelve el JSON relevante con citas y metadatos.
    - 'params' permite configurar modelo y parámetros avanzados de búsqueda.
    """
    print(f"  -> ❔ Enviando pregunta a Perplexity: '{question}'")
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return "Error: PERPLEXITY_API_KEY no encontrada en el archivo .env"

    # ✅ SEGURO: Obtener URL desde configuración
    url = Config.get_perplexity_url()

    # Parámetros opcionales
    params = params or {}
    model_from_env = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
    model_name = params.get("model", model_from_env)

    payload: dict = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ]
    }

    # Controles de lenguaje (usar defaults conservadores)
    if "temperature" in params:
        payload["temperature"] = params["temperature"]
    if "top_p" in params:
        payload["top_p"] = params["top_p"]
    if "max_tokens" in params:
        payload["max_tokens"] = params["max_tokens"]

    # Controles de búsqueda y resultados
    if params.get("return_citations", True):
        payload["return_citations"] = True
    if "return_related_questions" in params:
        payload["return_related_questions"] = params["return_related_questions"]
    if "search_domain_filter" in params:
        payload["search_domain_filter"] = params["search_domain_filter"]
    if "search_recency_days" in params:
        payload["search_recency_days"] = params["search_recency_days"]
    if "top_k" in params:
        payload["top_k"] = params["top_k"]
    if "web_search_options" in params:
        payload["web_search_options"] = params["web_search_options"]
    if "response_format" in params:
        payload["response_format"] = params["response_format"]
    if "stream" in params:
        payload["stream"] = params["stream"]

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        # Estructura típica compat OpenAI: choices[0].message.content
        text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        print("  -> ✅ Síntesis recibida de Perplexity.")

        if return_full:
            # Exponer campos útiles recomendados por la guía
            return {
                "text": text,
                "citations": data.get("citations") or data.get("search_results"),
                "related_questions": data.get("related_questions"),
                "raw": data
            }
        return text

    except requests.exceptions.RequestException as e:
        print(f"  -> ❌ Error de conexión con la API de Perplexity: {e}")
        return f"Error de conexión con Perplexity: {e}"
    except Exception as e:
        print(f"  -> ❌ Error procesando la respuesta de Perplexity: {e}")
        return f"Error al procesar la respuesta de Perplexity: {e}"
    
 
# quantex/core/agent_tools.py (Versión Definitiva y Autosuficiente)

import os
import sys
import json
import pytz
import pandas as pd
import math
import re
import numbers
import dpath.util
import requests
import demjson3
import time
import uuid
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone


 

# --- INICIO DE LA CORRECCIÓN ---
# 1. Se define la ruta raíz del proyecto de forma robusta y local
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core import llm_manager
from quantex.core.tool_registry import registry
from quantex.core.tools.technical_tools import fetch_stock_data
from quantex.core.web_tools import get_perplexity_synthesis
from quantex.core.ai_services import ai_services


def get_file_content(file_path: str) -> str:
    """(Versión Robusta) Lee el contenido de un archivo."""
    normalized_path = os.path.normpath(file_path)
    full_path = os.path.join(PROJECT_ROOT, normalized_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ get_file_content: No se encontró el archivo en {full_path}")
        return ""

# --- HERRAMIENTAS DE BAJO NIVEL (sin cambios) ---

def get_market_data(series_name: str, source: str, date_filter: dict = None) -> str:
    """
    (Versión Corregida)
    Actúa como un despachador: obtiene datos de EODHD o Supabase según la 'source'.
    """
    print(f"🛠️ [Herramienta Mercado] para Serie: '{series_name}' desde Fuente: '{source}'")

    if source == 'eodhd':
        try:
            api_key = os.getenv("EODHD_API_KEY")
            if not api_key:
                raise ValueError("EODHD_API_KEY no encontrada en el entorno.")
            
            period_days = date_filter.get('last_n_days', 365) if date_filter else 365
            
            # Llama a la herramienta especializada para EODHD, que devuelve OHLC
            df = fetch_stock_data(ticker=series_name, api_key=api_key, period_days=period_days)
            
            if df is not None and not df.empty:
                df.index.name = 'timestamp'
                df_reset = df.reset_index()
                return df_reset.to_json(orient='records', date_format='iso')
            else:
                return json.dumps([])
        except Exception as e:
            print(f"  -> ❌ Error en get_market_data (modo EODHD): {e}")
            return json.dumps({"error": str(e)})

    # Si la fuente es 'supabase' o cualquier otra, usa la lógica original
    else: # default to supabase
        if not db.supabase:
            return json.dumps({"error": "Cliente de Supabase no inicializado."})
        try:
            series_info_res = db.supabase.table('series_definitions').select('id').eq('series_name', series_name).single().execute()
            if not series_info_res.data:
                print(f"  -> ⚠️  No se encontró la definición para la serie '{series_name}' en Supabase.")
                return json.dumps([])
            
            series_id = series_info_res.data['id']
            query = db.supabase.table('time_series_data').select('timestamp, value').eq('series_id', series_id)
            
            if date_filter and 'last_n_days' in date_filter:
                days_ago = datetime.now(pytz.utc) - timedelta(days=date_filter['last_n_days'])
                query = query.gte('timestamp', days_ago.isoformat())
                
            data_res = query.order('timestamp', desc=True).execute()
            return json.dumps(data_res.data if data_res.data else [], default=str)
        except Exception as e:
            print(f"  -> ❌ Error en get_market_data (modo Supabase): {e}")
            return json.dumps({"error": str(e)})

  
def get_expert_opinion(topic: str) -> str:
    print(f"🛠️ [Herramienta Experto] Buscando opinión para: '{topic}'")
    if not db.supabase:
        return "Error: Cliente de Supabase no inicializado."
    try:
        response = db.supabase.table('expert_context').select('current_view').ilike('expert_name', f'%{topic}%').order('updated_at', desc=True).limit(1).single().execute()
        if response.data:
            return response.data['current_view']
        return f"No se encontró contexto de experto para el tema '{topic}'."
    except Exception as e:
        print(f"  -> ❌ Error en la herramienta get_expert_opinion: {e}")
        return f"Error técnico al buscar opinión de experto: {e}"
    

# --- HERRAMIENTAS DE ALTO NIVEL ---

@registry.register(name="get_last_value")
def get_last_value(series_data: list, value_key: str = 'close', date_key: str = 'date', **kwargs) -> dict | None:
    """
    (Versión Corregida y Flexible v2.0)
    Encuentra el último valor en una serie de tiempo, usando 'date' y 'close'
    como claves por defecto para alinearse con el data_fetcher.
    Maneja automáticamente series enriquecidas con metadatos.
    """
    if not series_data:
        return None
    
    # Extraer datos numéricos de series enriquecidas
    if isinstance(series_data, dict) and 'data' in series_data:
        print(f"    -> 🔍 Detectada serie enriquecida con metadatos en get_last_value. Extrayendo datos numéricos...")
        numeric_data = series_data['data']
    else:
        numeric_data = series_data
    
    try:
        data_copy = numeric_data[:]
        
        # Usamos la clave de fecha correcta ('date') para filtrar y ordenar
        valid_data = [d for d in data_copy if d.get(date_key)]
        if not valid_data:
            print(f"    -> ⚠️  get_last_value: No se encontraron fechas válidas con la clave '{date_key}'. Usando datos originales.")
            valid_data = data_copy

        # Ordenamos la lista de forma descendente para que el más reciente quede primero
        valid_data.sort(key=lambda x: x.get(date_key, ''), reverse=True)
        
        last_entry = valid_data[0]

    except (TypeError, KeyError) as e:
        print(f"    -> ❌ Error al ordenar datos en get_last_value: {e}. Usando fallback.")
        last_entry = numeric_data[-1]

    # Usamos la clave de valor correcta ('close')
    return {"value": last_entry.get(value_key)}

def format_number_spanish(value, decimals: int = 2):
    """
    Toma un número y lo formatea a un string con el formato español,
    permitiendo un número variable de decimales.
    - Usa '.' para miles.
    - Usa ',' para decimales.
    """
    # 1. Maneja casos donde el valor no es un número
    if not isinstance(value, numbers.Number):
        return value

    # 2. Formatea el número a un string con N decimales, usando placeholders
    #    Ej: 12345.67 -> "12,345.67"
    formatted_string = f"{value:,.{decimals}f}"

    # 3. Hacemos el reemplazo de separadores
    # Primero, reemplazamos la coma de miles por un punto.
    # Ej: "12,345.67" -> "12.345.67"
    # Luego, reemplazamos el punto decimal por una coma.
    # Ej: "12.345.67" -> "12.345,67"
    
    # Esto se puede hacer en un solo paso con un truco
    if decimals > 0:
        # Separa la parte entera de la decimal
        parts = formatted_string.rsplit('.', 1)
        # Formatea la parte entera y luego une con la parte decimal
        integer_part_formatted = parts[0].replace(',', '.')
        return f"{integer_part_formatted},{parts[1]}"
    else:
        # Si no hay decimales, solo formatea la parte entera
        return formatted_string.replace(',', '.')

def get_nested_value(data_dict, key_path):
    keys = key_path.split('.')
    value = data_dict
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value    

def get_formatted_report_date() -> str:
    """Obtiene la fecha actual en Santiago y la formatea para los informes."""
    santiago_tz = pytz.timezone('America/Santiago')
    fecha_actual = datetime.now(santiago_tz)
    # El locale ya está configurado al inicio del script
    return fecha_actual.strftime("%d de %B de %Y") 

def format_dataframe_to_html_table(headers: list, rows_data: list) -> str:
    """
    Toma una lista de encabezados y una lista de filas (diccionarios) y
    lo convierte en una tabla HTML usando Pandas.
    """
    try:
        if not rows_data:
            return ""
        df = pd.DataFrame(rows_data, columns=headers, dtype=str)
        html_table = df.to_html(classes="data-table", border=0, index=False, escape=False)
        return html_table
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo formatear la tabla DataFrame a HTML. Error: {e}")
        return "" 
    

@registry.register(name="generate_table")
def generate_table(evidence_workspace: dict, params: dict) -> dict | None:
    """
    (VERSIÓN CON FORMATO MEJORADO)
    Genera una tabla HTML, centrando las columnas numéricas.
    """
    title = params.get("title", "Tabla de Datos")
    headers = params.get("headers", [])
    rows_def = params.get("rows", [])

    print(f"  -> 🛠️  Generando tabla robusta: '{title}'")

    if not headers or not rows_def:
        return None

    html = f'<h3 style="margin-top: 20px; color: #E0E0E0;">{title}</h3>'
    html += '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
    
    # Cabecera
    html += '<thead><tr style="text-align: left; border-bottom: 2px solid #4A5568;">'
    for header in headers:
        # --- AJUSTE DE CENTRADO EN CABECERA ---
        # Si el header no es 'Bolsa' o 'Mercado', lo centramos.
        style = 'text-align: center;' if header.lower() not in ['bolsa', 'mercado'] else ''
        html += f'<th style="padding: 10px; color: #A0AEC0; font-weight: bold; {style}">{header}</th>'
    html += '</tr></thead>'
    
    # Cuerpo
    html += '<tbody>'
    for i, row_def in enumerate(rows_def):
        bg_color = "transparent" if i % 2 == 0 else "rgba(255, 255, 255, 0.03)"
        html += f'<tr style="border-bottom: 1px solid #2D3748; background-color: {bg_color};">'
        
        for header in headers:
            value_path = row_def.get(header)
            resolved_value = 'N/A'
            if value_path:
                if '.' in value_path:
                    try:
                        found_value = dpath.util.get(evidence_workspace, value_path, separator='.')
                        try:
                            numeric_value = float(found_value)
                            decimals = 0 if "Inventario" in title else 2
                            resolved_value = format_number_spanish(numeric_value, decimals=decimals)
                        except (ValueError, TypeError):
                            resolved_value = found_value
                    except KeyError:
                        resolved_value = 'N/A'
                else:
                    resolved_value = value_path
            
            # --- AJUSTE DE CENTRADO EN CELDAS ---
            # Aplicamos el mismo estilo que en la cabecera.
            style = 'text-align: center;' if header.lower() not in ['bolsa', 'mercado'] else ''
            html += f'<td style="padding: 10px; color: #E2E8F0; {style}">{resolved_value}</td>'
        html += '</tr>'

    html += '</tbody></table>'

    return {
        "title": title,
        "html": html,
        "type": "table"
    }

def summarize_conversation_history(history: list, max_turns: int = 3) -> str:
    """
    Toma el historial de una conversación y usa un LLM para resumir
    los últimos turnos, enfocándose en el contexto relevante para el Router.
    """
    if not history:
        return "No hay historial de conversación."

    # Seleccionamos solo los últimos 'max_turns' para resumir
    recent_turns = history[-max_turns:]
    
    transcript = ""
    for turn in recent_turns:
        user_msg = turn.get('user_message', '')
        
        # Buscamos el contenido de texto en la respuesta de Quantex
        quantex_msg = "Respuesta no textual (ej. un informe o gráfico)."
        response_blocks = turn.get('quantex_response', {}).get('response_blocks', [])
        for block in response_blocks:
            if block.get('type') in ['text', 'markdown']:
                quantex_msg = block.get('content', '')
                break
        
        transcript += f"Usuario: {user_msg}\nQuantex: {quantex_msg}\n\n"

    if not transcript.strip():
        return "No hay historial de conversación reciente."

    # Llamamos a un LLM para que resuma la transcripción
    from quantex.core import llm_manager
    summary_prompt = f"Resume de forma muy concisa el siguiente intercambio. El objetivo es darle contexto al agente principal sobre lo que se acaba de discutir. Extrae la intención principal y cualquier entidad o tópico clave (ej. 'el usuario acaba de generar el informe del cobre y ahora pide editarlo').\n\n### TRANSCRIPCIÓN RECIENTE ###\n{transcript}"
    
    summary = llm_manager.generate_completion(
        system_prompt=summary_prompt,
        user_prompt="Genera el resumen en una o dos frases.",
        task_complexity="simple" # Usamos un modelo rápido para esta tarea
    )
    return summary     

def _clean_html_for_llm(html_content: str) -> str:
    """
    Toma un contenido HTML, extrae el texto de etiquetas clave (títulos, párrafos, listas)
    y lo devuelve como un texto limpio y simplificado, ideal para un LLM.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Encuentra todas las etiquetas que probablemente contienen texto importante
        tags = soup.find_all(['h1', 'h2', 'h3', 'p', 'li'])
        
        # Extrae el texto limpio de cada etiqueta y lo une con saltos de línea
        clean_texts = [tag.get_text(strip=True) for tag in tags]
        
        cleaned_text = "\n".join(clean_texts)
        print(f"    -> ✨ HTML limpiado. Reducido de {len(html_content)} a {len(cleaned_text)} caracteres.")
        return cleaned_text
    except Exception as e:
        print(f"  -> ⚠️  Advertencia: Falló la limpieza de HTML con BeautifulSoup. Devolviendo texto vacío. Error: {e}")
        return "" # Devolvemos vacío para no pasar HTML crudo si falla
    
def _extract_json_from_response(text: str) -> dict | None:
    """
    Intenta encontrar y parsear un bloque de JSON dentro de un string de texto.
    Ideal para respuestas de LLMs que no son JSON puros.
    """
    try:
        # Busca el primer '{' y el último '}'
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_str = text[start_index:end_index+1]
            return demjson3.decode(json_str)
        return None
    except demjson3.JSONDecodeError:
        return None 
    

@registry.register(name="supabase")
def supabase_data_tool(workspace: dict, params: dict):
    """Herramienta alias para cargar datos desde Supabase."""
    series_name = params.get("name")
    data_json = get_market_data(series_name=series_name, source="supabase")
    data = json.loads(data_json)
    if data and (not isinstance(data, dict) or not data.get("error")):
        workspace[f"data_{series_name}"] = data

@registry.register(name="eodhd")
def eodhd_data_tool(workspace: dict, params: dict):
    """Herramienta alias para cargar datos desde EODHD."""
    series_name = params.get("name")
    data_json = get_market_data(series_name=series_name, source="eodhd")
    data = json.loads(data_json)
    if data and (not isinstance(data, dict) or not data.get("error")):
        workspace[f"data_{series_name}"] = data    


# FUNCIÓN ELIMINADA: distill_and_classify_text()
# Esta función ha sido migrada al nuevo motor centralizado:
# quantex.core.knowledge_graph.ai_processors.AIMetadataProcessor.distill_and_classify_text()

def process_and_store_knowledge(raw_text: str, source_context: dict):
    """
    ⚠️  WRAPPER DE COMPATIBILIDAD - REDIRIGE AL NUEVO MOTOR ⚠️
    
    Esta función mantiene compatibilidad con código existente pero redirige
    al nuevo motor centralizado de ingesta.
    """
    try:
        from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine
        print("  -> 🔄 Redirigiendo al nuevo Motor de Ingesta Centralizado...")
        engine = KnowledgeGraphIngestionEngine()
        result = engine.ingest_document(raw_text, source_context)
        
        if result.get("success"):
            print(f"  -> ✅ {result.get('nodes_created', 0)} nodo(s) creado(s) con conexiones semánticas.")
        else:
            print(f"  -> ❌ Error en ingesta: {result.get('reason', 'Desconocido')}")
            
        return result
    except Exception as e:
        print(f"  -> ❌ Error crítico en wrapper: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def process_and_store_knowledge_DEPRECATED(raw_text: str, source_context: dict):
    """
    ⚠️  FUNCIÓN DEPRECADA - NO USAR ⚠️
    
    Esta función ha sido migrada al nuevo motor centralizado:
    quantex.core.knowledge_graph.ingestion_engine.KnowledgeGraphIngestionEngine.ingest_document()
    
    (Línea de Ensamblaje v3.1 - Grafo Unificado Completo)
    Toma texto en bruto, lo destila y guarda los resultados y TODOS sus metadatos
    como nodos y ejes en el grafo de conocimiento unificado.
    """
    print(f"--- 🏭 Iniciando Línea de Ensamblaje (Modo Grafo) para fuente: {source_context.get('source')} ---")
    try:
        atomic_nodes = distill_and_classify_text(raw_text)
        if not atomic_nodes:
            print("  -> 🔴 El procesador no encontró nodos para guardar.")
            return

        print(f"  -> 💾 Procesando y guardando {len(atomic_nodes)} nodo(s) y sus conexiones...")
        for node_obj in atomic_nodes:
            node_content = node_obj.get("content")
            if not node_content: continue

            # 1. Crear el Nodo de tipo 'Documento'
            document_node_id = str(uuid.uuid4())
            document_title = node_obj.get('title') or f"Artículo de {source_context.get('source', 'desconocido')}"
            document_label = f"{document_title} - {document_node_id[:8]}"

            # --- INICIO DE LA CORRECCIÓN: Se añaden TODOS los metadatos ---
            word_count = len(node_content.split())
            reading_time_minutes = math.ceil(word_count / 200)

            document_properties = {
                "source": source_context.get('source'),
                "source_type": source_context.get('source_type'),
                "topic": source_context.get('topic'),
                "original_url": source_context.get('original_url'),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # Metadatos enriquecidos por la IA
                "ai_summary": node_obj.get('ai_summary'),
                "categories": node_obj.get('categories'),
                # Datos duros calculados
                "word_count": word_count,
                "reading_time_minutes": reading_time_minutes
            }
            # --- FIN DE LA CORRECCIÓN ---
            
            db.supabase.table('nodes').insert({
                "id": document_node_id,
                "type": "Documento",
                "label": document_label,
                "content": node_content,
                "properties": document_properties
            }).execute()
            print(f"    -> ✅ Nodo 'Documento' creado con ID: {document_node_id[:8]}...")

            # 2. Guardar en Pinecone (sin cambios)
            vector = ai_services.embedding_model.encode(node_content).tolist()
            metadata_for_pinecone = {
                "source": source_context.get("source", ""),
                "source_type": source_context.get("source_type", ""),
                "topic": source_context.get("topic", ""),
                "original_url": source_context.get("original_url", ""),
                "categories": node_obj.get("categories", []), # <-- AÑADIDO
                "key_entities": node_obj.get("key_entities", []), # <-- AÑADIDO
                "text_snippet": node_content[:500]
            }
            ai_services.pinecone_index.upsert(vectors=[{
                "id": document_node_id, "values": vector, "metadata": metadata_for_pinecone
            }])
            print(f"    -> 🌲 Nodo indexado en Pinecone.")

            # 3. Crear Nodos de 'Entidad' y sus 'Ejes' de conexión (sin cambios)
            entities = node_obj.get("key_entities", [])
            if entities:
                entity_nodes_to_upsert = [{"type": "Entidad", "label": entity} for entity in entities]
                db.supabase.table('nodes').upsert(entity_nodes_to_upsert, on_conflict='label,type').execute()
                
                entity_nodes_in_db = db.supabase.table('nodes').select('id, label').eq('type', 'Entidad').in_('label', entities).execute().data
                entity_map = {node['label']: node['id'] for node in entity_nodes_in_db}

                edges_to_insert = []
                for entity_name in entities:
                    if entity_name in entity_map:
                        edges_to_insert.append({
                            "source_id": document_node_id,
                            "target_id": entity_map[entity_name],
                            "relationship_type": "menciona"
                        })
                if edges_to_insert:
                    db.supabase.table('edges').upsert(edges_to_insert).execute()
                    print(f"    -> 🔗 {len(edges_to_insert)} conexiones con entidades creadas.")
            
            time.sleep(1)

    except Exception as e:
        print(f"--- ❌ Error Crítico en la Línea de Ensamblaje: {e}")
        import traceback
        traceback.print_exc()


@registry.register(name="create_standardized_series")
def create_standardized_series(workspace: dict, params: dict):
    """
    (Clonador Estandarizado v1.0 - No Destructivo)
    Lee una serie de tiempo original, la estandariza a un formato ohlc
    consistente y la guarda en una nueva clave en el workspace,
    dejando la serie original intacta.
    """
    source_key = params.get("source_key")
    output_key = params.get("output_key")

    if not all([source_key, output_key]):
        print("  -> ⚠️  [Clonador] Faltan 'source_key' u 'output_key'. Omitiendo.")
        return
    if source_key not in workspace:
        print(f"  -> ⚠️  [Clonador] No se encontró la serie original '{source_key}'.")
        return

    print(f"  -> 🤖 [Clonador] Creando copia estandarizada '{output_key}' desde '{source_key}'...")
    
    original_data = workspace[source_key]
    if not original_data:
        workspace[output_key] = []
        return

    first_record = original_data[0]
    if not isinstance(first_record, dict):
        workspace[output_key] = original_data
        return

    normalized_data = []
    # Caso 1: Viene con 'close' (minúscula) - ya es estándar
    if 'close' in first_record:
        normalized_data = original_data
        print(f"    -> ✅ La serie original ya es estándar. Copiando directamente.")
    
    # Caso 2: Viene con 'Close' (mayúscula) - necesita estandarización de claves
    elif 'Close' in first_record:
        for row in original_data:
            normalized_data.append({key.lower(): value for key, value in row.items()})
        print(f"    -> ✅ La serie ha sido estandarizada desde formato 'OHLC' a 'ohlc'.")
    
    # Caso 3: Viene con 'value' - necesita transformación a ohlc
    elif 'value' in first_record:
        for row in original_data:
            normalized_data.append({
                'timestamp': row.get('timestamp'), 'open': row.get('value'),
                'high': row.get('value'), 'low': row.get('value'),
                'close': row.get('value'), 'volume': 0
            })
        print(f"    -> ✅ La serie ha sido estandarizada desde formato 'value' a 'ohlc'.")

    workspace[output_key] = normalized_data

def _filter_for_novel_learnings(new_learnings: list[str], existing_learnings: list[str], similarity_threshold: float = 0.95) -> list[str]:
    """
    Compara una lista de aprendizajes nuevos contra una de existentes usando
    embeddings y similitud coseno para filtrar los que son semánticamente redundantes.
    """
    from quantex.core.ai_services import ai_services # Importación local para evitar errores circulares

    print(f"  -> 🔎 [Filtro de Novedad] Comparando {len(new_learnings)} aprendizajes nuevos contra {len(existing_learnings)} existentes...")

    # Si no hay aprendizajes existentes, todos los nuevos son novedosos por definición.
    if not existing_learnings or not new_learnings:
        print("    -> ✅ No hay base para comparar. Todos los nuevos aprendizajes son aceptados.")
        return new_learnings

    try:
        # 1. Convertir todo el texto a vectores numéricos (embeddings)
        new_vectors = np.array(ai_services.embedding_model.encode(new_learnings))
        existing_vectors = np.array(ai_services.embedding_model.encode(existing_learnings))

        # 2. Calcular la matriz de similitud coseno
        # Esto compara cada vector nuevo con todos los vectores existentes de una sola vez.
        similarity_matrix = np.dot(new_vectors, existing_vectors.T) / \
                          (np.linalg.norm(new_vectors, axis=1, keepdims=True) * np.linalg.norm(existing_vectors, axis=1, keepdims=True).T)

        # 3. Encontrar la máxima similitud para cada aprendizaje nuevo
        max_similarity_scores = np.max(similarity_matrix, axis=1)

        # 4. Filtrar basándose en el umbral
        novel_learnings_to_keep = []
        for i, score in enumerate(max_similarity_scores):
            if score < similarity_threshold:
                novel_learnings_to_keep.append(new_learnings[i])
                print(f"    -> ✅ ACEPTADO (Score: {score:.2f}): '{new_learnings[i][:60]}...'")
            else:
                print(f"    -> 🟡 RECHAZADO por redundancia (Score: {score:.2f}): '{new_learnings[i][:60]}...'")
        
        print(f"  -> ✅ Filtro completado. Se aceptaron {len(novel_learnings_to_keep)} de {len(new_learnings)} aprendizajes nuevos.")
        return novel_learnings_to_keep

    except Exception as e:
        print(f"    -> ❌ Error durante el filtrado semántico: {e}. Omitiendo filtro por seguridad.")
        return new_learnings # En caso de error, devolvemos todos los nuevos para no perder información.    
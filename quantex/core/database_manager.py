# quantex/core/database_manager.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json
import uuid
import pytz
import numpy as np
import yaml
from quantex.core.ai_services import ai_services

# --- Conexión a Supabase ---p
try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    print(f"Cliente de Supabase inicializado en database_manager.")
except Exception as e:
    print(f"ERROR al inicializar el cliente de Supabase: {e}")
    supabase = None

def unified_query(table_name: str, select_columns: str = "*", filters: dict = None, semantic_query: str = None, order_by: tuple = None, limit: int = 100) -> list:
    """
    (Versión Final - Híbrida y Robusta v2.0 - Case-Insensitive)
    La única función de consulta para Quantex. Combina el filtrado de precisión de Supabase
    con la búsqueda por significado de Pinecone, siendo insensible a mayúsculas/minúsculas.
    """
    print(f"🔎 Ejecutando Consulta Unificada vFINAL en tabla '{table_name}'...")
    try:
        id_list_from_filters = None
        has_filters = filters and any(filters.values())

        # --- ETAPA 1: FILTRADO DE PRECISIÓN EN SUPABASE (SI APLICA) ---
        if has_filters:
            print(f"   -> Aplicando filtros de metadatos: {filters}")
            filter_query_chain = supabase.table(table_name).select('id')
            active_filters = {k: v for k, v in filters.items() if v is not None}
            
            if 'days_ago' in active_filters:
                from datetime import datetime, timedelta, timezone
                days = active_filters.pop('days_ago')
                time_filter = datetime.now(timezone.utc) - timedelta(days=days)
                filter_query_chain = filter_query_chain.gte('timestamp', time_filter.isoformat())

            for column, value in active_filters.items():

                if isinstance(value, str):
                    print(f"      -> Aplicando filtro FLEXIBLE (Case-Insensitive): {column} ILIKE '{value}'")
                    filter_query_chain = filter_query_chain.ilike(column, value)
                else:
                    print(f"      -> Aplicando filtro EXACTO: {column} = '{value}'")
                    filter_query_chain = filter_query_chain.eq(column, value)

            
            filter_response = filter_query_chain.execute()
            if filter_response.data:
                id_list_from_filters = [item['id'] for item in filter_response.data]
                if not id_list_from_filters:
                    print("  -> 🟡 Los filtros en Supabase no encontraron resultados. Consulta finalizada.")
                    return []
            else:
                print("  -> 🟡 Los filtros en Supabase no encontraron resultados. Consulta finalizada.")
                return []

        # --- ETAPA 2: BÚSQUEDA SEMÁNTICA EN PINECONE (SI APLICA) ---
        if semantic_query:
            print(f"   -> Ejecutando búsqueda semántica para: '{semantic_query}'")
            vector = ai_services.embedding_model.encode(semantic_query).tolist()
            
            pinecone_pre_filter = {}
            if id_list_from_filters is not None:
                pinecone_pre_filter = {"id": {"$in": id_list_from_filters}}
            
            search_response = ai_services.pinecone_index.query(
                vector=vector, 
                filter=pinecone_pre_filter, 
                top_k=limit, 
                include_metadata=False
            )
            final_ids = [match['id'] for match in search_response.get('matches', [])]
        else:
            final_ids = id_list_from_filters

        # --- ETAPA 3: RECUPERACIÓN DEL CONTENIDO FINAL ---
        if not final_ids:
            print("  -> 🟡 La consulta no arrojó IDs finales.")
            return []

        print(f"   -> Recuperando contenido completo para {len(final_ids)} artículo(s) desde Supabase...")
        final_query_chain = supabase.table(table_name).select(select_columns).in_('id', final_ids)
        
        if order_by and isinstance(order_by, tuple) and len(order_by) == 2:
            final_query_chain = final_query_chain.order(order_by[0], desc=order_by[1])
        
        final_response = final_query_chain.execute()

        return final_response.data if final_response.data else []
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []
    


def get_filter_options() -> dict:
    """
    Crea un "mapa" dinámico de los filtros disponibles en la base de datos.
    """
    print("🗺️  Creando mapa dinámico de opciones de filtro...")
    try:
        # Usamos vistas de la base de datos para obtener los valores únicos de forma eficiente
        sources = supabase.rpc('get_distinct_sources').execute().data
        topics = supabase.rpc('get_distinct_topics').execute().data

        options = {
            "valid_sources": [item['source'] for item in sources if item.get('source')],
            "valid_topics": [item['topic'] for item in topics if item.get('topic')]
        }
        print("    -> ✅ Mapa creado exitosamente.")
        return options
    except Exception as e:
        print(f"    -> ❌ Error creando el mapa de filtros: {e}")
        return {"valid_sources": [], "valid_topics": []}    




# ==============================================================================
# --- NUEVAS FUNCIONES PARA LA ARQUITECTURA DE MATERIA PRIMA ---
# ==============================================================================

def get_latest_materia_prima_dossier(topic: str) -> dict | None:
    """
    (Versión Simplificada)
    Busca el último dossier de 'materia prima' para un tópico, sin restricciones de tiempo.
    """
    print(f"  -> 🛠️ [DB] Buscando el ÚLTIMO 'materia prima' para '{topic}'...")
    try:
        response = supabase.table('materia_prima_dossiers') \
            .select('*') \
            .eq('topic', topic) \
            .order('created_at', desc=True) \
            .limit(1) \
            .maybe_single() \
            .execute()

        if response.data:
            print("    -> ✅ 'Materia Prima' encontrada.")
            return response.data
        else:
            print("    -> ⚠️ No se encontró 'Materia Prima' para este tópico.")
            return None
            
    except Exception as e:
        print(f"    -> ❌ Error en get_latest_materia_prima_dossier: {e}")
        return None


def create_task_dossier(user_request: str, parent_artifact_id: str = None, target_artifact_type: str = None, initial_workspace: list = None) -> dict | None:
    """
    Crea un nuevo dossier de tarea, incluyendo opcionalmente un workspace inicial.
    """
    if not supabase: return None
    try:
        data_to_insert = {
            'user_request': user_request,
            'status': 'abierto',
            'parent_artifact_id': parent_artifact_id,
            'target_artifact_type': target_artifact_type,
            'workspace': json.dumps(initial_workspace or [], default=str)
        }
        # CORRECCIÓN: Se elimina la llamada a .select() que es inválida.
        response = supabase.table('task_dossiers').insert(data_to_insert).execute()
        
        if response.data:
            print(f"✅ Dossier de tarea creado con ID: {response.data[0]['id']}")
            return response.data[0]
        
        # Añadimos un log por si algo sale mal pero no hay excepción
        print(f"⚠️ La creación del dossier no devolvió datos. Respuesta: {response}")
        return None
    except Exception as e:
        print(f"❌ Error al crear dossier de tarea: {e}")
        return None

def get_dossier(dossier_id: str) -> dict | None:
    if not supabase: return None
    try:
        # CORRECCIÓN: Usar .select() y .eq() para buscar por ID
        response = supabase.table('task_dossiers').select('*').eq('id', dossier_id).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"❌ Error al recuperar dossier {dossier_id}: {e}")
        return None

def update_dossier_status(dossier_id: str, new_status: str) -> bool:
    if not supabase: return False
    try:
        supabase.table('task_dossiers').update({'status': new_status}).eq('id', dossier_id).execute()
        print(f"  -> ✅ Estado del dossier {dossier_id} actualizado a '{new_status}'.")
        return True
    except Exception as e:
        print(f"❌ Error al actualizar estado del dossier {dossier_id}: {e}")
        return False

def update_dossier_workspace(dossier_id: str, agent_name: str, findings: dict) -> dict | None:
    if not supabase: return None
    try:
        dossier = get_dossier(dossier_id)
        if not dossier: return None
        workspace_data = dossier.get('workspace', [])
        workspace = json.loads(workspace_data) if isinstance(workspace_data, str) and workspace_data else (workspace_data or [])
        contribution = {"agent_name": agent_name, "timestamp": datetime.now().isoformat(), "findings": findings}
        workspace.append(contribution)
        response = supabase.table('task_dossiers').update({'workspace': json.dumps(workspace, default=str)}).eq('id', dossier_id).execute()
        print(f"  -> ✅ Workspace del dossier {dossier_id} actualizado por {agent_name}.")
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Error al actualizar workspace del dossier {dossier_id}: {e}")
        return None

# La firma de la función ahora incluye 'source_dossier_id'
def insert_generated_artifact(report_keyword: str, artifact_content: str, artifact_type: str, results_packet: dict | None = None, source_dossier_id: str | None = None, ticker: str | None = None) -> dict | None:
    """
    (Versión 3.0 - Final)
    Inserta un artefacto. Si recibe un 'results_packet', lo guarda en la columna 'content_dossier'.
    Es 100% retrocompatible.
    """
    if not supabase: return None
    try:
        data_to_insert = {
            'report_keyword': report_keyword,
            'full_content': artifact_content,
            'artifact_type': artifact_type,
            'source_dossier_id': source_dossier_id,
            'ticker': ticker  # <-- AÑADIMOS LA COLUMNA TICKER
        }
        
        if results_packet:
            data_to_insert['content_dossier'] = results_packet

        response = supabase.table('generated_artifacts').insert(data_to_insert).execute()
        
        if response.data:
            print(f"✅ Artefacto para '{report_keyword}' guardado con ID: {response.data[0]['id']}")
            return response.data[0]
        return None
        
    except Exception as e:
        print(f"❌ Error al insertar artefacto: {e}")
        return None 

def get_artifact_by_id(artifact_id: str) -> dict | None:
    if not supabase: return None
    try:
        print(f"-> Buscando artefacto con ID: {artifact_id}")
        response = supabase.table('generated_artifacts').select('*').eq('id', artifact_id).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"❌ Error al recuperar artefacto {artifact_id}: {e}")
        return None

def get_full_catalog() -> dict:
    if not supabase: return {}
    try:
        tables = ['report_definitions', 'series_definitions', 'news_topics', 'expert_context']
        results = {table: supabase.table(table).select('*').execute().data or [] for table in tables}
        return {
            "reports": results['report_definitions'], "series": results['series_definitions'],
            "news_topics": results['news_topics'], "experts": results['expert_context'],
        }
    except Exception as e:
        print(f"❌ Error al recuperar el catálogo completo: {e}")
        return {}
    
def upload_file_to_storage(bucket_name: str, destination_path: str, file_body: bytes) -> str | None:
    """
    Sube un archivo en formato de bytes a un bucket de Supabase Storage.
    Si el archivo ya existe, lo actualiza. Devuelve la URL pública.
    """
    if not supabase:
        print("❌ Error: Cliente de Supabase no disponible en upload_file_to_storage.")
        return None
    
    try:
        # El valor de 'upsert' debe ser un string "true", no un booleano True.
        file_options = {"content-type": "image/png", "upsert": "true"}

        supabase.storage.from_(bucket_name).upload(
            path=destination_path,
            file=file_body,
            file_options=file_options
        )
        
        response = supabase.storage.from_(bucket_name).get_public_url(destination_path)
        
        # La siguiente línea 'print' ha sido eliminada para evitar duplicados en el log.
        
        return response

    except Exception as e:
        print(f"❌ Error al subir el archivo '{destination_path}' a Supabase Storage: {e}")
        return None
    
   
def get_conversation_history(session_id: str, limit: int = 3) -> list:
    """
    Recupera los últimos N turnos de una conversación para un session_id dado.
    """
    try:
        # Recuperamos los últimos N turnos, ordenados del más reciente al más antiguo
        response = supabase.table('conversation_turns').select('*') \
            .eq('session_id', session_id) \
            .order('turn_index', desc=True) \
            .limit(limit) \
            .execute()

        if not response.data:
            return []

        # Formateamos la salida a una lista de diccionarios simple
        # y la invertimos para que quede en orden cronológico (del más antiguo al más reciente)
        history = []
        for turn in reversed(response.data):
            history.append({"role": "user", "content": turn.get('user_message', '')})
            # El campo 'quantex_response' es un JSON, extraemos solo el texto del chat
            assistant_response_raw = turn.get('quantex_response', {})
            chat_content = "Acción sin respuesta de chat."
            if assistant_response_raw.get('response_blocks'):
                # Buscamos el primer bloque de texto destinado al chat
                for block in assistant_response_raw['response_blocks']:
                    if block.get('display_target') == 'chat' and block.get('type') == 'text':
                        chat_content = block.get('content', chat_content)
                        break
            history.append({"role": "assistant", "content": chat_content})
        
        return history
    except Exception as e:
        print(f"❌ Error al recuperar el historial de la conversación: {e}")
        return []

def upsert_expert_context(expert_name: str, update_data: dict):
    """
    Actualiza o inserta la visión de un experto en la tabla expert_context.
    """
    try:
        print(f"  -> 💾 Realizando UPSERT en 'expert_context' para: {expert_name}")
        
        # El método upsert de Supabase es perfecto para esto.
        # Combina los datos a actualizar con el nombre del experto para la búsqueda.
        data_to_upsert = {
            'expert_name': expert_name,
            **update_data
        }
        
        # 'on_conflict' le dice a Supabase qué columna usar para decidir si actualizar o insertar.
        response = supabase.table('expert_context').upsert(
            data_to_upsert,
            on_conflict='expert_name' 
        ).execute()

        if response.data:
            print(f"    -> ✅ Visión para '{expert_name}' guardada exitosamente.")
            return response.data[0]
        
        # Si no hay error, la operación fue exitosa aunque no devuelva datos.
        print(f"    -> ✅ Operación UPSERT para '{expert_name}' completada.")
        return None

    except Exception as e:
        print(f"  -> ❌ Error durante el UPSERT en expert_context: {e}")
        # import traceback # Descomenta si necesitas un traceback detallado
        # traceback.print_exc()
        return None 

def get_report_definition_by_topic(topic: str) -> dict | None:
    """
    (Versión Híbrida - YAML + Supabase)
    Busca primero en archivos YAML para comite_tecnico_*, luego hace fallback a Supabase.
    """
    try:
        # PASO 1: Buscar en YAML primero (para comite_tecnico_*, fair_value_*, cobre, clp)
        if topic.startswith('comite_tecnico_') or topic.startswith('fair_value_') or topic in ['cobre', 'clp']:
            yaml_definition = _load_yaml_definition(topic)
            if yaml_definition:
                print(f"  -> 📁 [YAML] Cargando definición para '{topic}' desde archivo")
                return yaml_definition
        
        # PASO 2: Fallback a Supabase (para todos los demás)
        print(f"  -> 🗄️ [Supabase] Cargando definición para '{topic}' desde base de datos")
        return _load_supabase_definition(topic)
        
    except Exception as e:
        print(f"  -> 🔉 DB: ❌ Error en get_report_definition_by_topic: {e}")
        return None

def _load_yaml_definition(topic: str) -> dict | None:
    """Carga definición desde archivo YAML con soporte para templates"""
    try:
        # Construir ruta al archivo YAML
        yaml_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'reports', f"{topic}.yaml")
        yaml_path = os.path.abspath(yaml_path)
        
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Si tiene 'extends', procesa el template
            if isinstance(config, dict) and 'extends' in config:
                template_file = config['extends']
                variables = config.get('variables', {})
                
                # Cargar template base
                template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', template_file)
                template_path = os.path.abspath(template_path)
                
                if os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                    
                    # Renderizar template con variables
                    rendered_content = _render_template(template_content, variables)
                    
                    # Convertir a dict
                    definition = yaml.safe_load(rendered_content)
                    print(f"    -> ✅ YAML template renderizado exitosamente desde: {yaml_path}")
                    return definition
                else:
                    print(f"    -> ⚠️ Template no encontrado: {template_path}")
                    return None
            else:
                # YAML normal sin template
                print(f"    -> ✅ YAML cargado exitosamente desde: {yaml_path}")
                return config
        else:
            print(f"    -> ⚠️ Archivo YAML no encontrado: {yaml_path}")
            return None
    except Exception as e:
        print(f"    -> ❌ Error cargando YAML para {topic}: {e}")
        return None

def _render_template(template: str, variables: dict) -> str:
    """Renderiza template con variables usando sintaxis simple"""
    result = template
    
    # Reemplazar variables simples {{variable}}
    for key, value in variables.items():
        if isinstance(value, str) or isinstance(value, int):
            result = result.replace(f'{{{{{key}}}}}', str(value))
    
    # Manejar bloque de tickers
    if 'tickers' in variables:
        tickers = variables['tickers']
        if isinstance(tickers, list):
            ticker_lines = []
            for ticker in tickers:
                ticker_lines.append(f'  - name: "{ticker}"')
            tickers_block = '\n'.join(ticker_lines)
            result = result.replace('{{tickers_block}}', tickers_block)
    
    # Manejar línea condicional de main_ticker_symbol
    if 'main_ticker_symbol' in variables:
        main_ticker = variables['main_ticker_symbol']
        main_ticker_line = f'  main_ticker_symbol: "{main_ticker}"'
        result = result.replace('{{main_ticker_symbol_line}}', main_ticker_line)
    else:
        # Eliminar la línea si no hay main_ticker_symbol
        result = result.replace('{{main_ticker_symbol_line}}', '')
    
    return result

def _load_supabase_definition(topic: str) -> dict | None:
    """Carga definición desde Supabase (lógica original)"""
    try:
        response = supabase.table('report_definitions').select('*').eq('report_keyword', topic).limit(1).execute()
        
        if response.data:
            print(f"    -> ✅ Supabase: Definición encontrada para '{topic}'")
            return response.data[0]
        else:
            print(f"    -> ⚠️ Supabase: No se encontró definición para '{topic}'")
            return None
    except Exception as e:
        print(f"    -> ❌ Error cargando Supabase para {topic}: {e}")
        return None     
        
def promote_draft_to_final(draft_id: str) -> dict | None:
    """
    (Versión Definitiva y Robusta)
    Promueve un borrador a 'final' y devuelve el artefacto COMPLETO actualizado.
    """
    if not supabase: return None
    try:
        draft_artifact = get_artifact_by_id(draft_id)
        if not draft_artifact or 'draft' not in draft_artifact.get('artifact_type', ''):
            print(f" -> ⚠️  El artefacto {draft_id} no es un borrador válido para promover.")
            return draft_artifact

        new_artifact_type = draft_artifact['artifact_type'].replace('_draft', '_final')
        
        # --- INICIO DE LA CORRECCIÓN FINAL ---
        # PASO 1: Ejecutar la actualización. Esta operación no devuelve el objeto completo.
        update_response = supabase.table('generated_artifacts').update({
            'artifact_type': new_artifact_type,
            'created_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', draft_id).execute()
        
        # Comprobamos si la actualización realmente modificó algo.
        if len(update_response.data) == 0:
            raise Exception("La operación de actualización no modificó ninguna fila.")

        # PASO 2: Si la actualización fue exitosa, volvemos a buscar el artefacto
        # para obtener la versión completa y actualizada.
        print(f"    -> ✅ Artefacto {draft_id} promovido a '{new_artifact_type}'. Recuperando versión final...")
        final_artifact = get_artifact_by_id(draft_id)
        
        return final_artifact
        # --- FIN DE LA CORRECCIÓN FINAL ---

    except Exception as e:
        print(f"❌ Error al promover el borrador {draft_id}: {e}")
        return None

def save_learnings_to_knowledge_graph(topic: str, learnings: list):
    """
    (Versión 2.1 - Grafo Unificado con Labels Únicos)
    Toma una lista de aprendizajes y los guarda como Nodos y Ejes
    en el grafo de conocimiento unificado, garantizando labels únicos.
    """
    if not learnings or not topic:
        return

    print(f"  -> ✍️  Guardando {len(learnings)} aprendizaje(s) para el tópico '{topic}' en el Grafo Unificado...")
    try:
        topic_node_upsert = supabase.table('nodes').upsert({
            'type': 'Tópico Principal',
            'label': topic
        }, on_conflict='label,type').execute()
        
        if not topic_node_upsert.data:
            raise Exception("No se pudo obtener o crear el ID del nodo principal del tópico.")
        
        topic_node_id = topic_node_upsert.data[0]['id']

        learnings_to_insert = []
        for learning_text in learnings:
            if isinstance(learning_text, str) and learning_text.strip():
                learnings_to_insert.append({
                    'type': 'Aprendizaje Clave',
                    # --- INICIO DE LA CORRECCIÓN CLAVE ---
                    'label': f"Aprendizaje sobre {topic} - {uuid.uuid4().hex[:8]}", # Añadimos un ID único
                    # --- FIN DE LA CORRECCIÓN CLAVE ---
                    'content': learning_text.strip()
                })
        
        if not learnings_to_insert:
            return

        learning_nodes_res = supabase.table('nodes').insert(learnings_to_insert).execute()
        
        if learning_nodes_res.data:
            edges_to_insert = []
            for new_learning_node in learning_nodes_res.data:
                edges_to_insert.append({
                    'source_id': topic_node_id,
                    'target_id': new_learning_node['id'],
                    'relationship_type': 'generó_aprendizaje'
                })
            
            supabase.table('edges').insert(edges_to_insert).execute()
            print("    -> ✅ Aprendizajes y sus conexiones guardados en el Grafo Unificado.")

    except Exception as e:
        print(f"    -> ❌ Error guardando aprendizajes en el Grafo Unificado: {e}")

def save_briefing_node(topic: str, briefing_content: str) -> str:
    """
    Guarda un Briefing Estratégico como un Nodo de alta prioridad en el grafo.
    """
    print(f"  -> 💾 Guardando 'Briefing Estratégico' para '{topic}' como Nodo...")
    if not supabase: return None
    try:
        node_id = str(uuid.uuid4())
        node_properties = {
            "source": "Human In The Loop",
            "source_type": "Briefing Estratégico",
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = supabase.table('nodes').insert({
            "id": node_id,
            "type": "Briefing",
            "label": f"Briefing Estratégico - {topic} - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "content": briefing_content,
            "properties": node_properties
        }).execute()

        if response.data:
            print(f"    -> ✅ Briefing guardado exitosamente como Nodo con ID: {response.data[0]['id']}")
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"    -> ❌ Error guardando el Briefing como Nodo: {e}")
        return None


def save_conversation_turn(session_id: str, turn_index: int, user_message: str, quantex_response: dict):
    """
    Guarda un turno de la conversación en la base de datos.
    """
    if not supabase:
        return
    try:
        supabase.table('conversation_history').insert({
            "session_id": session_id,
            "turn_index": turn_index,
            "user_message": user_message,
            "quantex_response": quantex_response
        }).execute()
        print("  -> 📝 Turno de conversación guardado en la memoria a largo plazo.")
    except Exception as e:
        print(f"  -> ❌ Error al guardar el turno de conversación: {e}")   

def get_conversation_history(session_id: str, limit: int = 5) -> str:
    """
    Recupera los últimos turnos de una conversación y los formatea como un string.
    """
    if not supabase or not session_id:
        return "No hay historial disponible."
    try:
        response = supabase.table('conversation_history').select('user_message, quantex_response').eq('session_id', session_id).order('turn_index', desc=True).limit(limit).execute()

        if not response.data:
            return "Inicio de la conversación."

        # Formateamos el historial para que sea fácil de leer para el LLM
        history_str = "### Historial Reciente de la Conversación (el más reciente primero):\n"
        for turn in reversed(response.data): # Lo invertimos para que el orden sea cronológico
            user_msg = turn.get('user_message', '')
            # Extraemos el mensaje de chat de la respuesta de Quantex
            quantex_msg = turn.get('quantex_response', {}).get('response_blocks', [{}])[0].get('content', '')
            history_str += f"- Usuario: \"{user_msg}\"\n"
            history_str += f"- Quantex: \"{quantex_msg}\"\n"

        return history_str

    except Exception as e:
        print(f"  -> ❌ Error al recuperar el historial de conversación: {e}")
        return "Error al acceder al historial."   

def get_latest_ticker_report(ticker: str, report_keyword: str = 'comite_tecnico_mercado', artifact_type_suffix: str = '_final') -> dict | None:
    """
    (Nueva función)
    Recupera el último informe individual para un ticker específico.
    """
    print(f"🛠️ [DB Manager] Buscando último informe para ticker '{ticker}' en '{report_keyword}'...")
    if not supabase: return None
    try:
        artifact_type = f'report_{report_keyword.replace(" ", "_")}{artifact_type_suffix}'
        response = supabase.table('generated_artifacts').select('*').eq('ticker', ticker).eq('artifact_type', artifact_type).order('created_at', desc=True).limit(1).single().execute()
        
        if response.data:
            print(f"    -> ✅ [DB] Informe individual encontrado para {ticker}.")
            return response.data
        else:
            print(f"    -> 🟡 [DB] No se encontró informe individual para {ticker}.")
            return None
    except Exception as e:
        print(f"  -> ❌ Error al recuperar informe individual para {ticker}: {e}")
        return None

def get_latest_report(report_keyword: str = None, ticker: str = None, artifact_type_suffix: str = '_final') -> dict | None:
    """
    (Versión Inteligente y Flexible)
    Recupera el último artefacto final para un report_keyword O para un ticker específico.
    
    Args:
        report_keyword: Tipo de informe (ej: 'comite_tecnico_mercado', 'mesa_redonda')
        ticker: Ticker específico (ej: 'SPIPSA.INDX', 'COPPER')
        artifact_type_suffix: Sufijo del tipo de artefacto ('_final' por defecto)
    
    Returns:
        dict: El artefacto más reciente que coincida con los criterios
    """
    if not supabase: 
        return None
    
    # Validación: debe tener al menos uno de los dos parámetros
    if not report_keyword and not ticker:
        print("❌ [DB Manager] Error: Debe especificar report_keyword O ticker")
        return None
    
    try:
        query = supabase.table('generated_artifacts').select('*')
        
        # Construir la consulta basada en los parámetros proporcionados
        if report_keyword and ticker:
            # Caso 1: Ambos parámetros - buscar por ticker específico en un tipo de informe específico
            artifact_type = f'report_{report_keyword.replace(" ", "_")}{artifact_type_suffix}'
            query = query.eq('artifact_type', artifact_type).eq('ticker', ticker)
            print(f"🛠️ [DB Manager] Buscando informe '{report_keyword}' para ticker '{ticker}'...")
            
        elif ticker:
            # Caso 2: Solo ticker - buscar cualquier informe final para ese ticker
            query = query.eq('ticker', ticker).like('artifact_type', f'%{artifact_type_suffix}')
            print(f"🛠️ [DB Manager] Buscando último informe final para ticker '{ticker}'...")
            
        else:
            # Caso 3: Solo report_keyword - buscar el último informe de ese tipo (comportamiento original)
            artifact_type = f'report_{report_keyword.replace(" ", "_")}{artifact_type_suffix}'
            query = query.eq('artifact_type', artifact_type)
            print(f"🛠️ [DB Manager] Buscando último informe '{report_keyword}'...")
        
        # Ejecutar consulta ordenada por fecha descendente
        response = query.order('created_at', desc=True).limit(1).single().execute()
        
        if response.data:
            artifact_id = response.data.get('id', 'N/A')
            artifact_type = response.data.get('artifact_type', 'N/A')
            ticker_found = response.data.get('ticker', 'N/A')
            print(f"    -> ✅ [DB] Artefacto encontrado: ID={artifact_id}, Tipo={artifact_type}, Ticker={ticker_found}")
            return response.data
        else:
            print(f"    -> 🟡 [DB] No se encontró artefacto.")
            return None
            
    except Exception as e:
        print(f"  -> ❌ Error al recuperar último informe: {e}")
        return None                


def insert_materia_prima_dossier(topic: str, evidence: dict) -> dict | None:
    """
    (Versión con Historial)
    Inserta un nuevo dossier de materia prima para un tópico, conservando
    las ejecuciones anteriores como un historial.
    """
    if not supabase: return None
    try:
        data_to_insert = {
            'topic': topic,
            'dossier_content': evidence,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # 2. El comentario ahora describe la nueva lógica.
        # Siempre insertamos una nueva fila para crear un historial.
        response = supabase.table('materia_prima_dossiers').insert(data_to_insert).execute()

        if response.data:
            # 3. El mensaje de log es ahora más preciso.
            print(f"✅ Lote de materia prima para '{topic}' guardado exitosamente.")
            return response.data[0]
        return None
        
    except Exception as e:
        print(f"❌ Error al guardar el lote de materia prima: {e}")
        return None

def get_materia_prima_dossier(topic: str) -> dict | None:
    """(Versión con Historial) Recupera el último dossier de materia prima."""
    if not supabase: return None
    try:
        response = supabase.table('materia_prima_dossiers') \
            .select('dossier_content') \
            .eq('topic', topic) \
            .order('created_at', desc=True) \
            .limit(1) \
            .single() \
            .execute()
        if response.data:
            return response.data.get('dossier_content')
        return None
    except Exception as e:
        if 'JSON object requested, multiple (or no) rows returned' in str(e):
             print(f"🟡 No se encontró materia prima para el tema '{topic}'.")
             return None
        print(f"❌ Error al recuperar lote de materia prima: {e}")
        return None
    
def get_latest_draft_artifact(topic: str) -> dict | None:
    """
    Recupera el artefacto de borrador (_draft) más reciente para un tópico.
    """
    if not supabase: return None
    try:
        print(f"  -> 📦 [DB] Buscando el último borrador para '{topic}'...")
        artifact_type_pattern = f'report_{topic}_draft'
        
        response = supabase.table('generated_artifacts') \
            .select('*') \
            .eq('artifact_type', artifact_type_pattern) \
            .order('created_at', desc=True) \
            .limit(1) \
            .maybe_single() \
            .execute()

        if response.data:
            print(f"    -> ✅ [DB] Borrador encontrado con ID: {response.data.get('id')}")
            return response.data
        else:
            print(f"    -> 🟡 [DB] No se encontró un borrador para '{topic}'.")
            return None
            
    except Exception as e:
        print(f"    -> ❌ [DB] Error al buscar el último borrador: {e}")
        return None

# En quantex/core/database_manager.py

def create_knowledge_edge(source_node_id: str, target_node_id: str, relationship_type: str, metadata: dict = None) -> dict | None:
    """
    (Versión 2.0)
    Crea una nueva conexión (edge) entre dos nodos, incluyendo opcionalmente
    un diccionario de metadatos en formato JSON.
    """
    if not all([source_node_id, target_node_id, relationship_type]):
        print("    -> ⚠️  Faltan datos para crear el edge. Omitiendo.")
        return None
    
    try:
        print(f"    -> 🔗 Creando conexión: ({source_node_id}) -[{relationship_type}]-> ({target_node_id})")
        edge_data = {
            'source_id': source_node_id,
            'target_id': target_node_id,
            'relationship_type': relationship_type
        }
        
        # Agregar metadata (siempre presente para justificaciones del Archivista)
        if metadata:
            edge_data['metadata'] = metadata
        else:
            edge_data['metadata'] = None
        response = supabase.table('edges').insert(edge_data).execute()
        
        if response.data:
            print("      -> ✅ Conexión guardada exitosamente.")
            return response.data[0]
        return None

    except Exception as e:
        print(f"      -> ❌ Error en create_knowledge_edge: {e}")
        return None  
    

def get_all_drivers_paths() -> list:
    """
    Recupera una lista de todas las rutas a los archivos de drivers
    desde las definiciones de informes activos.
    """
    try:
        # Seleccionamos únicamente la columna 'drivers_map' donde is_active = true
        response = supabase.table('report_definitions').select('drivers_map').eq('is_active', True).execute()
        
        if response.data:
            # Creamos una lista de las rutas, eliminando valores nulos o vacíos
            paths = [item['drivers_map'] for item in response.data if item.get('drivers_map')]
            # Usamos set para devolver una lista de rutas únicas
            return list(set(paths))
        return []
    except Exception as e:
        print(f"  -> ❌ Error en get_all_drivers_paths: {e}")
        return []    
    
# Añade esta función al final de tu archivo: quantex/core/database_manager.py

def upsert_fixed_income_trades(records_to_insert: list) -> bool:
    """
    Inserta o actualiza registros en la tabla 'fixed_income_trades'.
    Si un registro para un instrumento en una fecha ya existe, lo actualiza.
    Si no, lo inserta.
    """
    if not supabase:
        print("❌ Error: Cliente de Supabase no disponible.")
        return False
    
    if not records_to_insert:
        print("🟡 No hay registros para la operación upsert.")
        return True # No es un error, simplemente no hay nada que hacer.

    print(f"💾 Ejecutando UPSERT para {len(records_to_insert)} registros en 'fixed_income_trades'...")
    try:
        # 'on_conflict' le dice a Supabase que la combinación de instrument_id y trade_date
        # debe ser única. Si se repite, actualiza el registro en lugar de crear uno nuevo.
        response = supabase.table('fixed_income_trades').upsert(
            records_to_insert,
            on_conflict='instrument_id,trade_date' 
        ).execute()

        print("🎉 ¡Éxito! Los datos han sido guardados/actualizados en la base de datos.")
        return True
        
    except Exception as e:
        print(f"❌ ERROR durante la operación UPSERT: {e}")
        # Si quieres ver el detalle completo del error, descomenta la siguiente línea
        # import traceback; traceback.print_exc()
        return False

def get_expert_context(report_keyword: str) -> dict | None:
    """
    (Versión Robusta 2.0 - Modo Historial)
    Recupera el último contexto de visión experta para un tópico, ordenando
    por fecha para asegurar que siempre se obtiene el más reciente del historial.
    """
    if not supabase: return None
    try:
        response = supabase.table('expert_context') \
            .select('*') \
            .eq('report_keyword', report_keyword) \
            .order('last_updated', desc=True) \
            .limit(1) \
            .maybe_single() \
            .execute()
            
        return response.data if response.data else None
    except Exception as e:
        print(f"-> ⚠️  Advertencia: No se pudo obtener el contexto experto para '{report_keyword}'. Error: {e}")
        return None

def update_expert_context(report_keyword: str, view_label: str, thesis_summary: str, artifact_id: str):
    """
    (Versión 4.0 - Modo Historial)
    Inserta una nueva entrada de visión experta para crear un log histórico.
    """
    if not supabase:
        print("-> ❌ Error: Cliente de Supabase no disponible.")
        return

    try:
        print(f"  -> 🧠 Guardando NUEVA 'Visión Experta' para '{report_keyword}' en el historial...")
        
        data_to_insert = {
            'report_keyword': report_keyword,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'current_view_label': view_label,
            'core_thesis_summary': thesis_summary,
            'source_artifact_id': artifact_id
        }

        # Cambiamos a un simple insert para construir el historial
        supabase.table('expert_context').insert(data_to_insert).execute()
            
        print(f"    -> ✅ Nueva entrada de Memoria Estratégica para '{report_keyword}' guardada exitosamente.")

    except Exception as e:
        print(f"-> ❌ Error crítico guardando el contexto experto para '{report_keyword}'. Error: {e}")
        import traceback
        traceback.print_exc()   


def get_supabase_client_id():
    """Devuelve el ID de memoria del objeto cliente de Supabase."""
    if supabase:
        return id(supabase)
    return None        


def save_briefing_node(topic: str, briefing_content: str) -> str:
    """
    Guarda un Briefing Estratégico como un Nodo de alta prioridad en el grafo.
    """
    print(f"  -> 💾 Guardando 'Briefing Estratégico' para '{topic}' como Nodo...")
    if not supabase: return None
    try:
        node_id = str(uuid.uuid4())
        node_properties = {
            "source": "Human In The Loop",
            "source_type": "Briefing Estratégico",
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # --- INICIO DE LA CORRECCIÓN CLAVE ---
        # Añadimos la hora, minuto y segundo al nombre para hacerlo único
        unique_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        # --- FIN DE LA CORRECCIÓN CLAVE ---

        response = supabase.table('nodes').insert({
            "id": node_id,
            "type": "Briefing",
            "label": f"Briefing Estratégico - {topic} - {unique_timestamp}", # <-- Usamos el timestamp único
            "content": briefing_content,
            "properties": node_properties
        }).execute()

        if response.data:
            print(f"    -> ✅ Briefing guardado exitosamente como Nodo con ID: {response.data[0]['id']}")
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"    -> ❌ Error guardando el Briefing como Nodo: {e}")
        return None
    
# OBSOLETO: Esta función ya no se usa. El sistema ahora usa status ACTIVE/CONSUMED
# def get_latest_briefing_node(topic: str) -> dict | None:
#     """
#     Busca el Briefing más reciente para un tópico.
#     - Caso A: Nodos canónicos type='Briefing' guardados por save_briefing_node
#     - Caso B (fallback): Nodos type='Documento' creados por la sesión, con
#       properties.source='Strategic_Alignment_Session' y properties.topic=topic
#     """
#     print(f"  -> 🕵️  [DB] Buscando el último 'Briefing Estratégico' para '{topic}'...")
#     try:
#         # Intento A: Nodo canónico de Briefing
#         res_briefing = supabase.table('nodes') \
#             .select('*') \
#             .eq('type', 'Briefing') \
#             .eq('properties->>topic', topic) \
#             .order('created_at', desc=True) \
#             .limit(1) \
#             .maybe_single() \
#             .execute()
#
#         if res_briefing.data:
#             print("    -> ✅ [DB] Briefing canónico encontrado.")
#             return res_briefing.data
#
#         # Intento B: Documento de la Sesión de Alineamiento (fallback)
#         res_fallback = supabase.table('nodes') \
#             .select('*') \
#             .eq('type', 'Documento') \
#             .eq('properties->>source', 'Strategic_Alignment_Session') \
#             .eq('properties->>topic', topic) \
#             .order('created_at', desc=True) \
#             .limit(1) \
#             .maybe_single() \
#             .execute()
#
#         if res_fallback.data:
#             print("    -> ✅ [DB] Briefing derivado de sesión encontrado (fallback).")
#             return res_fallback.data
#
#         print("    -> 🟡 [DB] No se encontró un Briefing para este tópico.")
#         return None
#             
#     except Exception as e:
#         print(f"    -> ℹ️  [DB] No hay briefings disponibles para '{topic}': {e}")
#         return None   
    
def get_all_series_definitions():
    """
    Obtiene todas las definiciones de series activas desde la base de datos.
    """
    try:
        response = supabase.table('series_definitions').select('*').eq('is_active', True).execute()
        if response.data:
            return response.data
        else:
            return []
    except Exception as e:
        print(f"Error al obtener las definiciones de series: {e}")
        return None

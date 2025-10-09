# --- 1. Importaciones de Librerías y Configuración de Rutas ---
import json, os, sys, traceback, locale, uuid, re, datetime, logging
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, render_template_string
from flask_cors import CORS
import traceback
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- 2. INICIALIZACIÓN CRÍTICA DE SERVICIOS ---
# Primero, importamos los módulos base que gestionan el estado global.
from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core.tool_registry import registry 
from quantex.core.dossier import Dossier
from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine
from quantex.core.semantic_search_engine import get_semantic_engine
from quantex.grafo.interfaz_universal import get_grafo_interface

# --- 3. Importaciones del Resto de la Aplicación ---
# Ahora que los servicios están listos, importamos los componentes que dependen de ellos.
from quantex.core.dossier import Dossier
from quantex.core.flow_registry import FLOW_REGISTRY
from quantex.agents.federation import run_router_agent as run_strategy_planner
from quantex.core.tool_catalog_manager import build_tool_catalog
from quantex.core.handler_registry import register_handler, HANDLER_REGISTRY
from verticals import fair_value
from verticals import analisis_tecnico
from verticals.mesa_redonda import engine_mesa_redonda as mesa_redonda
import inspect
from quantex.core import llm_manager
from quantex.core.agent_tools import get_market_data, get_expert_opinion, fetch_stock_data, _extract_json_from_response
from quantex.core.tools.technical_tools import calculate_all_indicators
from quantex.core.tools.visualization_tools import generate_and_upload_clean_price_chart, generate_and_upload_full_indicator_chart
from verticals.quantex_agora.airtable_manager import send_report_action
from quantex.core.web_tools import get_perplexity_synthesis
from quantex.core.agent_tools import get_file_content
from verticals.quantex_agora.airtable_manager import send_report_action
import verticals.quantex_agora.airtable_manager as agora
from verticals.quantex_agora.airtable_manager import process_webhook_event_action
from quantex.core.interactive_tools import answer_report_question_with_reasoning
from quantex.core.interactive_tools import get_evidence_for_conclusion



# ==============================================================================
# --- FUNCIONES AUXILIARES PARA EL GRAFO DE CONOCIMIENTO ---
# ==============================================================================

def search_knowledge_graph(query: str, top_k: int = 5) -> list:
    """
    Busca en el grafo de conocimiento usando búsqueda semántica
    """
    try:
        print(f"  -> 🔍 Buscando en Pinecone para: '{query}'")
        
        # Generar embedding de la consulta
        query_embedding = ai_services.embedding_model.encode(query).tolist()
        
        # Buscar en Pinecone
        search_results = ai_services.pinecone_index.query(
            vector=query_embedding, 
            top_k=top_k, 
            include_metadata=True
        )
        
        results = []
        for match in search_results.get('matches', []):
            node_id = match['id']
            score = match['score']
            metadata = match.get('metadata', {})
            
            # Obtener información del nodo desde Supabase
            node_response = db.supabase.table('nodes').select('*').eq('id', node_id).execute()
            
            if node_response.data:
                node_data = node_response.data[0]
                
                # Obtener conexiones del nodo
                connections_response = db.supabase.table('edges').select('*').or_(
                    f'source_id.eq.{node_id},target_id.eq.{node_id}'
                ).execute()
                
                connection_count = len(connections_response.data) if connections_response.data else 0
                
                result = {
                    'id': node_id,
                    'title': node_data.get('label', 'Sin título')[:100],
                    'content': node_data.get('content', node_data.get('label', 'Sin contenido'))[:500],
                    'node_type': node_data.get('type', 'Desconocido'),
                    'score': round(score, 3),
                    'connections': connection_count,
                    'created_at': node_data.get('created_at', '')
                }
                results.append(result)
        
        print(f"  -> ✅ Encontrados {len(results)} resultados")
        return results
        
    except Exception as e:
        print(f"  -> ❌ Error en búsqueda del grafo: {e}")
        return []

def search_knowledge_graph_recent(query: str, months: int = 6, top_k: int = 20) -> list:
    """
    Busca en el grafo de conocimiento con filtro temporal - Usa motor unificado
    """
    try:
        print(f"🔍 [Graph Synthesis] Buscando conocimiento reciente: '{query}' (últimos {months} meses)")
        
        # Usar el motor unificado
        engine = get_semantic_engine()
        
        results = engine.search_knowledge(
            query=query,
            top_k=top_k,
            months=months,
            filters=None,
            include_connections=False
        )
        
        print(f"✅ [Graph Synthesis] Encontrados {len(results)} nodos recientes")
        return results
        
    except Exception as e:
        print(f"❌ [Graph Synthesis] Error en búsqueda reciente: {e}")
        traceback.print_exc()
        return []

def prepare_synthesis_context(results: list, query: str) -> str:
    """
    Prepara el contexto para la síntesis de IA
    """
    context = f"Consulta del usuario: '{query}'\n\n"
    context += f"Conocimiento reciente encontrado ({len(results)} nodos):\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"{i}. {result['title']}\n"
        context += f"   Tipo: {result['node_type']}\n"
        context += f"   Fecha: {result['created_at']}\n"
        context += f"   Contenido: {result['content']}\n\n"
    
    return context

def generate_intelligent_synthesis(context: str, query: str) -> str:
    """
    Genera síntesis inteligente usando Claude
    """
    try:
        prompt = f"""
Eres un asistente experto en análisis de conocimiento. Tu tarea es sintetizar el conocimiento reciente de un usuario sobre un tema específico.

{context}

Instrucciones:
1. Sintetiza el conocimiento de manera coherente y estructurada
2. Identifica los puntos clave y patrones principales
3. Destaca información relevante y actual
4. Mantén un tono profesional pero accesible
5. Si hay información contradictoria, menciónala
6. Limita la respuesta a máximo 500 palabras

Responde en español y enfócate en proporcionar insights útiles basados en el conocimiento reciente.
"""
        
        response = llm_manager.generate_completion(
            task_complexity='reasoning',
            system_prompt=prompt,
            user_prompt=f"Sintetiza el conocimiento sobre: {query}"
        )
        
        return response.get('raw_text', 'No se pudo generar la síntesis')
        
    except Exception as e:
        print(f"  -> ❌ Error generando síntesis: {e}")
        return f"Error generando síntesis: {str(e)}"

# ==============================================================================
# --- FÁBRICA DE LA APLICACIÓN ---
# ==============================================================================

def create_app():

    app = Flask(__name__, template_folder='templates', static_folder='static')
    CORS(app)
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

    # --- LOG A ARCHIVO Y CONSOLA PARA REQUESTS (DIAGNÓSTICO) ---
    try:
        logs_dir = os.path.join(PROJECT_ROOT, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        request_logger = logging.getLogger('quantex.requests')
        if not request_logger.handlers:
            request_logger.setLevel(logging.INFO)
            fh = logging.FileHandler(os.path.join(logs_dir, 'server_requests.log'), encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s - %(message)s')
            fh.setFormatter(fmt)
            # También enviar a consola para ver en terminal
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            request_logger.addHandler(fh)
            request_logger.addHandler(sh)
    except Exception:
        request_logger = logging.getLogger('quantex.requests')

    # --- ESPÍAS GLOBALES DE REQUESTS ---
    @app.before_request
    def _spy_before_request():
        try:
            msg = f"BEFORE {request.method} {request.path}"
            print(f"[SENTINEL] {msg}")
            request_logger.info(msg)
        except Exception:
            pass

    @app.after_request
    def _spy_after_request(response):
        try:
            msg = f"AFTER {request.method} {request.path} -> {response.status_code}"
            print(f"[SENTINEL] {msg}")
            request_logger.info(msg)
        except Exception:
            pass
        return response

    @app.errorhandler(404)
    def _spy_404(e):
        print(f"[SENTINEL] 404 for {request.method} {request.path}")
        return jsonify({"error": "Not Found", "path": request.path}), 404

    @app.route('/health')
    def _health():
        print("[SENTINEL] /health ping")
        request_logger.info("/health ping")
        return jsonify({"ok": True})

    print("🚀 QUANTEX: Iniciando y configurando sistema...")

    ai_services.initialize()
    registry.register_all_tools()

    if db.supabase: print(" -> ✅ Módulo de Base de Datos listo.")
    print(" -> ✅ Módulo de Registro de Herramientas poblado y listo.")
    print("✅ QUANTEX: Sistema inicializado y listo.")
    
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        print("Advertencia: No se pudo establecer el locale a es_ES.UTF-8.")


# ==============================================================================
# --- MANEJADORES DE FLUJO ---
# ==============================================================================


    @register_handler("run_technical_committee")
    def _handle_run_technical_committee(parameters: dict, **kwargs) -> dict:
        """Delega la ejecución completa a la vertical de Análisis Técnico."""
        print("-> 🚀 [Orquestador] Delegando TOTALMENTE a la vertical: Análisis Técnico...")
        try:

            # --- NUESTRO ESPÍA AQUÍ ---
            print("🕵️  ESPÍA 1 (Servidor): Llamando a mesa_redonda.engine_mesa_redonda.run...")

            # La única línea de lógica: llamar a la vertical y devolver su respuesta.
            return analisis_tecnico.run(parameters)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"response_blocks": [{"type": "text", "content": f"Error crítico al llamar a la vertical de Análisis Técnico: {e}"}]})
        
    @register_handler("generate_consolidated_report")
    def _handle_generate_consolidated_report(parameters: dict, **kwargs) -> dict:
        """Genera reporte consolidado independiente basado en datos base existentes."""
        print("-> 🚀 [Orquestador] Generando reporte consolidado independiente...")
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from verticals.analisis_tecnico.independent_consolidated_generator import run_independent_consolidated_generator
            
            return run_independent_consolidated_generator(parameters)
        except Exception as e:
            print(f"❌ [Orquestador] Error generando consolidado independiente: {e}")
            import traceback
            traceback.print_exc()
            return {"response_blocks": [{"type": "text", "content": f"Error generando consolidado: {e}"}]}
        

    @register_handler("strategic_alignment_session")
    def _handle_strategic_alignment_session(parameters: dict, state: dict, user_message: str, **kwargs) -> dict:
        print("-> 🤝 [Sesión de Alineamiento v2.0 - Robusta] Iniciando o continuando diálogo...")
        topic = parameters.get("report_keyword")
        
        alignment_history = state.get("alignment_session_history", [])
        
        # --- LÓGICA DE INICIO DE SESIÓN (SOLO LA PRIMERA VEZ) ---
        if not alignment_history:
            print("    -> 🚀 Iniciando nueva sesión. Realizando verificación exhaustiva de contexto...")
            
            # 1. VERIFICAR EL BORRADOR
            draft = db.get_latest_draft_artifact(topic)
            if not draft or not draft.get('content_dossier'):
                error_msg = f"No se encontró un pre-informe válido (con contenido) para '{topic}'. Por favor, ejecuta primero 'generar pre informe para {topic}'."
                return jsonify({"response_blocks": [{"type": "text", "content": error_msg, "display_target": "chat"}]})

            # 2. VERIFICAR LA VISIÓN EXPERTA
            expert_context = db.get_expert_context(topic)
            if not expert_context:
                error_msg = f"No se encontró una Visión Estratégica para '{topic}'. Asegúrate de que el último 'generar pre informe' se completó exitosamente y guardó este dato."
                return jsonify({"response_blocks": [{"type": "text", "content": error_msg, "display_target": "chat"}]})

            # 3. VERIFICAR EL PROMPT DEL ORÁCULO
            report_def = db.get_report_definition_by_topic(topic)
            prompt_oraculo = None
            synthesis_pipeline_str = report_def.get('synthesis_pipeline', '[]')
            synthesis_pipeline = json.loads(synthesis_pipeline_str) if isinstance(synthesis_pipeline_str, str) else synthesis_pipeline_str

            if synthesis_pipeline and isinstance(synthesis_pipeline, list) and len(synthesis_pipeline) > 0:
                prompt_oraculo_path = synthesis_pipeline[0].get('prompt_file')
                if prompt_oraculo_path:
                    prompt_oraculo = get_file_content(prompt_oraculo_path)

            if not prompt_oraculo:
                error_msg = f"Error Crítico: No se pudo encontrar la ruta al 'prompt_file' en la definición del informe para '{topic}'. La sesión no puede continuar."
                return jsonify({"response_blocks": [{"type": "text", "content": error_msg, "display_target": "chat"}]})
            
            # --- SI TODAS LAS VERIFICACIONES PASAN, GUARDAMOS EL CONTEXTO ---
            state['alignment_context'] = {
                "tesis_actual": expert_context.get('core_thesis_summary', 'No definida'),
                "prompt_oraculo": prompt_oraculo,
                "borrador_actual": json.dumps(draft.get('content_dossier', {}).get('ai_content', {}), indent=2, ensure_ascii=False)
            }
            state['active_session'] = 'strategic_alignment_session'
            state['active_session_params'] = parameters

        # --- LÓGICA DE DIÁLOGO Y CIERRE (SIN CAMBIOS) ---
        if not alignment_history or (len(alignment_history) > 0 and alignment_history[-1].get('content') != user_message):
            alignment_history.append({"role": "Humano", "content": user_message})

        if "guardar briefing" in user_message.lower() or "estamos alineados" in user_message.lower():
            print("    -> ✅ Consenso alcanzado. Guardando Briefing Estratégico COMPLETO...")
            
            # Formatear como diálogo estructurado completo
            formatted_dialogue = "\n".join([
                f"**{turn['role'].upper()}**: {turn['content']}" 
                for turn in alignment_history
            ])
            
            # Usar el nuevo motor de ingesta centralizado
            try:
                print("    -> 🏭 Inicializando Motor de Ingesta Centralizado...")
                ingestion_engine = KnowledgeGraphIngestionEngine()
                
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                source_context = {
                    "source": "Strategic_Alignment_Session",
                    "topic": topic,
                    "source_type": "Briefing_Estratégico_Completo",
                    "original_url": f"briefing_completo_{now_iso}",
                    # Estado explícito para detección inmediata por el motor de síntesis:
                    "status": "ACTIVE",
                    # Timestamp normalizado para ordenación y fallback por fecha
                    "timestamp": now_iso,
                    # Metadatos adicionales para debugging
                    "session_length": len(alignment_history),
                    "dialogue_format": "structured_complete"
                }
                
                result = ingestion_engine.ingest_document(formatted_dialogue, source_context)
                if result.get("success"):
                    print(f"    -> ✅ Briefing COMPLETO guardado como unidad coherente ({len(alignment_history)} turnos de diálogo).")
                else:
                    print(f"    -> ❌ Error en ingesta de briefing: {result.get('reason', 'Desconocido')}")
                    
            except Exception as e:
                print(f"    -> ❌ Error crítico guardando briefing: {e}")
                traceback.print_exc()
            
            state.pop("active_session", None)
            state.pop("active_session_params", None)
            state.pop("alignment_session_history", None)
            state.pop("alignment_context", None)
            
            return jsonify({
                "response_blocks": [{"type": "text", "content": f"✅ Briefing Estratégico para '{topic}' guardado. Ahora puedes generar el informe final.", "display_target": "chat"}],
                "state": state
            })

        context = state.get('alignment_context', {})
        prompt_template = get_file_content("verticals/mesa_redonda/impact_analyst_prompt.md")
        
        prompt = prompt_template.format(
            tesis_actual=context.get('tesis_actual', 'No disponible'),
            prompt_oraculo=context.get('prompt_oraculo', 'No disponible'),
            borrador_actual=context.get('borrador_actual', 'No disponible'),
            historial_conversacion="\n".join([f"- {turn['role']}: {turn['content']}" for turn in alignment_history])
        )

        response = llm_manager.generate_completion(system_prompt=prompt, user_prompt="Continúa la conversación.", task_complexity='complex')
        ai_response_text = response.get('raw_text', 'No pude procesar la respuesta.')

        alignment_history.append({"role": "IA", "content": ai_response_text})
        state["alignment_session_history"] = alignment_history

        return jsonify({
            "response_blocks": [{"type": "text", "content": ai_response_text, "display_target": "chat"}],
            "state": state
        })
        

    @register_handler("ask_expert_opinion")
    def _handle_expert_query(parameters: dict, user_message: str, **kwargs) -> dict:
        """Delega la consulta a expertos a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_expert_query(
            parameters=parameters,
            user_message=user_message,
            **kwargs
        )

    
    @register_handler("run_specialist_analysis")
    def _handle_run_specialist_analysis(parameters: dict, **kwargs) -> dict:
        """Delega el análisis especialista a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_run_specialist_analysis(
            parameters=parameters,
            **kwargs
        )

    @register_handler("answer_with_perplexity")
    def _handle_perplexity_answer(state, user_message, **kwargs) -> dict:
        """Delega la consulta a Perplexity a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_perplexity_answer(
            state=state,
            user_message=user_message,
            **kwargs
        )

    @register_handler("add_evidence_to_d dossier")
    def _handle_add_evidence_to_dossier(state, **kwargs) -> dict:
        """Delega la adición de evidencia a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_add_evidence_to_dossier(
            state=state,
            **kwargs
        )

    @register_handler("edit_artifact")
    def _handle_edit(parameters: dict, state: dict, user_message: str, **kwargs) -> dict:
        """Delega la edición a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_edit(
            parameters=parameters,
            state=state,
            user_message=user_message
        )

    @register_handler("enrich_and_evaluate_artifact")
    def _handle_enrich_and_evaluate(state: dict, user_message: str, **kwargs) -> dict:
        """Delega el enriquecimiento y evaluación a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_enrich_and_evaluate(
            state=state,
            user_message=user_message,
            **kwargs
        )

    @register_handler("social_response")
    def _handle_social_response(parameters, **kwargs):

        """Manejador para respuestas sociales simples."""
        # Podríamos hacer esto más inteligente en el futuro, por ahora es simple.
        return jsonify({"response_blocks": [{"type": "text", "content": "¡Hola! Soy Quantex. ¿En qué puedo ayudarte hoy?", "display_target": "chat"}]})

    @register_handler("out_of_domain_response")
    def _handle_out_of_domain_response(parameters, **kwargs):

        """Manejador para peticiones fuera de dominio."""
        return jsonify({"response_blocks": [{"type": "text", "content": "Entendido, pero mi especialización es el análisis financiero. No puedo ayudarte con esa tarea.", "display_target": "chat"}]})    

    @register_handler("generate_expert_vision")
    def _handle_generate_expert_vision(parameters: dict, **kwargs) -> dict:
        """Delega la generación de visión de experto a la vertical de Mesa Redonda."""
        return mesa_redonda.engine_mesa_redonda._handle_generate_expert_vision(
            parameters=parameters,
            **kwargs
        )

    @register_handler("run_fair_value_analysis")
    def _handle_run_fair_value_analysis(parameters: dict, **kwargs) -> dict:
        """Delega la ejecución completa a la vertical de Fair Value."""
        print("-> 🚀 [Orquestador] Delegando TOTALMENTE a la vertical: Fair Value...")
        try:
            return fair_value.run(parameters)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"response_blocks": [{"type": "text", "content": f"Error crítico en el orquestador al llamar a la vertical: {e}"}]})
        

    @register_handler("retrieve_latest_report")
    def _handle_retrieve_report(parameters: dict, state: dict, **kwargs) -> dict:
        """
        (Versión Inteligente y Flexible)
        Busca el último informe por report_keyword O por ticker, lo muestra en el panel y devuelve el estado actualizado.
        """
        report_keyword = parameters.get("report_keyword")
        ticker = parameters.get("ticker")
        
        # Resolver aliases humanos → keyword canónico
        if report_keyword:
            try:
                from quantex.core.report_aliases import resolve_report_keyword
                report_keyword = resolve_report_keyword(report_keyword)
            except Exception:
                pass
        
        # Validación: debe tener al menos uno de los dos parámetros
        if not report_keyword and not ticker:
            return jsonify({"response_blocks": [{"type": "text", "content": "No se especificó qué informe recuperar. Debe proporcionar 'report_keyword' O 'ticker'."}]})

        # Usar la función inteligente que puede buscar por cualquiera de los dos parámetros
        latest_report = db.get_latest_report(report_keyword=report_keyword, ticker=ticker, artifact_type_suffix='_final')

        if not latest_report:
            search_criteria = []
            if report_keyword:
                search_criteria.append(f"reporte '{report_keyword}'")
            if ticker:
                search_criteria.append(f"ticker '{ticker}'")
            criteria_text = " y ".join(search_criteria)
            return jsonify({"response_blocks": [{"type": "text", "content": f"No se encontró un informe final publicado para {criteria_text}."}]})

        # --- INICIO DE LA CORRECCIÓN CLAVE ---
        # Guardamos el ID del artefacto en el estado de la sesión
        artifact_id = latest_report.get('id')
        state['artifact_id'] = artifact_id
        # --- FIN DE LA CORRECCIÓN CLAVE ---

        # Mensaje informativo sobre qué se encontró
        found_ticker = latest_report.get('ticker', 'N/A')
        found_type = latest_report.get('artifact_type', 'N/A')
        display_message = f"Mostrando informe encontrado: {found_type}"
        if found_ticker != 'N/A':
            display_message += f" para {found_ticker}"

        return jsonify({
            "response_blocks": [
                {"type": "html", "content": latest_report.get('full_content', ''), "display_target": "panel"},
                {"type": "text", "content": display_message, "display_target": "chat"}
            ],
            "artifact_id": artifact_id,
            "state": state  # <-- Devolvemos el estado completo al frontend
        })

    @register_handler("generate_draft_report")
    def _handle_fusion_synthesis(parameters: dict, **kwargs) -> dict:
        """Delega la ejecución completa a la vertical de Mesa Redonda."""
        print("-> 🚀 [Orquestador] Delegando TOTALMENTE a la vertical: Mesa Redonda...")
        try:
            # La única línea de lógica: llamar a la vertical y devolver su respuesta.
            return mesa_redonda.run(parameters)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"response_blocks": [{"type": "text", "content": f"Error crítico al llamar a la vertical de Mesa Redonda: {e}"}]})
        
        
    @register_handler("load_data")
    def _handle_load_data(parameters: dict, **kwargs) -> dict:
        """Delega la carga de datos a la vertical de Mesa Redonda."""
        try:
            print("[SENTINEL] -> _handle_load_data: entrada", parameters)
            result = mesa_redonda.load_data(parameters=parameters)
            print("[SENTINEL] <- _handle_load_data: retorno OK")
            return result
        except Exception as e:
            print(f"[SENTINEL] !! _handle_load_data: excepción: {e}")
            raise

    @register_handler("send_report")
    def _handle_send_report(parameters, **kwargs):
        report_topic = parameters.get("report_keyword")
        recipient = parameters.get("recipient") # <-- Usamos la clave 'recipient' que envía el Router
        message = agora.send_report_action(report_topic, recipient)
        return jsonify({"response_blocks": [{"type": "text", "content": message}]})
    
    @register_handler("trace_evidence_for_conclusion") 
    def _handle_answer_with_reasoning(parameters: dict, state: dict, user_message: str, **kwargs) -> dict:
        """
        Delega la respuesta a una pregunta de seguimiento al orquestador del
        "Equipo de Analistas de IA".
        """
        print("-> 🧠 [Orquestador] Delegando al 'Equipo de Analistas'...")
        
        # Inyectamos el artifact_id desde el estado de la sesión, que es seguro.
        parameters['artifact_id'] = state.get('artifact_id')

        # Llamamos a la función orquestadora principal que construimos en la Fase 2
        return answer_report_question_with_reasoning(
            parameters=parameters,
            user_message=user_message
        )



    # ==============================================================================
    # --- RUTA PRINCIPAL Y ORQUESTADOR (VERSIÓN DINÁMICA) ---
    # ==============================================================================



    @app.route('/')
    def index():
        return render_template('index.html')
    
    
    @app.route('/graph-visualize', methods=['POST'])
    def graph_visualize():
        """Endpoint para generar visualización del grafo completo"""
        try:
            print("📊 [Graph Visualizer] Generando visualización del grafo completo...")
            
            # Importar las funciones de visualización
            from quantex.pipelines.pinecone_visualizer import visualize_full_knowledge_graph, get_all_data_paginated
            
            # Obtener estadísticas del grafo
            nodes_data = get_all_data_paginated('nodes')
            edges_data = get_all_data_paginated('edges')
            
            node_count = len(nodes_data)
            edge_count = len(edges_data)
            
            print(f"  -> 📊 Grafo tiene {node_count} nodos y {edge_count} conexiones")
            
            if node_count == 0:
                return jsonify({
                    'error': 'No hay nodos en el grafo para visualizar',
                    'node_count': node_count,
                    'edge_count': edge_count
                }), 400
            
            # Generar la visualización
            visualize_full_knowledge_graph()
            
            # Buscar el archivo generado
            import os
            image_filename = "grafo_conocimiento_completo.png"
            if os.path.exists(image_filename):
                # Subir a Supabase Storage para servir la imagen
                try:
                    with open(image_filename, 'rb') as f:
                        image_data = f.read()
                    
                    # Subir a Supabase Storage usando el bucket existente
                    public_url = db.upload_file_to_storage(
                        "report-charts", 
                        f"graph_visualizations/{image_filename}", 
                        image_data
                    )
                    
                    if public_url:
                        
                        return jsonify({
                            'success': True,
                            'image_url': public_url,
                            'node_count': node_count,
                            'edge_count': edge_count,
                            'message': 'Visualización generada exitosamente'
                        })
                    
                except Exception as e:
                    print(f"  -> ⚠️ Error subiendo imagen: {e}")
                    # Fallback: devolver éxito sin URL
                    return jsonify({
                        'success': True,
                        'node_count': node_count,
                        'edge_count': edge_count,
                        'message': 'Visualización generada (archivo local)',
                        'local_file': image_filename
                    })
            else:
                return jsonify({
                    'error': 'No se pudo generar el archivo de visualización',
                    'node_count': node_count,
                    'edge_count': edge_count
                }), 500
            
        except Exception as e:
            print(f"❌ [Graph Visualizer] Error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500
    
    @app.route('/graph-synthesis', methods=['POST'])
    def graph_synthesis():
        """Endpoint para síntesis inteligente de conocimiento reciente"""
        try:
            data = request.get_json()
            query = data.get('query', '').strip()
            
            if not query:
                return jsonify({'error': 'Query vacía'}), 400
            
            print(f"🧠 [Graph Synthesis] Procesando síntesis: '{query}'")
            
            # Buscar nodos relevantes de los últimos 6 meses
            results = search_knowledge_graph_recent(query, months=6, top_k=20)
            
            if not results:
                return jsonify({
                    'error': 'No se encontró conocimiento reciente sobre este tema',
                    'query': query
                }), 404
            
            # Preparar contexto para IA
            context = prepare_synthesis_context(results, query)
            
            # Generar síntesis con Claude
            synthesis = generate_intelligent_synthesis(context, query)
            
            return jsonify({
                'query': query,
                'synthesis': synthesis,
                'node_count': len(results),
                'timestamp': datetime.datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ [Graph Synthesis] Error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500
    
    @app.route('/graph-insights', methods=['POST'])
    def graph_insights():
        """Endpoint para generar insights predictivos del grafo"""
        try:
            data = request.get_json() or {}
            months = data.get('months', 6)
            
            print(f"📈 [Graph Insights] Generando insights predictivos (últimos {months} meses)")
            
            # Importar el motor de insights predictivos
            from quantex.core.autoconocimiento.insights_predictivos import generate_predictive_insights_report
            
            # Generar reporte completo
            report = generate_predictive_insights_report(months)
            
            if not report.get('success'):
                return jsonify({
                    'error': report.get('error', 'Error desconocido'),
                    'timestamp': datetime.datetime.now().isoformat()
                }), 500
            
            return jsonify({
                'success': True,
                'insights': report.get('predictive_insights'),
                'temporal_data': report.get('temporal_analysis'),
                'connection_data': report.get('connection_analysis'),
                'timestamp': datetime.datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ [Graph Insights] Error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500
    
    @app.route('/graph-temporal', methods=['POST'])
    def graph_temporal():
        """Endpoint para análisis temporal del grafo"""
        try:
            data = request.get_json() or {}
            months = data.get('months', 12)
            
            print(f"📅 [Graph Temporal] Generando análisis temporal (últimos {months} meses)")
            
            # Importar el analizador temporal
            from quantex.core.autoconocimiento.temporal_analyzer import generate_temporal_analysis_report
            
            # Generar reporte completo
            report = generate_temporal_analysis_report(months)
            
            if not report.get('success'):
                return jsonify({
                    'error': report.get('error', 'Error desconocido'),
                    'timestamp': datetime.datetime.now().isoformat()
                }), 500
            
            return jsonify({
                'success': True,
                'evolution_data': report.get('evolution_data'),
                'visualization_url': report.get('visualization_url'),
                'temporal_insights': report.get('temporal_insights'),
                'timestamp': datetime.datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ [Graph Temporal] Error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500
    
    @app.route('/graph-correlations', methods=['POST'])
    def graph_correlations():
        """Endpoint para análisis de correlaciones del grafo"""
        try:
            data = request.get_json() or {}
            months = data.get('months', 6)
            
            print(f"🔍 [Graph Correlations] Generando análisis de correlaciones (últimos {months} meses)")
            
            # Importar el detector de correlaciones
            from quantex.core.autoconocimiento.correlation_detector import generate_correlation_analysis_report
            
            # Generar reporte completo
            report = generate_correlation_analysis_report(months)
            
            if not report.get('success'):
                return jsonify({
                    'error': report.get('error', 'Error desconocido'),
                    'timestamp': datetime.datetime.now().isoformat()
                }), 500
            
            return jsonify({
                'success': True,
                'semantic_analysis': report.get('semantic_analysis'),
                'structural_analysis': report.get('structural_analysis'),
                'temporal_analysis': report.get('temporal_analysis'),
                'correlation_insights': report.get('correlation_insights'),
                'timestamp': datetime.datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ [Graph Correlations] Error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500
    
    @app.route('/api/get_evidence', methods=['POST'])
    def handle_get_evidence_request():
        data = request.json
        return get_evidence_for_conclusion(data)

    @app.route("/chat", methods=['POST'])
    def chat():
        response = None
        state = {}
        user_message = ""
        request_data = request.get_json()

        try:
            print("[SENTINEL] /chat: request recibida")
            try:
                print("[SENTINEL] /chat payload:", request_data)
            except Exception:
                pass
            user_message = request_data.get("message", "")
            state = request_data.get("state", {})
            
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
                state['turn_index'] = 0
            state['turn_index'] += 1
            
            conversation_history = db.get_conversation_history(state['session_id'], limit=3)
            dynamic_catalog = build_tool_catalog()
            strategy_plan = run_strategy_planner(user_message, state, dynamic_catalog, conversation_history)
            flow_type = strategy_plan.get("flow_type", "out_of_domain_response").lower()
            print(f"[SENTINEL] /chat: flow_type resuelto -> {flow_type}")
            handler_function = HANDLER_REGISTRY.get(flow_type)

            if handler_function:
                print(f"[SENTINEL] /chat: llamando handler {handler_function.__name__}")
                response = handler_function(
                    parameters=strategy_plan.get("parameters", {}), 
                    state=state, 
                    user_message=user_message,
                    conversation_history=conversation_history
                )
                print("[SENTINEL] /chat: handler retornó respuesta")
            else:
                handler_name_for_error = FLOW_REGISTRY.get(flow_type, {}).get("handler_name", "desconocido")
                error_message = f"-> ❌ ERROR ARQUITECTÓNICO: No se encontró la función '{handler_name_for_error}' registrada para el flujo '{flow_type}'."
                print(error_message)
                response = jsonify({"response_blocks": [{"type": "text", "content": error_message}]})
                response.status_code = 500
                
        except Exception as e:
            print("-> ❌ ERROR CRÍTICO en el flujo principal de 'chat':")
            traceback.print_exc()
            error_response_content = f"Ocurrió un error inesperado en el servidor: {e}"
            response = jsonify({"response_blocks": [{"type": "text", "content": error_response_content}]})
            response.status_code = 500
        
        finally:
            # --- NUEVO BLOQUE DE GUARDADO SEGURO ---
            # Este bloque se ejecuta SIEMPRE, ya sea que hubo éxito o error.
            if state.get('session_id'):
                try:
                    response_data = response.get_json() if response else {"error": "El handler no generó una respuesta válida."}
                    
                    db.save_conversation_turn(
                        session_id=state['session_id'],
                        turn_index=state.get('turn_index', 0),
                        user_message=user_message,
                        quantex_response=response_data
                    )
                except Exception as e:
                    print(f"-> ⚠️  Advertencia CRÍTICA: Fallo al guardar el turno de la conversación: {e}")
            
            if response is None:
                response = jsonify({"response_blocks": [{"type": "text", "content": "Error: la respuesta del servidor es nula."}]})
                response.status_code = 500

        return response
        
    @app.route('/api/brevo_webhook', methods=['POST'])
    def handle_brevo_webhook():
        """
        Este es el endpoint que escucha las notificaciones de Brevo.
        """
        # Obtiene los datos JSON que envía Brevo
        data = request.json
        
        # Imprime los datos recibidos en tu terminal para que puedas verlos
        print("--- 📥 Notificación de Webhook de Brevo Recibida ---")
        print(data)
        
        # Llama a la lógica de negocio en tu airtable_manager para procesar el evento
        process_webhook_event_action(data)
        
        # Le responde a Brevo con un "200 OK" para confirmar que recibimos la notificación
        return jsonify({"status": "success"}), 200    
    

    @app.route('/admin', methods=['GET'])
    def admin_dashboard():
        """
        Esta versión robusta carga las definiciones de informes y maneja
        de forma segura los errores en las columnas JSON, asegurando que la
        plantilla admin.html siempre reciba datos bien formados.
        """
        reports_from_db = []
        try:
            # 1. Obtenemos todos los datos de la tabla de definiciones
            response = db.supabase.table('report_definitions').select('*').order('report_keyword').execute()
            if response.data:
                reports_from_db = response.data
        except Exception as e:
            print(f"Error crítico al conectar con la base de datos: {e}")
            # Si la BD falla, renderizamos la página con una lista vacía
            return render_template('admin.html', reports=[])

        # 2. Definimos qué columnas deberían ser objetos JSON
        json_columns = [
            'market_data_series', 'data_requirements', 'processing_pipeline',
            'synthesis_pipeline', 'visualization_pipeline', 'knowledge_retrieval_config'
        ]

        processed_reports = []
        for report in reports_from_db:
            # 3. Para cada reporte, intentamos "parsear" las columnas JSON
            for column in json_columns:
                # Solo intentamos si la columna existe y es un string no vacío
                if report.get(column) and isinstance(report.get(column), str):
                    try:
                        # Convertimos el string a un objeto Python (lista/diccionario)
                        report[column] = json.loads(report[column])
                    except json.JSONDecodeError:
                        # Si el JSON es inválido, lo dejamos como texto pero añadimos un aviso
                        print(f"Aviso: La columna '{column}' del reporte '{report.get('report_keyword')}' no es un JSON válido.")
                        report[column] = f"Error: JSON Inválido -> {report[column]}"
            processed_reports.append(report)
        
        # 4. Pasamos la lista de reportes ya procesada a la plantilla
        return render_template('admin.html', reports=processed_reports)

    @app.route('/debug')
    def debug_info():
        debug_data = {
            "Entorno de Python": {"python_version": sys.version, "platform": sys.platform},
            "Variables de Entorno Cargadas": {
                "SUPABASE_URL": f"{os.getenv('SUPABASE_URL', 'No encontrada')[:20]}...",
                "SUPABASE_SERVICE_KEY": f"{os.getenv('SUPABASE_SERVICE_KEY', 'No encontrada')[:10]}...",
            },
            "Estado de Clientes de API": {
                "Cliente Supabase": str(type(db.supabase)),
                "Cliente Anthropic (Claude)": str(type(llm_manager.claude_client)) if hasattr(llm_manager, 'claude_client') else 'No inicializado',
                "Modelo Google (Gemini)": "Configurado" if os.getenv("GEMINI_API_KEY") else "No configurado"
            }
        }
        return render_template('debug.html', debug_data=debug_data)

    @app.after_request
    def add_security_headers(response):
        """
        Añade encabezados de seguridad a cada respuesta para permitir
        que el navegador cargue las imágenes desde Supabase Y ejecute los scripts locales.
        """
        # ✅ SEGURO: Obtener dominio desde configuración
        from quantex.config import Config
        supabase_domain = Config.get_supabase_domain()

        # --- POLÍTICA CORREGIDA ---
        # Añadimos 'unsafe-inline' a script-src y style-src para permitir el código
        # y los estilos que están directamente en index.html.
        csp = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline'; "
            f"style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data: {supabase_domain};"
        )

        response.headers['Content-Security-Policy'] = csp
        return response

    return app


    


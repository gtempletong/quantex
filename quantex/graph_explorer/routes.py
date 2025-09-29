from flask import Blueprint, jsonify, render_template, request
import datetime
import traceback

from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core.semantic_search_engine import get_semantic_engine
from quantex.grafo.interfaz_universal import get_grafo_interface

bp = Blueprint('graph_explorer', __name__)


SYNONYM_MAP = {
	"clp": ["peso chileno", "usd/clp", "tipo de cambio chile"],
	"cobre": ["copper", "commodities", "metales"],
	"dxy": ["dólar index", "dollar index"],
}


def reformulate_query(query: str) -> str:
	q = query.lower().strip()
	expansions = []
	for key, syns in SYNONYM_MAP.items():
		if key in q:
			expansions.extend(syns)
	if expansions:
		return query + " " + " ".join(set(expansions))
	return query


def _fetch_neighbors(node_id: str, limit: int = 10) -> list[str]:
	try:
		resp = db.supabase.table('edges').select('*').or_(f'source_id.eq.{node_id},target_id.eq.{node_id}').limit(limit).execute()
		neighbors = set()
		for e in (resp.data or []):
			if e.get('source_id') == node_id:
				neighbors.add(e.get('target_id'))
			else:
				neighbors.add(e.get('source_id'))
		return list(neighbors)
	except Exception:
		return []


def _parse_dt(dt_str: str) -> datetime.datetime | None:
	try:
		return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
	except Exception:
		return None


def search_knowledge_graph(query: str, top_k: int = 5, filters: dict | None = None) -> list:
	"""
	Función de compatibilidad que usa el motor unificado
	"""
	try:
		print(f"🔍 [Graph Explorer] Buscando: '{query[:50]}...'")
		
		# Usar el motor unificado
		engine = get_semantic_engine()
		
		# Convertir filtros al formato del motor unificado
		unified_filters = {}
		if filters:
			# Mapear filtros legacy
			if 'since' in filters:
				# Convertir ISO date a meses aproximados
				since_date = _parse_dt(filters['since'])
				if since_date:
					now = datetime.datetime.now(datetime.timezone.utc)
					days_diff = (now - since_date).days
					months = max(1, days_diff // 30)  # Mínimo 1 mes
				else:
					months = 1
			else:
				months = 1  # Default para Graph Explorer
			
			# Mapear otros filtros
			if 'source' in filters:
				unified_filters['source'] = filters['source']
			if 'topic' in filters:
				unified_filters['topic'] = filters['topic']
			if 'node_type' in filters:
				unified_filters['node_type'] = filters['node_type']
		else:
			months = 1  # Default para Graph Explorer
		
		# Buscar con el motor unificado
		results = engine.search_knowledge(
			query=query,
			top_k=top_k,
			months=months,
			filters=unified_filters,
			include_connections=True
		)
		
		# Aplicar reranking para compatibilidad
		def _rank_key(r):
			created = _parse_dt(r.get('created_at', '')) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
			age_days = (datetime.datetime.now(datetime.timezone.utc) - created).days if created else 9999
			return (
				- r.get('score', 0.0),
				- r.get('connections', 0),
				age_days,
			)
		results.sort(key=_rank_key)
		
		print(f"✅ [Graph Explorer] Encontrados {len(results)} resultados")
		return results
		
	except Exception as e:
		print(f"❌ [Graph Explorer] Error en búsqueda: {e}")
		traceback.print_exc()
		return []


@bp.route('/graph-explorer')
def graph_explorer_page():
	return render_template('graph-explorer.html')


@bp.route('/graph-query', methods=['POST'])
def graph_query():
	try:
		data = request.get_json() or {}
		query = (data.get('query') or '').strip()
		use_grafo_system = data.get('use_grafo_system', True)  # Por defecto usar nuevo sistema
		
		if not query:
			return jsonify({'error': 'Query vacía'}), 400
		
		print(f"🔍 [Graph Explorer Web] Búsqueda: '{query}' (Sistema Grafo: {use_grafo_system})")
		
		# NUEVO: Usar Sistema Grafo si está habilitado
		if use_grafo_system:
			try:
				grafo_interface = get_grafo_interface()
				filters = data.get('filters') or {}
				resultado_completo = grafo_interface.consultar_grafo(query, {"filters": filters, "top_k": 8})
				
				return jsonify({
					'query': query, 
					'results': resultado_completo.get("resultados_encontrados", []),
					'sintesis': resultado_completo.get("sintesis"),
					'estadisticas': resultado_completo.get("estadisticas", {}),
					'grafo_system_used': True,
					'timestamp': datetime.datetime.now().isoformat()
				})
			except Exception as grafo_error:
				print(f"⚠️ [Graph Explorer Web] Error en Sistema Grafo, usando fallback: {grafo_error}")
				# Continuar con sistema legacy
		
		# SISTEMA LEGACY (fallback)
		print("🔄 [Graph Explorer Web] Usando sistema legacy...")
		filters = data.get('filters') or {}
		results = search_knowledge_graph(query, top_k=8, filters=filters)
		
		return jsonify({
			'query': query, 
			'results': results, 
			'grafo_system_used': False,
			'timestamp': datetime.datetime.now().isoformat()
		})
		
	except Exception as e:
		traceback.print_exc()
		return jsonify({'error': f'Error interno: {str(e)}'}), 500



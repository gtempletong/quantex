"""
Motor de Búsqueda Semántica Unificado - Quantex
Versión 1.0 - Filtro Temporal Robusto y Consistente
"""

import os
import sys
import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services

class SemanticSearchEngine:
    """
    Motor de búsqueda semántica unificado con filtro temporal robusto
    """
    
    def __init__(self):
        self.db = db
        self.ai_services = ai_services
        
        # Asegurar que los servicios de AI estén inicializados
        if not hasattr(self.ai_services, 'embedding_model') or self.ai_services.embedding_model is None:
            print("🔧 [SemanticSearch] Inicializando servicios de AI...")
            self.ai_services.initialize()
    
    def search_knowledge(
        self, 
        query: str, 
        top_k: int = 10,
        months: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_connections: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda semántica unificada con filtro temporal por defecto
        
        Args:
            query: Consulta de búsqueda
            top_k: Número máximo de resultados
            months: Meses hacia atrás (None = usar default según contexto)
            filters: Filtros adicionales (source, topic, node_type)
            include_connections: Incluir información de conexiones
            
        Returns:
            Lista de nodos relevantes con metadatos
        """
        try:
            # 1. Configurar filtro temporal por defecto
            if months is None:
                months = self._get_default_temporal_filter()
            
            print(f"🔍 [SemanticSearch] Buscando: '{query[:50]}...' (últimos {months} meses)")
            
            # 2. Calcular fecha límite
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
            
            # 3. Reformular consulta si es necesario
            reformulated_query = self._reformulate_query(query)
            
            # 4. Generar embedding
            query_embedding = self.ai_services.embedding_model.encode(reformulated_query).tolist()
            
            # 5. Construir filtros para Pinecone
            pinecone_filters = self._build_pinecone_filters(cutoff_date, filters)
            
            # 6. Búsqueda en Pinecone con filtros
            query_params = {
                "vector": query_embedding,
                "top_k": top_k * 3,  # Buscar 3x más para compensar filtros
                "include_metadata": True
            }
            
            if pinecone_filters:
                query_params["filter"] = pinecone_filters
            
            search_results = self.ai_services.pinecone_index.query(**query_params)
            
            # 6. Procesar y filtrar resultados
            results = []
            for match in search_results.get('matches', []):
                node_id = match.get('id')
                score = match.get('score', 0.0)
                
                if not node_id:
                    continue
                
                # Obtener datos del nodo desde Supabase
                node_data = self._get_node_data(node_id)
                if not node_data:
                    continue
                
                # Aplicar filtros
                if not self._passes_filters(node_data, cutoff_date, filters):
                    continue
                
                # Construir resultado
                result = self._build_result(node_data, score, include_connections)
                results.append(result)
                
                # Limitar resultados
                if len(results) >= top_k:
                    break
            
            print(f"✅ [SemanticSearch] Encontrados {len(results)} nodos relevantes")
            return results
            
        except Exception as e:
            print(f"❌ [SemanticSearch] Error: {e}")
            traceback.print_exc()
            return []
    
    def _get_default_temporal_filter(self) -> int:
        """
        Determina el filtro temporal por defecto según el contexto
        """
        # Para análisis general, usar 12 meses por defecto para capturar más información
        # Esto permite acceder a más contenido histórico del grafo
        return 12  # 12 meses por defecto (365 días)
    
    def _reformulate_query(self, query: str) -> str:
        """
        Reformula la consulta para mejorar resultados
        """
        # Mapeo de sinónimos
        synonym_map = {
            "clp": ["peso chileno", "usd/clp", "tipo de cambio chile"],
            "cobre": ["copper", "commodities", "metales", "lme", "comex"],
            "dxy": ["dólar index", "dollar index", "usd index"],
            "fed": ["federal reserve", "banco central usa"],
            "bcch": ["banco central chile", "banco central de chile"]
        }
        
        query_lower = query.lower().strip()
        expansions = []
        
        for key, synonyms in synonym_map.items():
            if key in query_lower:
                expansions.extend(synonyms)
        
        if expansions:
            return query + " " + " ".join(set(expansions))
        
        return query
    
    def _get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos completos del nodo desde Supabase
        """
        try:
            response = self.db.supabase.table('nodes').select('*').eq('id', node_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo nodo {node_id}: {e}")
            return None
    
    def _build_pinecone_filters(self, cutoff_date: datetime, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Construye filtros para Pinecone"""
        try:
            # Convertir fecha a timestamp Unix para Pinecone
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            # Usar timestamp Unix para filtros temporales
            pinecone_filters = {
                "timestamp": {"$gte": cutoff_timestamp}
            }
            
            # Agregar filtros adicionales
            if filters:
                for key, value in filters.items():
                    if key in ['source', 'topic', 'node_type']:
                        pinecone_filters[key] = value
            
            return pinecone_filters if pinecone_filters else None
            
        except Exception as e:
            print(f"⚠️ Error construyendo filtros Pinecone: {e}")
            return None
    
    def _passes_filters(
        self, 
        node_data: Dict[str, Any], 
        cutoff_date: datetime, 
        filters: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Verifica si el nodo pasa todos los filtros
        """
        # 1. Filtro temporal obligatorio
        # Buscar fecha en múltiples campos (created_at de Supabase o timestamp de Pinecone)
        created_at = node_data.get('created_at') or node_data.get('timestamp')
        if not created_at:
            return False
        
        try:
            node_date = self._parse_datetime(created_at)
            if node_date < cutoff_date:
                return False
        except Exception:
            return False
        
        # 2. Filtros adicionales si se especifican
        if not filters:
            return True
        
        properties = node_data.get('properties') or {}
        
        # Filtro por fuente
        if 'source' in filters:
            node_source = (properties.get('source') or '').lower()
            filter_source = filters['source']
            
            # Manejar tanto strings como listas
            if isinstance(filter_source, list):
                filter_sources = [s.lower() for s in filter_source]
                if not any(fs in node_source for fs in filter_sources):
                    return False
            else:
                filter_source = filter_source.lower()
                if filter_source not in node_source:
                    return False
        
        # Filtro por tópico
        if 'topic' in filters:
            node_topic = (properties.get('topic') or '').lower()
            filter_topic = filters['topic']
            
            # Manejar tanto strings como listas
            if isinstance(filter_topic, list):
                filter_topics = [t.lower() for t in filter_topic]
                if not any(ft in node_topic for ft in filter_topics):
                    return False
            else:
                filter_topic = filter_topic.lower()
                if filter_topic not in node_topic:
                    return False
        
        # Filtro por tipo de nodo
        if 'node_type' in filters:
            node_type = node_data.get('type', '').lower()
            filter_type = filters['node_type']
            
            # Manejar tanto strings como listas
            if isinstance(filter_type, list):
                filter_types = [t.lower() for t in filter_type]
                if node_type not in filter_types:
                    return False
            else:
                filter_type = filter_type.lower()
                if node_type != filter_type:
                    return False
        
        return True
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """
        Parsea fecha de diferentes formatos
        """
        try:
            if 'Z' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                parsed = datetime.fromisoformat(date_str)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
        except Exception:
            # Fallback a fecha mínima
            return datetime.min.replace(tzinfo=timezone.utc)
    
    def _build_result(
        self, 
        node_data: Dict[str, Any], 
        score: float, 
        include_connections: bool
    ) -> Dict[str, Any]:
        """
        Construye el resultado final
        """
        properties = node_data.get('properties', {})
        
        result = {
            'id': node_data.get('id'),
            'title': node_data.get('label', 'Sin título')[:100],
            'content': node_data.get('content', node_data.get('label', 'Sin contenido'))[:500],
            'node_type': node_data.get('type', 'Desconocido'),
            'score': round(score, 3),
            'created_at': node_data.get('created_at', ''),
            'source': properties.get('source', ''),
            'topic': properties.get('topic', ''),
            'ai_summary': (properties.get('ai_summary') or '')[:200]
        }
        
        # Incluir conexiones si se solicita
        if include_connections:
            try:
                edges_response = self.db.supabase.table('edges').select('*').or_(
                    f'source_id.eq.{node_data["id"]},target_id.eq.{node_data["id"]}'
                ).execute()
                
                result['connections'] = len(edges_response.data) if edges_response.data else 0
                result['neighbors'] = self._get_neighbor_ids(node_data['id'], limit=10)
                
            except Exception as e:
                print(f"⚠️ Error obteniendo conexiones: {e}")
                result['connections'] = 0
                result['neighbors'] = []
        
        return result
    
    def _get_neighbor_ids(self, node_id: str, limit: int = 10) -> List[str]:
        """
        Obtiene IDs de nodos vecinos
        """
        try:
            response = self.db.supabase.table('edges').select('*').or_(
                f'source_id.eq.{node_id},target_id.eq.{node_id}'
            ).limit(limit).execute()
            
            neighbors = set()
            for edge in (response.data or []):
                if edge.get('source_id') == node_id:
                    neighbors.add(edge.get('target_id'))
                else:
                    neighbors.add(edge.get('source_id'))
            
            return list(neighbors)
            
        except Exception:
            return []

# Instancia global del motor
_semantic_engine = None

def get_semantic_engine() -> SemanticSearchEngine:
    """
    Obtiene la instancia global del motor semántico
    """
    global _semantic_engine
    if _semantic_engine is None:
        _semantic_engine = SemanticSearchEngine()
    return _semantic_engine

# Funciones de compatibilidad
def search_knowledge_graph_unified(
    query: str, 
    top_k: int = 10, 
    months: int = None, 
    filters: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Función de compatibilidad para el motor unificado
    """
    engine = get_semantic_engine()
    return engine.search_knowledge(
        query=query,
        top_k=top_k,
        months=months,
        filters=filters,
        include_connections=True
    )


if __name__ == "__main__":
    # Prueba del motor
    print("🧪 Probando Motor de Búsqueda Semántica Unificado...")
    
    engine = SemanticSearchEngine()
    
    # Prueba 1: Búsqueda básica
    results = engine.search_knowledge("cobre", top_k=5, months=1)
    print(f"Resultados: {len(results)}")
    
    # Prueba 2: Con filtros
    results = engine.search_knowledge(
        "cobre", 
        top_k=5, 
        months=1,
        filters={"source": "MktNewsScraper"}
    )
    print(f"Resultados con filtro: {len(results)}")

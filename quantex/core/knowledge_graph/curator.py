"""
Curador del Grafo - Sistema Centralizado
Mantiene la calidad y limpieza del grafo de conocimiento
"""

from typing import List, Dict, Any
from quantex.core import database_manager as db
from quantex.core import llm_manager


class KnowledgeGraphCurator:
    """
    Curador del Grafo - Mantiene la calidad y limpieza del grafo de conocimiento
    """
    
    def __init__(self):
        self.db = db
        self.llm_manager = llm_manager
    
    def get_hub_nodes(self) -> List[Dict[str, str]]:
        """Recupera los nodos principales que sirven como anclas en el grafo."""
        print("  -> 📚 Obteniendo nodos 'hub' principales...")
        try:
            response = self.db.supabase.table('nodes').select('id, label') \
                .in_('type', ['Tópico Principal', 'Briefing']) \
                .execute()
            if response.data:
                hub_nodes = [{'id': node['id'], 'node_name': node['label']} for node in response.data]
                print(f"    -> ✅ Se encontraron {len(hub_nodes)} nodos principales.")
                return hub_nodes
            return []
        except Exception as e:
            print(f"    -> ❌ Error obteniendo nodos principales: {e}")
            return []
    
    def get_orphan_nodes(self) -> List[Dict[str, str]]:
        """Recupera nodos que no tienen ninguna conexión entrante o saliente."""
        print("  -> 🔎 Buscando nodos 'huérfanos' sin conexiones...")
        try:
            source_ids_res = self.db.supabase.table('edges').select('source_id').execute()
            target_ids_res = self.db.supabase.table('edges').select('target_id').execute()
            
            connected_ids = set()
            if source_ids_res.data:
                connected_ids.update([edge['source_id'] for edge in source_ids_res.data])
            if target_ids_res.data:
                connected_ids.update([edge['target_id'] for edge in target_ids_res.data])
            
            all_nodes_res = self.db.supabase.table('nodes').select('id, label').execute()
            if not all_nodes_res.data:
                return []
            
            orphan_nodes = [
                {'id': node['id'], 'node_name': node['label']} 
                for node in all_nodes_res.data 
                if node['id'] not in connected_ids
            ]
            
            print(f"    -> ✅ Se encontraron {len(orphan_nodes)} nodos huérfanos.")
            return orphan_nodes
            
        except Exception as e:
            print(f"    -> ❌ Error buscando nodos huérfanos: {e}")
            return []
    
    def run_curation_cycle(self, topic: str = None) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de curación del grafo
        
        Args:
            topic: Tópico específico a curar (opcional)
            
        Returns:
            Dict con estadísticas de la curación
        """
        print(f"  -> 🔧 [Curador del Grafo] Iniciando ciclo de curación...")
        
        try:
            # Obtener nodos huérfanos
            orphan_nodes = self.get_orphan_nodes()
            
            # Obtener nodos hub
            hub_nodes = self.get_hub_nodes()
            
            # Ejecutar curación específica si se proporciona un tópico
            curation_results = {}
            if topic:
                curation_results = self._curate_topic_specific(topic, orphan_nodes, hub_nodes)
            
            print("  -> ✅ [Curador del Grafo] Ciclo de curación completado.")
            
            return {
                "success": True,
                "orphan_nodes_count": len(orphan_nodes),
                "hub_nodes_count": len(hub_nodes),
                "curation_results": curation_results
            }
            
        except Exception as e:
            print(f"  -> ❌ Error en ciclo de curación: {e}")
            return {"success": False, "error": str(e)}
    
    def _curate_topic_specific(self, topic: str, orphan_nodes: List[Dict], hub_nodes: List[Dict]) -> Dict[str, Any]:
        """Ejecuta curación específica para un tópico"""
        print(f"    -> 🎯 Curación específica para tópico: {topic}")
        
        # Aquí se pueden agregar lógicas específicas de curación
        # Por ejemplo: conectar nodos huérfanos relevantes al tópico
        
        return {
            "topic": topic,
            "orphans_processed": 0,
            "connections_created": 0
        }


# Funciones de conveniencia para mantener compatibilidad
def get_hub_nodes() -> List[Dict[str, str]]:
    """Función de conveniencia para mantener compatibilidad"""
    curator = KnowledgeGraphCurator()
    return curator.get_hub_nodes()


def get_orphan_nodes() -> List[Dict[str, str]]:
    """Función de conveniencia para mantener compatibilidad"""
    curator = KnowledgeGraphCurator()
    return curator.get_orphan_nodes()


def run_knowledge_curator_agent(topic: str = None) -> Dict[str, Any]:
    """Función de conveniencia para mantener compatibilidad"""
    curator = KnowledgeGraphCurator()
    return curator.run_curation_cycle(topic)

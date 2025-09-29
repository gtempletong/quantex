# quantex/core/knowledge_graph/edge_manager.py
"""
Edge Management for Knowledge Graph
Handles creation and management of connections between nodes
"""

from typing import Dict, List, Any, Optional

from quantex.core import database_manager as db


class EdgeManager:
    """
    Manages all edge operations in the knowledge graph.
    """
    
    def create_edge(self, source_id: str, target_id: str, relationship_type: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Create an edge between two nodes.
        Maintains exact same structure as current process_and_store_knowledge()
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            metadata: Optional edge metadata
            
        Returns:
            True if edge was created successfully
        """
        try:
            edge_data = {
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type
            }
            
            if metadata:
                edge_data["metadata"] = metadata
            
            db.supabase.table('edges').upsert([edge_data]).execute()
            return True
        except Exception as e:
            print(f"    -> ❌ Error creando edge: {e}")
            return False
        
    def create_document_entity_edges(self, document_id: str, entity_ids: List[str]) -> int:
        """
        Create edges between a document and its entities.
        Maintains exact same structure as current process_and_store_knowledge()
        
        Args:
            document_id: Document node ID
            entity_ids: List of entity node IDs
            
        Returns:
            Number of edges created
        """
        edges_created = 0
        
        for entity_id in entity_ids:
            if entity_id and self.create_edge(document_id, entity_id, "menciona"):
                edges_created += 1
        
        if edges_created > 0:
            print(f"    -> 🔗 {edges_created} conexiones con entidades creadas.")
        
        return edges_created
        
    def get_node_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all edges connected to a node.
        
        Args:
            node_id: Node ID to get edges for
            
        Returns:
            List of edge data
        """
        # TODO: Implement edge retrieval
        pass

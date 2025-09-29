# quantex/core/knowledge_graph/types/entity_node.py
"""
Entity Node Type
Specific implementation for entity nodes in the knowledge graph
"""

from typing import Dict, Any


class EntityNode:
    """
    Represents an entity node in the knowledge graph.
    """
    
    def __init__(self, entity_name: str):
        self.type = "Entidad"
        self.label = entity_name
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node to dictionary for database storage.
        
        Returns:
            Dictionary representation of the node
        """
        return {
            "type": self.type,
            "label": self.label
        }


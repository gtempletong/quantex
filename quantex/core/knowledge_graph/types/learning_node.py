# quantex/core/knowledge_graph/types/learning_node.py
"""
Learning Node Type
Specific implementation for learning nodes in the knowledge graph
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any


class LearningNode:
    """
    Represents a learning node in the knowledge graph.
    """
    
    def __init__(self, learning_text: str, topic: str):
        self.id = str(uuid.uuid4())
        self.type = "Aprendizaje Clave"
        self.label = f"Aprendizaje sobre {topic} - {self.id[:8]}"
        self.content = learning_text.strip()
        self.topic = topic
        self.created_at = datetime.now(timezone.utc)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node to dictionary for database storage.
        
        Returns:
            Dictionary representation of the node
        """
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "content": self.content
        }


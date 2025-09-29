# quantex/core/knowledge_graph/types/briefing_node.py
"""
Briefing Node Type
Specific implementation for briefing nodes in the knowledge graph
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any


class BriefingNode:
    """
    Represents a briefing node in the knowledge graph.
    """
    
    def __init__(self, briefing_content: str, topic: str):
        self.id = str(uuid.uuid4())
        self.type = "Briefing"
        self.label = f"Briefing Estratégico - {topic}"
        self.content = briefing_content
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
            "content": self.content,
            "properties": {
                "topic": self.topic,
                "created_at": self.created_at.isoformat(),
                "priority": "high"
            }
        }


# quantex/core/knowledge_graph/types/document_node.py
"""
Document Node Type
Specific implementation for document nodes in the knowledge graph
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


class DocumentNode:
    """
    Represents a document node in the knowledge graph.
    """
    
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.type = "Documento"
        self.content = content
        self.metadata = metadata
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
            "label": self._generate_label(),
            "content": self.content,
            "properties": self.metadata
        }
        
    def _generate_label(self) -> str:
        """
        Generate a label for the document node.
        
        Returns:
            Generated label
        """
        title = self.metadata.get('title', 'Documento sin título')
        return f"{title} - {self.id[:8]}"
        
    def get_entities(self) -> List[str]:
        """
        Get entities associated with this document.
        
        Returns:
            List of entity names
        """
        return self.metadata.get('key_entities', [])
        
    def get_categories(self) -> List[str]:
        """
        Get categories associated with this document.
        
        Returns:
            List of categories
        """
        return self.metadata.get('categories', [])

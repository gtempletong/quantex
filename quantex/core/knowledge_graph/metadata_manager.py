# quantex/core/knowledge_graph/metadata_manager.py
"""
Metadata Management for Knowledge Graph
Handles metadata processing, validation and standardization
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Any


class MetadataManager:
    """
    Manages metadata processing and validation for knowledge graph nodes.
    """
    
    def process_document_metadata(self, content: str, source_context: Dict[str, Any], ai_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and standardize metadata for document nodes.
        Maintains exact same structure as current process_and_store_knowledge()
        
        Args:
            content: Document content
            source_context: Source context information
            ai_metadata: AI-generated metadata (node_obj from distill_and_classify_text)
            
        Returns:
            Processed metadata dictionary with exact same structure
        """
        # Calculate content metrics
        metrics = self.calculate_content_metrics(content)
        
        # Build document properties - EXACT SAME STRUCTURE as current system,
        # with backward-compatible inclusion of status and timestamp from source_context
        timestamp_from_context = source_context.get('timestamp')
        normalized_timestamp = None
        if timestamp_from_context:
            try:
                # Normalize to ISO with timezone
                if isinstance(timestamp_from_context, str):
                    normalized_timestamp = datetime.fromisoformat(timestamp_from_context.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat()
                else:
                    normalized_timestamp = datetime.now(timezone.utc).isoformat()
            except Exception:
                normalized_timestamp = datetime.now(timezone.utc).isoformat()
        else:
            normalized_timestamp = datetime.now(timezone.utc).isoformat()

        document_properties = {
            "source": source_context.get('source'),
            "source_type": source_context.get('source_type'),
            "topic": source_context.get('topic'),
            "original_url": source_context.get('original_url'),
            # Guardar hash y hora original del scraper si vienen
            "hash": source_context.get('hash'),
            "scraped_time": source_context.get('scraped_time'),
            # Persist provided timestamp if any; else now
            "timestamp": normalized_timestamp,
            # Explicit status passthrough (e.g., ACTIVE/CONSUMED for briefings)
            "status": source_context.get('status'),
            # Metadatos enriquecidos por la IA
            "ai_summary": ai_metadata.get('ai_summary'),
            "categories": ai_metadata.get('categories'),
            # Datos duros calculados
            "word_count": metrics["word_count"],
            "reading_time_minutes": metrics["reading_time_minutes"]
        }
        
        return document_properties
        
    def process_learning_metadata(self, learning_text: str, topic: str) -> Dict[str, Any]:
        """
        Process and standardize metadata for learning nodes.
        
        Args:
            learning_text: Learning content
            topic: Related topic
            
        Returns:
            Processed metadata dictionary
        """
        # TODO: Implement learning metadata processing
        pass
        
    def process_briefing_metadata(self, briefing_content: str, topic: str) -> Dict[str, Any]:
        """
        Process and standardize metadata for briefing nodes.
        
        Args:
            briefing_content: Briefing content
            topic: Related topic
            
        Returns:
            Processed metadata dictionary
        """
        # TODO: Implement briefing metadata processing
        pass
        
    def calculate_content_metrics(self, content: str) -> Dict[str, Any]:
        """
        Calculate content metrics (word count, reading time, etc.).
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with calculated metrics
        """
        word_count = len(content.split())
        reading_time_minutes = math.ceil(word_count / 200)
        
        return {
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes,
            "character_count": len(content)
        }

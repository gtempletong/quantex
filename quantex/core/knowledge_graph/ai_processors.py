# quantex/core/knowledge_graph/ai_processors.py
"""
AI Processors for Knowledge Graph
Handles AI-powered processing of content and metadata extraction
"""

from typing import Dict, List, Any, Optional

from quantex.core import llm_manager
from quantex.core.agent_tools import get_file_content, _extract_json_from_response


class AIMetadataProcessor:
    """
    Handles AI-powered processing for knowledge graph ingestion.
    """
    
    def distill_and_classify_text(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Distill and classify raw text into atomic nodes.
        
        Args:
            raw_text: Raw text to process
            
        Returns:
            List of classified nodes
        """
        print("  -> 🧠 Usando Destilador Centralizado v2.0...")
        destilador_prompt = get_file_content("quantex/core/knowledge_graph/destilador_y_clasificador.txt")
        if not destilador_prompt: 
            return []
        
        # CORRECCIÓN: Eliminamos 'sentiment' del esquema que le exigimos a la IA.
        output_schema = {
            "type": "object", "properties": { 
                "classified_nodes": { "type": "array", "items": { 
                    "type": "object", 
                    "properties": { 
                        "title": {"type": "string"}, 
                        "content": {"type": "string"},
                        "ai_summary": {"type": "string"},
                        "doc_type": {"type": "string"},
                        "categories": {"type": "array", "items": {"type": "string"}},
                        "key_entities": {"type": "array", "items": {"type": "string"}}
                    }, 
                    "required": ["title", "content", "ai_summary", "doc_type", "categories", "key_entities"] 
                }}
            }, "required": ["classified_nodes"]
        }
        
        response = llm_manager.generate_structured_output(
            system_prompt=destilador_prompt.replace('{source_data}', raw_text),
            user_prompt="Destila el texto en el formato JSON requerido.",
            model_name=llm_manager.MODEL_CONFIG['simple']['primary'],
            output_schema=output_schema
        )
        if response and "classified_nodes" in response:
            nodes = response["classified_nodes"]
            print(f"    -> ✅ Destilador extrajo {len(nodes)} nodos enriquecidos.")
            return nodes
        return []
        
    def extract_entities_from_text(self, text: str) -> List[str]:
        """
        Extract key entities from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        # TODO: Implement entity extraction
        pass
        
    def categorize_content(self, content: str) -> List[str]:
        """
        Categorize content into relevant categories.
        
        Args:
            content: Content to categorize
            
        Returns:
            List of relevant categories
        """
        # TODO: Implement content categorization
        pass
        
    def generate_content_summary(self, content: str) -> str:
        """
        Generate AI summary of content.
        
        Args:
            content: Content to summarize
            
        Returns:
            Generated summary
        """
        # TODO: Implement content summarization
        pass

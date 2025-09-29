# quantex/core/knowledge_graph/ingestion_engine.py
"""
Central Knowledge Graph Ingestion Engine
Main entry point for all knowledge graph ingestion operations
"""

import uuid
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from quantex.core.ai_services import ai_services
from .node_manager import NodeManager
from .edge_manager import EdgeManager
from .metadata_manager import MetadataManager
from .ai_processors import AIMetadataProcessor
from .archivist import IntelligentArchivist


class KnowledgeGraphIngestionEngine:
    """
    Central ingestion engine for the knowledge graph.
    Provides unified interface for all ingestion operations.
    """
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.edge_manager = EdgeManager()
        self.metadata_manager = MetadataManager()
        self.ai_processor = AIMetadataProcessor()
        self.archivist = IntelligentArchivist()
        
    def ingest_document(self, raw_text: str, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge graph.
        Maintains EXACT same structure as process_and_store_knowledge()
        
        Args:
            raw_text: Raw text content to ingest
            source_context: Context about the source (source, topic, url, etc.)
            
        Returns:
            Dict with ingestion results and node IDs created
        """
        print(f"--- 🏭 Iniciando Línea de Ensamblaje (Modo Grafo) para fuente: {source_context.get('source')} ---")
        
        try:
            # Determine vectorization policy
            source_type = (source_context.get("source_type") or "").strip()
            index_to_pinecone = source_context.get("index_to_pinecone")
            if index_to_pinecone is None:
                # Default: do NOT index briefings or extracted learnings unless explicitly enabled
                index_to_pinecone = source_type not in ["Briefing_Estratégico", "Briefing_Estratégico_Completo", "Aprendizajes_Extraídos"]

            # Permitir desactivar vectorización de noticias/externo por env
            disable_news_vec = os.environ.get("QUANTEX_DISABLE_NEWS_VECTORIZATIONS", "").lower() in ["1", "true", "yes"]
            if disable_news_vec and source_type in ["Noticia", "Artículo", "Web", "RSS"]:
                index_to_pinecone = False
            
            print(f"  -> 🔍 [VECTORIZACIÓN] source_type: '{source_type}', index_to_pinecone: {index_to_pinecone}")
            
            # Special handling for complete briefings - keep as single unit
            if source_type == "Briefing_Estratégico_Completo":
                print("  -> 🎯 [BRIEFING COMPLETO] Manteniendo como unidad coherente (sin fragmentación)")
                # Create a single node with the complete dialogue
                atomic_nodes = [{
                    "type": "Documento",
                    "content": raw_text,
                    "metadata": {
                        "source_type": "Briefing_Estratégico_Completo",
                        "dialogue_format": "structured_complete",
                        "session_length": source_context.get("session_length", 0)
                    }
                }]
            else:
                # Step 1: Distill and classify text using AI (normal fragmentation)
                atomic_nodes = self.ai_processor.distill_and_classify_text(raw_text)
            
            if not atomic_nodes:
                print("  -> 🔴 El procesador no encontró nodos para guardar.")
                return {"success": False, "reason": "No nodes found"}

            print(f"  -> 💾 Procesando y guardando {len(atomic_nodes)} nodo(s) y sus conexiones...")
            
            created_nodes = []
            
            for node_obj in atomic_nodes:
                node_content = node_obj.get("content")
                if not node_content: 
                    continue

                # Step 2: Process metadata
                document_metadata = self.metadata_manager.process_document_metadata(
                    node_content, source_context, node_obj
                )

                # Step 3: Create document node in Supabase
                document_node_id = self.node_manager.create_document_node(node_content, document_metadata)

                # Step 4: Store in Pinecone (optional)
                if index_to_pinecone and ai_services.pinecone_index is not None:
                    print(f"  -> 🌲 [PINEONE] Indexando nodo en Pinecone...")
                    encoded = ai_services.embedding_model.encode(node_content)
                    # Aceptar ndarray o list
                    try:
                        vector = encoded.tolist() if hasattr(encoded, "tolist") else (encoded if isinstance(encoded, list) else [float(x) for x in encoded])
                    except Exception:
                        # Fallback defensivo a lista plana
                        import numpy as np
                        vector = np.array(encoded, dtype=float).flatten().tolist()
                    
                    # Obtener timestamp del contexto o usar timestamp actual
                    timestamp_iso = source_context.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    created_at_iso = datetime.now(timezone.utc).isoformat()
                    
                    # Convertir timestamps a Unix para Pinecone
                    try:
                        if isinstance(timestamp_iso, str):
                            dt = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
                            timestamp_unix = int(dt.timestamp())
                        else:
                            timestamp_unix = timestamp_iso
                    except:
                        timestamp_unix = int(datetime.now(timezone.utc).timestamp())
                    
                    try:
                        dt = datetime.fromisoformat(created_at_iso.replace('Z', '+00:00'))
                        created_at_unix = int(dt.timestamp())
                    except:
                        created_at_unix = int(datetime.now(timezone.utc).timestamp())
                    
                    metadata_for_pinecone = {
                        "source": source_context.get("source", ""),
                        "source_type": source_context.get("source_type", ""),
                        "topic": source_context.get("topic", ""),
                        "original_url": source_context.get("original_url", ""),
                        "categories": node_obj.get("categories", []),
                        "key_entities": node_obj.get("key_entities", []),
                        "text_snippet": node_content[:500],
                        "timestamp": timestamp_unix,
                        "created_at": created_at_unix,
                        "timestamp_iso": timestamp_iso,
                        "created_at_iso": created_at_iso,
                        "node_type": "Documento"
                    }
                    ai_services.pinecone_index.upsert(vectors=[{
                        "id": document_node_id, "values": vector, "metadata": metadata_for_pinecone
                    }])
                    print(f"    -> 🌲 Nodo indexado en Pinecone.")
                else:
                    print("    -> ⏭️  Vectorización desactivada para este nodo (no indexado en Pinecone).")

                # Step 5: Create entity nodes and connections
                entities = node_obj.get("key_entities", [])
                entity_ids = []
                
                if entities:
                    for entity_name in entities:
                        entity_id = self.node_manager.create_entity_node(entity_name)
                        if entity_id:
                            entity_ids.append(entity_id)

                # Step 6: Create document-entity edges
                if entity_ids:
                    self.edge_manager.create_document_entity_edges(document_node_id, entity_ids)

                # Step 7: Run Archivista Inteligente for semantic connections
                if index_to_pinecone and ai_services.pinecone_index is not None:
                    print(f"    -> 🤖 [Archivista] Analizando conexiones semánticas...")
                    try:
                        archivist_result = self.archivist.analyze_semantic_connections(
                            new_node_id=document_node_id,
                            new_node_content=node_content
                        )
                        if archivist_result.get("success"):
                            print(f"    -> ✅ [Archivista] {archivist_result.get('connections_created', 0)} conexiones semánticas creadas.")
                        else:
                            print(f"    -> ⚠️  [Archivista] {archivist_result.get('reason', 'Error desconocido')}")
                    except Exception as e:
                        print(f"    -> ⚠️  [Archivista] Error en conexiones semánticas: {e}")

                created_nodes.append({
                    "node_id": document_node_id,
                    "type": "Documento",
                    "entities": entity_ids
                })

                # Small delay like in original
                time.sleep(1)

            return {
                "success": True,
                "nodes_created": len(created_nodes),
                "nodes": created_nodes
            }

        except Exception as e:
            print(f"--- ❌ Error Crítico en la Línea de Ensamblaje: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        
    def ingest_learning(self, topic: str, learnings: List[str]) -> Dict[str, Any]:
        """
        Ingest learning nodes into the knowledge graph.
        
        Args:
            topic: Main topic for the learnings
            learnings: List of learning texts
            
        Returns:
            Dict with ingestion results and node IDs created
        """
        # TODO: Implement learning ingestion logic
        # This will replace save_learnings_to_knowledge_graph()
        pass
        
    def ingest_briefing(self, topic: str, briefing_content: str) -> Dict[str, Any]:
        """
        Ingest a briefing node into the knowledge graph.
        
        Args:
            topic: Topic for the briefing
            briefing_content: Briefing content
            
        Returns:
            Dict with ingestion results and node ID created
        """
        # TODO: Implement briefing ingestion logic
        # This will replace save_briefing_node()
        pass

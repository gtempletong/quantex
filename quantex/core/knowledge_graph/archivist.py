"""
Archivista Inteligente - Sistema Centralizado
Crea conexiones semánticas automáticas entre nodos del grafo de conocimiento
"""

import time
from typing import List, Dict, Any
from quantex.core import llm_manager
from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services


class IntelligentArchivist:
    """
    Archivista Inteligente - Crea conexiones semánticas automáticas entre nodos
    Versión optimizada con batching de LLM calls
    """
    
    def __init__(self):
        self.llm_manager = llm_manager
        self.db = db
        # ai_services es un módulo, no una instancia
    
    def analyze_semantic_connections(self, new_node_id: str, new_node_content: str) -> Dict[str, Any]:
        """
        Analiza y crea conexiones semánticas para un nuevo nodo
        
        Args:
            new_node_id: ID del nodo nuevo
            new_node_content: Contenido del nodo nuevo
            
        Returns:
            Dict con estadísticas de conexiones creadas
        """
        if not new_node_content:
            print(f"  -> ⏭️  SALTANDO nodo {new_node_id[:8]}... Contenido vacío.")
            return {"success": False, "reason": "Empty content"}
        
        print(f"  -> 🤖 [Archivista Inteligente] Analizando conexiones para el nuevo nodo {new_node_id[:8]}...")
        
        try:
            # ETAPA 1: Búsqueda semántica
            relevant_node_ids = self._find_semantically_similar_nodes(new_node_content)
            
            if not relevant_node_ids:
                print("    -> No se encontraron nodos semánticamente similares para conectar.")
                self._mark_node_as_reviewed(new_node_id, "No se encontraron nodos semánticamente similares para conectar.")
                return {"success": True, "connections_created": 0, "reason": "No similar nodes found"}
            
            print(f"    -> Encontrados {len(relevant_node_ids)} nodos potencialmente relacionados.")
            
            # ETAPA 2: Análisis batch optimizado
            edges_created_count = self._analyze_connections_batch(new_node_id, new_node_content, relevant_node_ids)
            
            # ETAPA 3: Marcar como revisado si no hay conexiones
            if edges_created_count == 0:
                print("    -> ✍️  [Archivista] Nodo analizado pero sin conexiones relevantes. Marcando como 'revisado'.")
                self._mark_node_as_reviewed(new_node_id, "El agente archivista revisó este nodo y no encontró conexiones de valor.")
            
            print("  -> ✅ [Archivista Inteligente] Proceso para este nodo finalizado.")
            return {"success": True, "connections_created": edges_created_count}
            
        except Exception as e:
            print(f"  -> ❌ Error en el Archivista Inteligente: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _find_semantically_similar_nodes(self, content: str) -> List[str]:
        """Encuentra nodos semánticamente similares usando Pinecone"""
        try:
            # Usar ai_services directamente como módulo (igual que en ingestion_engine.py)
            query_embedding = ai_services.embedding_model.encode(content).tolist()
            search_results = ai_services.pinecone_index.query(
                vector=query_embedding, 
                top_k=6, 
                include_metadata=False
            )
            relevant_node_ids = [match['id'] for match in search_results['matches']]
            return relevant_node_ids
        except Exception as e:
            print(f"    -> ❌ Error en búsqueda semántica: {e}")
            return []
    
    def _analyze_connections_batch(self, new_node_id: str, new_node_content: str, relevant_node_ids: List[str]) -> int:
        """
        Análisis optimizado con batching de LLM calls
        """
        print("    -> 🚀 [OPTIMIZADO] Analizando todas las conexiones en una sola llamada al LLM...")
        
        # Obtener contenido de todos los nodos existentes
        existing_nodes_data = self._get_existing_nodes_content(relevant_node_ids)
        
        if not existing_nodes_data:
            print("    -> ⚠️ No se encontró contenido para los nodos relacionados.")
            return 0
        
        # Crear prompt batch optimizado
        batch_prompt = self._create_batch_prompt(new_node_content, existing_nodes_data)
        
        # UNA SOLA llamada al LLM para todos los nodos
        batch_output_schema = {
            "type": "object",
            "properties": {
                "connections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "node_index": {"type": "integer"},
                            "relationship_type": {"type": "string"},
                            "justification": {"type": "string"}
                        },
                        "required": ["node_index", "relationship_type", "justification"]
                    }
                }
            },
            "required": ["connections"]
        }
        
        try:
            batch_relationship_data = self.llm_manager.generate_structured_output(
                system_prompt=None,
                user_prompt=batch_prompt,
                model_name=self.llm_manager.MODEL_CONFIG['simple']['primary'],
                output_schema=batch_output_schema
            )
            
            # Procesar resultados del batch
            return self._process_batch_results(new_node_id, existing_nodes_data, batch_relationship_data)
            
        except Exception as e:
            print(f"    -> ⚠️ Error en análisis batch: {e}")
            print("    -> 🔄 Volviendo a método individual...")
            return self._analyze_connections_individual(new_node_id, new_node_content, relevant_node_ids)
    
    def _get_existing_nodes_content(self, node_ids: List[str]) -> List[Dict[str, str]]:
        """Obtiene el contenido de los nodos existentes"""
        existing_nodes_data = []
        for existing_node_id in node_ids:
            try:
                response = self.db.supabase.table('nodes').select('id, label').eq('id', existing_node_id).execute()
                if response.data and len(response.data) > 0 and response.data[0].get('label'):
                    existing_nodes_data.append({
                        'id': existing_node_id,
                        'content': response.data[0]['label']
                    })
            except Exception as e:
                print(f"    -> ⚠️ Error obteniendo nodo {existing_node_id[:8]}: {e}")
                continue
        return existing_nodes_data
    
    def _create_batch_prompt(self, new_node_content: str, existing_nodes_data: List[Dict[str, str]]) -> str:
        """Crea el prompt batch optimizado"""
        batch_prompt = f"""Tu rol es ser un Analista de Inteligencia experto. Analiza las conexiones entre un documento nuevo y varios documentos existentes.

DOCUMENTO NUEVO:
{new_node_content[:4000]}

DOCUMENTOS EXISTENTES:
"""
        
        for i, node_data in enumerate(existing_nodes_data, 1):
            batch_prompt += f"""
{i}. ID: {node_data['id'][:8]}...
   Contenido: {node_data['content'][:2000]}
"""
        
        batch_prompt += """
Para cada documento existente, determina su relación con el documento nuevo:
- "confirma": El documento existente confirma información del nuevo
- "contradice": El documento existente contradice información del nuevo  
- "expande": El documento existente expande o profundiza en temas del nuevo
- "causa_efecto": Hay relación de causa y efecto entre los documentos
- "referencia": Los documentos se refieren a temas similares
- "irrelevante": No hay relación significativa

Responde en formato JSON con una justificación breve para cada conexión.
"""
        return batch_prompt
    
    def _process_batch_results(self, new_node_id: str, existing_nodes_data: List[Dict[str, str]], batch_data: Dict) -> int:
        """Procesa los resultados del análisis batch"""
        edges_created_count = 0
        
        if batch_data and "connections" in batch_data:
            for connection in batch_data["connections"]:
                node_index = connection.get("node_index", 0)
                relationship_type = connection.get("relationship_type", "irrelevante")
                justification = connection.get("justification", "")
                
                # Validar índice
                if 0 <= node_index < len(existing_nodes_data):
                    existing_node_id = existing_nodes_data[node_index]['id']
                    
                    if relationship_type != 'irrelevante':
                        print(f"    -> 🔗 Creando conexión: ({new_node_id[:8]}) -[{relationship_type}]-> ({existing_node_id[:8]})")
                        self.db.create_knowledge_edge(
                            source_node_id=new_node_id,
                            target_node_id=existing_node_id,
                            relationship_type=relationship_type,
                            metadata={"justification": justification}
                        )
                        edges_created_count += 1
                        print("        -> ✅ Conexión guardada exitosamente.")
        
        return edges_created_count
    
    def _analyze_connections_individual(self, new_node_id: str, new_node_content: str, relevant_node_ids: List[str]) -> int:
        """Método fallback individual si el batch falla"""
        edges_created_count = 0
        
        for existing_node_id in relevant_node_ids:
            try:
                response = self.db.supabase.table('nodes').select('label').eq('id', existing_node_id).execute()
                if not response.data or not response.data[0].get('label'):
                    continue
                
                existing_node_content = response.data[0]['label']
                simple_prompt = f"""Analiza la relación entre estos dos documentos:
Nuevo: {new_node_content[:2000]}
Existente: {existing_node_content[:2000]}

Relación: "confirma", "expande", "referencia", o "irrelevante"
Justificación: breve explicación"""

                relationship_data = self.llm_manager.generate_structured_output(
                    system_prompt=None,
                    user_prompt=simple_prompt,
                    model_name=self.llm_manager.MODEL_CONFIG['simple']['primary'],
                    output_schema={
                        "type": "object", "properties": {
                            "relationship_type": {"type": "string"}, "justification": {"type": "string"}
                        }, "required": ["relationship_type", "justification"]
                    }
                )

                if relationship_data and relationship_data.get('relationship_type') != 'irrelevante':
                    print(f"    -> 🔗 Creando conexión: ({new_node_id[:8]}) -[{relationship_data['relationship_type']}]-> ({existing_node_id[:8]})")
                    self.db.create_knowledge_edge(
                        source_node_id=new_node_id,
                        target_node_id=existing_node_id,
                        relationship_type=relationship_data['relationship_type'],
                        metadata={"justification": relationship_data.get('justification', '')}
                    )
                    edges_created_count += 1
                    print("        -> ✅ Conexión guardada exitosamente.")
                    
            except Exception as e:
                print(f"    -> ⚠️ Error procesando nodo {existing_node_id[:8]}: {e}")
                continue
        
        return edges_created_count
    
    def _mark_node_as_reviewed(self, node_id: str, justification: str):
        """Marca un nodo como revisado sin conexiones"""
        try:
            self.db.create_knowledge_edge(
                source_node_id=node_id,
                target_node_id=node_id,
                relationship_type='revisado_sin_accion',
                metadata={"justification": justification}
            )
        except Exception as e:
            print(f"    -> ⚠️ Error marcando nodo como revisado: {e}")


# Función de conveniencia para mantener compatibilidad
def run_intelligent_archivist_agent(new_node_id: str, new_node_content: str) -> Dict[str, Any]:
    """
    Función de conveniencia para mantener compatibilidad con el código existente
    """
    archivist = IntelligentArchivist()
    return archivist.analyze_semantic_connections(new_node_id, new_node_content)

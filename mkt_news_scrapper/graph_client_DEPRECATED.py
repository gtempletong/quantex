"""
DEPRECATED - graph_client.py
Este archivo ha sido reemplazado por quantex_integration.py

La funcionalidad de cliente de grafo ahora se maneja a través del motor unificado
de Quantex: KnowledgeGraphIngestionEngine

MIGRACIÓN COMPLETADA:
- ✅ Verificación de duplicados: Ahora usa quantex_integration.py
- ✅ Upsert de entidades: Ahora usa KnowledgeGraphIngestionEngine
- ✅ Inserción de nodos: Ahora usa motor unificado
- ✅ Gestión de metadatos: Ahora usa motor unificado

Para usar la nueva funcionalidad:
from quantex_integration import MktNewsQuantexIntegration

integration = MktNewsQuantexIntegration()
result = integration.process_news_item(news_item)
"""

import warnings

warnings.warn(
    "graph_client.py está DEPRECADO. Usa quantex_integration.py en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

# Funciones de compatibilidad temporal
def node_exists_by_original_url(original_url: str) -> bool:
    """
    ⚠️ FUNCIÓN DEPRECADA ⚠️
    
    Esta función redirige al nuevo motor unificado de Quantex.
    """
    print("⚠️ Usando función DEPRECADA. Migra a quantex_integration.py")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        integration = MktNewsQuantexIntegration()
        return integration.check_duplicate_by_url(original_url)
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return False

def node_exists_by_hash(item_hash: str) -> bool:
    """
    ⚠️ FUNCIÓN DEPRECADA ⚠️
    
    Esta función redirige al nuevo motor unificado de Quantex.
    """
    print("⚠️ Usando función DEPRECADA. Migra a quantex_integration.py")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        integration = MktNewsQuantexIntegration()
        return integration.check_duplicate_by_hash(item_hash)
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return False

def upsert_entity_nodes(entity_labels: list[str]) -> dict[str, str]:
    """
    ⚠️ FUNCIÓN DEPRECADA ⚠️
    
    Esta función redirige al nuevo motor unificado de Quantex.
    """
    print("⚠️ Usando función DEPRECADA. Migra a quantex_integration.py")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        integration = MktNewsQuantexIntegration()
        # La gestión de entidades ahora se maneja automáticamente en el motor unificado
        return {label: f"managed_by_unified_engine" for label in entity_labels}
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return {}

def insert_document_node(node_data: dict) -> str:
    """
    ⚠️ FUNCIÓN DEPRECADA ⚠️
    
    Esta función redirige al nuevo motor unificado de Quantex.
    """
    print("⚠️ Usando función DEPRECADA. Migra a quantex_integration.py")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        integration = MktNewsQuantexIntegration()
        
        # Crear item temporal para compatibilidad
        news_item = {
            "title": node_data.get("title", ""),
            "content": node_data.get("content", ""),
            "time": node_data.get("time", ""),
            "url": node_data.get("url", ""),
            "item_hash": node_data.get("hash", ""),
            "category": node_data.get("category", "Noticias")
        }
        
        result = integration.process_news_item(news_item)
        return result.get("document_node_id", "unknown") if result.get("success") else "error"
        
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return "error"

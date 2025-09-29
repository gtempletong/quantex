"""
DEPRECATED - llm_destiller.py
Este archivo ha sido reemplazado por quantex_integration.py

La funcionalidad de destilación ahora se maneja a través del motor unificado
de Quantex: KnowledgeGraphIngestionEngine

MIGRACIÓN COMPLETADA:
- ✅ Destilación: Ahora usa quantex_integration.py
- ✅ Clasificación: Ahora usa KnowledgeGraphIngestionEngine
- ✅ Ingesta al grafo: Ahora usa motor unificado
- ✅ Conexiones semánticas: Ahora usa Archivista Inteligente

Para usar la nueva funcionalidad:
from quantex_integration import MktNewsQuantexIntegration

integration = MktNewsQuantexIntegration()
result = integration.process_news_item(news_item)
"""

import warnings

warnings.warn(
    "llm_destiller.py está DEPRECADO. Usa quantex_integration.py en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

# Función de compatibilidad temporal
def distill_and_classify_text(raw_text: str) -> list:
    """
    ⚠️ FUNCIÓN DEPRECADA ⚠️
    
    Esta función redirige al nuevo motor unificado de Quantex.
    """
    print("⚠️ Usando función DEPRECADA. Migra a quantex_integration.py")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        
        # Crear item temporal para compatibilidad
        news_item = {
            "title": "Item de compatibilidad",
            "content": raw_text,
            "time": "",
            "url": "",
            "item_hash": "",
            "category": "Compatibilidad"
        }
        
        integration = MktNewsQuantexIntegration()
        result = integration.process_news_item(news_item)
        
        if result.get("success"):
            # Retornar formato compatible
            return [{"title": "Procesado", "content": raw_text, "ai_summary": "Procesado por motor unificado", "doc_type": "Noticia", "categories": ["Noticias"], "key_entities": []}]
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return []

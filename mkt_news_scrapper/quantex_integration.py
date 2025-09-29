"""
MktNewsScraper - Integración con Quantex Knowledge Graph
Reemplaza llm_destiller.py y graph_client.py con el motor unificado
"""

import os
import sys
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine
    from quantex.core import database_manager as db
    from quantex.core.ai_services import ai_services
    
    # Inicializar servicios de AI
    print("🔧 Inicializando servicios de AI...")
    ai_services.initialize()
    print("✅ Servicios de AI inicializados")
    
except ImportError as e:
    print(f"❌ Error importando Quantex: {e}")
    print("Asegúrate de que Quantex esté correctamente configurado")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inicializando servicios de AI: {e}")
    print("Verifica que las variables de entorno estén configuradas")
    sys.exit(1)

class MktNewsQuantexIntegration:
    """
    Integración de MktNewsScraper con el motor unificado de Quantex
    """
    
    def __init__(self):
        self.ingestion_engine = KnowledgeGraphIngestionEngine()
        self.db = db
    
    def check_duplicate_by_url(self, original_url: str) -> bool:
        """Verifica si ya existe un documento con la misma URL"""
        if not original_url:
            return False
        
        try:
            result = self.db.supabase.table('nodes') \
                .select('id', count='exact') \
                .eq('type', 'Documento') \
                .eq('properties->>original_url', original_url.strip()) \
                .execute()
            
            return (result.count or 0) > 0
        except Exception as e:
            print(f"⚠️ Error verificando duplicado por URL: {e}")
            return False
    
    def check_duplicate_by_hash(self, item_hash: str) -> bool:
        """Verifica si ya existe un documento con el mismo hash"""
        if not item_hash:
            return False
        
        try:
            result = self.db.supabase.table('nodes') \
                .select('id', count='exact') \
                .eq('type', 'Documento') \
                .eq('properties->>hash', item_hash) \
                .execute()
            
            return (result.count or 0) > 0
        except Exception as e:
            print(f"⚠️ Error verificando duplicado por hash: {e}")
            return False
    
    def process_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un item de noticia usando el motor unificado de Quantex
        
        Args:
            news_item: Dict con 'title', 'content', 'time', 'url', 'item_hash'
        
        Returns:
            Dict con resultado de la ingesta
        """
        try:
            print(f"  -> 📰 Procesando: {news_item.get('title', 'Sin título')[:50]}...")
            
            # Verificar duplicados
            if self.check_duplicate_by_url(news_item.get('url', '')):
                print(f"    -> ⚠️ Duplicado por URL detectado, saltando...")
                return {"success": False, "reason": "Duplicate by URL"}
            
            if self.check_duplicate_by_hash(news_item.get('item_hash', '')):
                print(f"    -> ⚠️ Duplicado por hash detectado, saltando...")
                return {"success": False, "reason": "Duplicate by hash"}
            
            # Preparar contenido combinado
            content = self._prepare_content(news_item)
            
            # Preparar contexto de fuente
            source_context = {
                "source": "MktNewsScraper",
                "topic": news_item.get('category', 'Noticias Financieras'),
                "source_type": "Noticia_Scrapeada",
                "original_url": news_item.get('url', ''),
                "hash": news_item.get('item_hash', ''),
                "scraped_time": news_item.get('time', ''),
                "scraper_version": "v2.0_quantex_integrated"
            }
            
            # Usar el motor unificado de Quantex
            result = self.ingestion_engine.ingest_document(content, source_context)
            
            if result.get("success"):
                print(f"    -> ✅ {result.get('nodes_created', 0)} nodo(s) creado(s) con conexiones semánticas.")
            else:
                print(f"    -> ❌ Error en ingesta: {result.get('reason', 'Desconocido')}")
            
            return result
            
        except Exception as e:
            print(f"    -> ❌ Error procesando item: {e}")
            return {"success": False, "error": str(e)}
    
    def _prepare_content(self, news_item: Dict[str, Any]) -> str:
        """Prepara el contenido combinado para la ingesta"""
        title = news_item.get('title', 'Sin título')
        content = news_item.get('content', '')
        time = news_item.get('time', '')
        
        # Formato estructurado para mejor procesamiento
        structured_content = f"""
# {title}

**Fuente:** MktNews.net  
**Tiempo:** {time}  
**Categoría:** {news_item.get('category', 'Noticias Financieras')}

## Contenido:
{content}
"""
        
        return structured_content.strip()
    
    def process_multiple_items(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Procesa múltiples items de noticias
        
        Args:
            news_items: Lista de items de noticias
        
        Returns:
            Dict con resumen del procesamiento
        """
        print(f"🚀 Procesando {len(news_items)} items de noticias con motor unificado...")
        
        results = {
            "total_items": len(news_items),
            "successful": 0,
            "failed": 0,
            "duplicates": 0,
            "errors": []
        }
        
        for i, item in enumerate(news_items, 1):
            print(f"📰 [{i}/{len(news_items)}] Procesando item...")
            
            result = self.process_news_item(item)
            
            if result.get("success"):
                results["successful"] += 1
            elif result.get("reason") in ["Duplicate by URL", "Duplicate by hash"]:
                results["duplicates"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(result.get("error", result.get("reason", "Unknown")))
        
        print(f"\n📊 Resumen del procesamiento:")
        print(f"  -> ✅ Exitosos: {results['successful']}")
        print(f"  -> ⚠️ Duplicados: {results['duplicates']}")
        print(f"  -> ❌ Fallidos: {results['failed']}")
        
        return results

# Función de compatibilidad para reemplazar las funciones anteriores
def process_and_store_knowledge(raw_text: str, source_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de compatibilidad que reemplaza la función anterior
    """
    try:
        integration = MktNewsQuantexIntegration()
        
        # Crear un item de noticia temporal
        news_item = {
            "title": source_context.get("title", "Noticia"),
            "content": raw_text,
            "time": source_context.get("time", datetime.now().isoformat()),
            "url": source_context.get("original_url", ""),
            "item_hash": source_context.get("hash", ""),
            "category": source_context.get("topic", "Noticias")
        }
        
        return integration.process_news_item(news_item)
        
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return {"success": False, "error": str(e)}

# Función para verificar duplicados (compatibilidad)
def node_exists_by_original_url(original_url: str) -> bool:
    """Función de compatibilidad para verificar duplicados por URL"""
    try:
        integration = MktNewsQuantexIntegration()
        return integration.check_duplicate_by_url(original_url)
    except Exception as e:
        print(f"❌ Error verificando duplicado: {e}")
        return False

def node_exists_by_hash(item_hash: str) -> bool:
    """Función de compatibilidad para verificar duplicados por hash"""
    try:
        integration = MktNewsQuantexIntegration()
        return integration.check_duplicate_by_hash(item_hash)
    except Exception as e:
        print(f"❌ Error verificando duplicado: {e}")
        return False

if __name__ == "__main__":
    # Prueba básica de la integración
    print("🧪 Probando integración MktNewsScraper → Quantex...")
    
    integration = MktNewsQuantexIntegration()
    
    # Item de prueba
    test_item = {
        "title": "Prueba de Integración",
        "content": "Este es un contenido de prueba para verificar la integración con Quantex.",
        "time": datetime.now().isoformat(),
        "url": "https://example.com/test",
        "item_hash": hashlib.sha256("test".encode()).hexdigest(),
        "category": "Prueba"
    }
    
    result = integration.process_news_item(test_item)
    print(f"Resultado: {result}")

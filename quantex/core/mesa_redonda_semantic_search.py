"""
Motor de Búsqueda Semántica para Mesa Redonda
Versión 1.0 - Integración con report definitions
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.semantic_search_engine import get_semantic_engine
from quantex.core import database_manager as db

def get_semantic_news_for_report(report_keyword: str, days_ago: int = 2) -> Dict[str, List[str]]:
    """
    Obtiene noticias semánticamente relevantes para un informe específico
    
    Args:
        report_keyword: Tópico del informe (ej: 'cobre', 'clp')
        days_ago: Días hacia atrás para buscar
        
    Returns:
        Diccionario con noticias categorizadas por fuente
    """
    try:
        print(f"🔍 [Mesa Redonda Semantic] Buscando noticias para '{report_keyword}' (últimos {days_ago} días)")
        
        # Convertir días a meses (mínimo 1 mes para el motor)
        months = max(1, days_ago // 30)
        
        engine = get_semantic_engine()
        
        # Fuentes a buscar
        sources = ["MktNewsScraper", "SMM", "Autonomous_Researcher"]
        
        # Queries semánticas para cada fuente
        semantic_queries = {
            "MktNewsScraper": f"noticias recientes sobre {report_keyword} mercado financiero",
            "SMM": f"análisis {report_keyword} commodities metales",
            "Autonomous_Researcher": f"investigación {report_keyword} economía análisis"
        }
        
        results = {}
        
        for source in sources:
            print(f"  -> Buscando en {source}...")
            
            # Buscar con filtro de fuente
            source_results = engine.search_knowledge(
                query=semantic_queries[source],
                top_k=50,  # Más resultados para filtrar después
                months=months,
                filters={"source": source},
                include_connections=False
            )
            
            # Extraer contenido
            content_list = []
            for result in source_results:
                content = result.get('content', '')
                if content and len(content.strip()) > 50:  # Filtrar contenido muy corto
                    content_list.append(content)
            
            if content_list:
                results[f"noticias_{source.lower()}_{report_keyword.lower()}"] = content_list
                print(f"    -> ✅ Encontrados {len(content_list)} documentos")
            else:
                print(f"    -> ⚠️ No se encontraron documentos relevantes")
        
        print(f"✅ [Mesa Redonda Semantic] Total: {sum(len(v) for v in results.values())} documentos")
        return results
        
    except Exception as e:
        print(f"❌ [Mesa Redonda Semantic] Error: {e}")
        return {}

def enhance_dossier_curator_with_semantic_search(report_keyword: str, report_def: dict) -> Dict[str, List[str]]:
    """
    Enriquece el curador de dossier con búsqueda semántica
    
    Args:
        report_keyword: Tópico del informe
        report_def: Definición del informe
        
    Returns:
        Diccionario con contenido semántico adicional
    """
    try:
        print(f"🧠 [Dossier Curator Enhancement] Enriqueciendo con búsqueda semántica para '{report_keyword}'")
        
        # Obtener fuentes tácticas del report definition
        tactical_sources = report_def.get('fuentes_tacticas', [])
        
        if not tactical_sources:
            print("  -> ⚠️ No hay fuentes tácticas configuradas")
            return {}
        
        # Buscar contenido semántico para cada fuente
        semantic_content = {}
        
        for source_config in tactical_sources:
            source_name = source_config.get('source')
            topic = source_config.get('topic', report_keyword)
            days_ago = source_config.get('days_ago', 2)
            
            if not source_name:
                continue
            
            print(f"  -> Buscando semánticamente: {source_name} + {topic}")
            
            # Búsqueda semántica
            months = max(1, days_ago // 30)
            
            engine = get_semantic_engine()
            results = engine.search_knowledge(
                query=f"análisis reciente {topic} {source_name}",
                top_k=30,
                months=months,
                filters={"source": source_name},
                include_connections=False
            )
            
            # Extraer contenido
            content_list = []
            for result in results:
                content = result.get('content', '')
                if content and len(content.strip()) > 50:
                    content_list.append(content)
            
            if content_list:
                key = f"noticias_{source_name.lower()}_{topic.lower()}"
                semantic_content[key] = content_list
                print(f"    -> ✅ {len(content_list)} documentos semánticos encontrados")
        
        return semantic_content
        
    except Exception as e:
        print(f"❌ [Dossier Curator Enhancement] Error: {e}")
        return {}

def get_cross_topic_semantic_insights(report_keyword: str, days_ago: int = 2) -> List[str]:
    """
    Obtiene insights semánticos cruzados (conexiones entre tópicos)
    
    Args:
        report_keyword: Tópico principal
        days_ago: Días hacia atrás
        
    Returns:
        Lista de insights cruzados
    """
    try:
        print(f"🔗 [Cross-Topic Insights] Buscando conexiones para '{report_keyword}'")
        
        months = max(1, days_ago // 30)
        engine = get_semantic_engine()
        
        # Buscar conexiones semánticas amplias
        results = engine.search_knowledge(
            query=f"análisis conexiones {report_keyword} economía global mercados",
            top_k=20,
            months=months,
            filters=None,
            include_connections=True
        )
        
        insights = []
        for result in results:
            # Extraer insights de contenido rico
            content = result.get('content', '')
            if len(content) > 200 and result.get('connections', 0) > 3:
                insights.append(content)
        
        print(f"✅ [Cross-Topic Insights] {len(insights)} insights cruzados encontrados")
        return insights
        
    except Exception as e:
        print(f"❌ [Cross-Topic Insights] Error: {e}")
        return []

if __name__ == "__main__":
    # Prueba del sistema
    print("🧪 Probando Motor Semántico para Mesa Redonda...")
    
    # Prueba 1: Búsqueda para cobre
    results = get_semantic_news_for_report("cobre", days_ago=2)
    print(f"Resultados para cobre: {len(results)} categorías")
    
    # Prueba 2: Insights cruzados
    insights = get_cross_topic_semantic_insights("cobre", days_ago=2)
    print(f"Insights cruzados: {len(insights)}")

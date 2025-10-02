# quantex/pipelines/knowledge/source_monitor.py (Versión 14.0 - FXStreet Integrado)
import os
import sys
import time
import feedparser
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
# Imports eliminados: numpy, cosine_similarity - IA detecta duplicados semánticos

# Desactivar logging de httpx para evitar spam de consultas HTTP
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Lógica de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importaciones de Quantex (Centralizadas) ---
from quantex.core import database_manager as db
from quantex.core.web_tools import get_firecrawl_scrape
from quantex.core.ai_services import ai_services
from quantex.core import agent_tools
from quantex.core.knowledge_graph.ingestion_engine import KnowledgeGraphIngestionEngine
from quantex.core.config_loader import get_config_loader
from quantex.core.llm_manager import generate_completion

# --- Clases de Screening Inteligente ---

class NewsScreeningAgent:
    """
    Agente de screening inteligente para evaluar relevancia de noticias
    """
    
    def __init__(self, commodity: str, keywords: List[str]):
        self.commodity = commodity
        self.keywords = keywords
        self.ai_service = ai_services
    
    def screen_with_full_context(self, title: str, summary: str, url: str, source: str,
                                feed_similarity: float, historical_similarity: float,
                                similar_titles: List[str], feed_context: List[str]) -> Dict[str, Any]:
        """
        Screening completo con contexto de duplicados
        """
        prompt = f"""
Eres un experto en análisis de noticias financieras y de commodities. 
Evalúa la relevancia de esta noticia para el mercado de {self.commodity}.

CONTEXTO DEL FEED:
{feed_context[:5]}  # Primeras 5 noticias del feed

NOTICIA ACTUAL:
Título: {title}
Resumen: {summary}
URL: {url}
Fuente: {source}

ANÁLISIS DE DUPLICADOS:
- Similitud con noticias del feed: {feed_similarity:.2f}
- Similitud con noticias históricas: {historical_similarity:.2f}
- Títulos similares encontrados: {similar_titles[:3]}

CRITERIOS DE EVALUACIÓN:
1. **Novedad**: ¿Esta noticia aporta información nueva?
2. **Relevancia**: ¿Es relevante para {self.commodity}?
3. **Impacto**: ¿Puede afectar precios o mercado?
4. **Calidad**: ¿Es información confiable y detallada?

RESPUESTA REQUERIDA (JSON):
{{
    "relevant": true/false,
    "confidence": 0.0-1.0,
    "novelty_score": 0.0-1.0,
    "reasoning": "Explicación breve",
    "impact_level": "high/medium/low",
    "duplicate_analysis": {{
        "is_duplicate": true/false,
        "similarity_level": "high/medium/low",
        "new_information": "Qué información nueva aporta"
    }},
    "recommended_action": "scrape/ignore/monitor"
}}
"""
        
        try:
            # Importar el LLM manager para usar la función correcta
            from quantex.core.llm_manager import generate_completion
            
            # Usar generate_completion en lugar de chat_completion
            response = generate_completion(
                task_complexity="default",
                system_prompt="Eres un experto en análisis de noticias financieras y de commodities.",
                user_prompt=prompt
            )
            
            # Parsear respuesta JSON desde raw_text
            if 'raw_text' in response:
                decision = json.loads(response['raw_text'])
                return decision
            else:
                raise Exception(f"Respuesta inválida del LLM: {response}")
            
        except Exception as e:
            print(f"      ❌ Error en screening IA: {e}")
            # Fallback: usar filtro básico
            return self.fallback_screening(title, summary)
    
    def fallback_screening(self, title: str, summary: str) -> Dict[str, Any]:
        """
        Screening de fallback cuando falla la IA
        """
        text = f"{title} {summary}".lower()
        keyword_matches = sum(1 for keyword in self.keywords if keyword.lower() in text)
        
        relevant = keyword_matches > 0
        confidence = min(keyword_matches / len(self.keywords), 1.0)
        
        return {
            "relevant": relevant,
            "confidence": confidence,
            "novelty_score": 0.5,
            "reasoning": f"Fallback: {keyword_matches} keywords encontradas",
            "impact_level": "medium",
            "duplicate_analysis": {
                "is_duplicate": False,
                "similarity_level": "low",
                "new_information": "Análisis básico"
            },
            "recommended_action": "scrape" if relevant else "ignore"
        }
    
    def screen_with_full_content(self, title: str, summary: str, content: str, url: str, source: str,
                                feed_similarity: float, historical_similarity: float,
                                similar_titles: List[str], feed_context: List[str]) -> Dict[str, Any]:
        """
        Screening completo con contenido scrapeado
        """
        prompt = f"""
Eres un experto en análisis de noticias financieras y de commodities. 
Evalúa la relevancia de esta noticia para el mercado de {self.commodity}.

CONTENIDO COMPLETO DE LA NOTICIA:
Título: {title}
Resumen: {summary}
Contenido completo: {content[:2000]}...

URL: {url}
Fuente: {source}

ANÁLISIS DE DUPLICADOS:
- Similitud con noticias del feed: {feed_similarity:.2f}
- Similitud con noticias históricas: {historical_similarity:.2f}
- Títulos similares encontrados: {similar_titles[:3]}

CRITERIOS DE EVALUACIÓN:
1. **Novedad**: ¿Esta noticia aporta información nueva?
2. **Relevancia**: ¿Es relevante para {self.commodity}?
3. **Impacto**: ¿Puede afectar precios o mercado?
4. **Calidad**: ¿Es información confiable y detallada?

RESPUESTA REQUERIDA (JSON):
{{
    "relevant": true/false,
    "confidence": 0.0-1.0,
    "novelty_score": 0.0-1.0,
    "reasoning": "Explicación breve basada en el contenido completo",
    "impact_level": "high/medium/low",
    "duplicate_analysis": {{
        "is_duplicate": true/false,
        "similarity_level": "high/medium/low",
        "new_information": "Qué información nueva aporta"
    }},
    "recommended_action": "scrape/ignore/monitor"
}}
"""
        
        try:
            response = generate_completion(
                task_complexity="default",
                system_prompt="Eres un experto en análisis de noticias financieras y de commodities.",
                user_prompt=prompt
            )
            
            if 'raw_text' in response:
                try:
                    raw_text = response['raw_text'].strip()
                    if '{' in raw_text and '}' in raw_text:
                        start = raw_text.find('{')
                        end = raw_text.rfind('}') + 1
                        json_text = raw_text[start:end]
                        decision = json.loads(json_text)
                        return decision
                    else:
                        raise Exception("No se encontró JSON válido en la respuesta")
                except json.JSONDecodeError as e:
                    print(f"      ⚠️ Error parseando JSON: {e}")
                    print(f"      📝 Respuesta raw: {response['raw_text'][:200]}...")
                    raise Exception(f"Error parseando JSON: {e}")
            else:
                raise Exception(f"Respuesta inválida del LLM: {response}")
            
        except Exception as e:
            print(f"      ❌ Error en screening IA: {e}")
            return self.fallback_screening(title, summary)

# Función eliminada: calculate_semantic_similarity - IA detecta duplicados semánticos

def enhanced_prefilter(title: str, summary: str, keywords: List[str], filter_config: dict = None) -> bool:
    """
    Prefiltro mejorado con configuración desde YAML
    """
    text = f"{title} {summary}".lower()
    
    # Si no hay configuración, usar filtro básico
    if not filter_config:
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in text)
        return keyword_matches > 0
    
    # Obtener configuración del filtro
    specific_keywords = [kw.lower() for kw in filter_config.get('specific_keywords', [])]
    general_keywords = [kw.lower() for kw in filter_config.get('general_keywords', [])]
    exclude_keywords = [kw.lower() for kw in filter_config.get('exclude_keywords', [])]
    target_pairs = [pair.lower() for pair in filter_config.get('target_pairs', [])]
    filter_logic = filter_config.get('filter_logic', 'any_keyword')
    
    # 1. Verificar exclusiones primero
    if exclude_keywords:
        for exclude in exclude_keywords:
            if exclude in text:
                print(f"      ❌ Excluido por keyword: {exclude}")
                return False
    
    # 2. Verificar pares de divisas específicos
    if target_pairs:
        for pair in target_pairs:
            if pair in text:
                print(f"      ✅ Aprobado por par específico: {pair}")
                return True
    
    # 3. Aplicar lógica del filtro
    if filter_logic == "specific_or_general":
        # Debe tener al menos una divisa específica O ser forex general
        has_specific = any(currency in text for currency in specific_keywords)
        has_general = any(general in text for general in general_keywords)
        result = has_specific or has_general
        if result:
            print(f"      ✅ Aprobado por filtro específico/general")
        return result
    
    elif filter_logic == "all_specific":
        # Debe tener TODAS las keywords específicas
        result = all(currency in text for currency in specific_keywords)
        if result:
            print(f"      ✅ Aprobado por todas las keywords específicas")
        return result
    
    elif filter_logic == "any_keyword":
        # Cualquier keyword de la lista
        all_keywords = specific_keywords + general_keywords
        result = any(keyword in text for keyword in all_keywords)
        if result:
            print(f"      ✅ Aprobado por cualquier keyword")
        return result
    
    else:
        # Fallback: filtro básico
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in text)
        return keyword_matches > 0

# Función eliminada: analyze_feed_context - IA detecta duplicados semánticos

# Función eliminada: check_historical_duplicates
# Ahora usamos solo verificación de URL exacta para mayor eficiencia

def does_url_exist_in_db(url: str) -> bool:
    """
    Verifica si una URL específica ya existe en la base de datos (método 1 a 1)
    """
    try:
        if not url:
            return False
            
        # Query que funciona para verificar URL individual
        response = db.supabase.table('nodes') \
            .select('id') \
            .eq('type', 'Documento') \
            .eq('properties->>original_url', url) \
            .limit(1) \
            .execute()
        
        exists = len(response.data) > 0
        return exists
        
    except Exception as e:
        print(f"      ⚠️ Error verificando URL individual: {e}")
        return False

def get_existing_urls_batch(urls: List[str]) -> set:
    """
    (Versión Optimizada - Consulta Masiva Alternativa)
    Obtiene todas las URLs existentes en una sola consulta, filtrando en Python
    """
    try:
        if not urls:
            return set()
            
        # Query que SÍ funciona (con filtro NOT NULL)
        response = db.supabase.table('nodes') \
            .select('properties->>original_url') \
            .eq('type', 'Documento') \
            .not_.is_('properties->>original_url', 'null') \
            .execute()
        
        # Crear set de todas las URLs existentes
        all_existing_urls = set()
        for row in response.data:
            if row.get('original_url'):
                all_existing_urls.add(row['original_url'])
        
        print(f"      -> 🔍 URLs encontradas en DB: {len(all_existing_urls)}")
        
        # Filtrar solo las que están en el feed actual
        existing_urls = {url for url in all_existing_urls if url in urls}
        
        print(f"      -> 📊 Consulta masiva: {len(existing_urls)} URLs encontradas en DB de {len(urls)} del feed")
        
        # Debug: mostrar URLs duplicadas
        if existing_urls:
            print(f"      -> 🔍 URLs duplicadas encontradas:")
            for i, url in enumerate(list(existing_urls)[:3]):
                print(f"         {i+1}. {url[:80]}...")
        print(f"      -> 📋 Total documentos en DB: {len(all_existing_urls)}")
        
        return existing_urls
        
    except Exception as e:
        print(f"      ⚠️ Error en consulta masiva de URLs: {e}")
        return set()

def process_rss_feed(target: dict, ingestion_engine: KnowledgeGraphIngestionEngine):
    """
    (Versión 16.0 - Optimizado)
    Procesa un feed con eliminación de duplicados en lote para máxima eficiencia.
    """
    target_name = target.get('target_name', 'Desconocido')
    rss_url = target.get('source_url')
    
    print(f"\n--- 📰 Procesando Feed: {target_name} ---")
    if not rss_url: return

    # Obtener keywords del target
    filter_keywords = target.get('filter_keywords', [])
    commodity = target.get('commodity', 'copper')
    
    try:
        # 1. Cargar RSS feed completo
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print("  -> No se encontraron noticias en este feed.")
            return

        print(f"  📰 Feed cargado: {len(feed.entries)} noticias encontradas")
        
        # 2. Crear agente de screening
        screening_agent = NewsScreeningAgent(commodity, filter_keywords)
        
        # 3. Contadores para estadísticas
        new_articles_processed = 0
        skipped_prefilter = 0
        skipped_screening = 0
        skipped_existing = 0

        # 4. Procesar cada noticia individualmente (método 1 a 1 que funciona)
        for entry in feed.entries:
            entry_link = entry.get('link')
            title = entry.get('title', '')
            summary = entry.get('summary', '')

            # 4.1 Verificar si URL ya existe en DB (método 1 a 1)
            if entry_link:
                if does_url_exist_in_db(entry_link):
                    skipped_existing += 1
                    continue

            # 4.2 Prefiltro mejorado con keywords
            filter_config = target.get('filter_config')
            if not enhanced_prefilter(title, summary, target.get('filter_keywords', []), filter_config):
                skipped_prefilter += 1
                continue
            
            # Solo mostrar noticias que pasan el prefiltro
            print(f"    📰 Procesando: '{title[:60]}...'")
            
            # 4.3 Proceder con scrape (antes del screening)
            full_content_md = scrape_article_with_retries(entry_link)
            if not full_content_md:
                print(f"      ⏭️  Sin contenido tras scrapeo")
                continue
            
            # 4.4 OMITIR screening IA con contenido completo (política actual)
            print("      ⚠️ Screening IA omitido por política: se procederá a ingesta tras prefiltro.")
            screening_result = {
                "relevant": True,
                "confidence": 1.0,
                "novelty_score": 0.0,
                "impact_level": "unclassified"
            }
            
            # 4.6 Proceder con ingesta
            print(f"      ✅ Aprobado: {screening_result['impact_level']} impact")
            new_articles_processed += 1
            
            try:
                source_context = {
                    "source": target.get('publisher', target_name),
                    "topic": target.get('target_name'),
                    "source_type": "Noticia Continua",
                    "original_url": entry_link,
                    "screening_score": screening_result['confidence'],
                    "novelty_score": screening_result['novelty_score'],
                    "impact_level": screening_result['impact_level'],
                    "feed_similarity": 0.0,  # Eliminado: IA detecta duplicados
                    "historical_similarity": 0.0  # Simplificado: solo URL exacta
                }
                
                # Usar el nuevo motor de ingesta centralizado
                result = ingestion_engine.ingest_document(full_content_md, source_context)
                if result.get("success"):
                    print(f"      -> ✅ {result.get('nodes_created', 0)} nodo(s) creado(s) con conexiones semánticas.")
                else:
                    print(f"      -> ❌ Error en ingesta: {result.get('reason', 'Desconocido')}")

            except Exception as e:
                print(f"      -> ❌ Error en el procesamiento profundo de la noticia '{entry_link}': {e}")
        
        # 5. Mostrar resumen de procesamiento
        print(f"\n  📊 Resumen: {new_articles_processed} procesadas, {skipped_existing} duplicadas, {skipped_prefilter} prefiltradas, {skipped_screening} rechazadas")
        
        if new_articles_processed == 0:
            print("  ✅ No se encontraron noticias nuevas para procesar.")
        else:
            print(f"  ✅ Se procesaron {new_articles_processed} noticias nuevas de este feed.")

    except Exception as e:
        print(f"  -> ❌ Error fatal al procesar el feed '{target_name}': {e}")


def run_automated_monitoring():
    print("\n--- Vigilancia Automatica de RSS (Version 16.0 - Optimizado) ---")
    
    # Inicializar el nuevo motor de ingesta centralizado
    print("Inicializando Motor de Ingesta Centralizado...")
    ingestion_engine = KnowledgeGraphIngestionEngine()
    
    # Cargar configuración desde YAML
    print("Cargando configuracion de fuentes desde YAML...")
    config_loader = get_config_loader()
    
    try:
        # Obtener fuentes RSS activas desde YAML
        targets = config_loader.get_rss_sources(active_only=True)
        if not targets:
            print("-> No se encontraron objetivos RSS activos para procesar.")
            return
        
        print(f"-> Se encontraron {len(targets)} fuentes RSS activas.")
        
        for target in targets:
            process_rss_feed(target, ingestion_engine)
            # Timestamps eliminados del YAML para simplificar el sistema
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO durante la vigilancia de RSS: {e}")

# Función eliminada: process_fxstreet_feed
# Ahora FXStreet se procesa desde YAML como las otras fuentes

def clean_scraped_markdown(markdown_text: str) -> str:
    print("      -> 🧹 Limpiando contenido scrapeado...")
    text = markdown_text
    match = re.search(r'# .*', text)
    if match: text = text[match.start():]
    footer_start_points = ["Data Source Statement:", "SMM Events & Webinars", "MOST POPULAR"]
    for start_point in footer_start_points:
        if start_point in text: text = text[:text.find(start_point)]; break
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    print("      -> ✅ Limpieza completada.")
    return text.strip()

def scrape_article_with_retries(url: str) -> str:
    print(f"      -> 🔥 Realizando scrapeo profundo de: {url}")
    for i in range(3):
        try:
            print(f"        -> Intento {i + 1} de 3...")
            scraped_data = get_firecrawl_scrape(url) 
            if scraped_data and isinstance(scraped_data, dict):
                markdown_content = scraped_data.get('markdown', '')
                if markdown_content:
                    return clean_scraped_markdown(markdown_content)
        except Exception as e:
            print(f"      -> ❌ Fallo en el intento {i + 1}: {e}")
            if i < 2: time.sleep(5)
    print("      -> ❌ Se han agotado todos los intentos de scrapeo.")
    return ""

# --- CÓDIGO DE ARRANQUE ---
if __name__ == '__main__':
    print("\n--- Iniciando Vigilante de Fuentes (v11.0 Metodo Robusto) ---")
    ai_services.initialize()
    run_automated_monitoring()
    print("\n--- Vigilante ha finalizado su ronda. ---")
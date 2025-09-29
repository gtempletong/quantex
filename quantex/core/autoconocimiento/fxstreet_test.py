# quantex/core/autoconocimiento/fxstreet_test.py (Versión 1.0 - Prueba FXStreet)
import os
import sys
import time
import feedparser
import re
import json
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

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
            # Usar generate_completion en lugar de chat_completion
            response = generate_completion(
                task_complexity="default",
                system_prompt="Eres un experto en análisis de noticias financieras y de commodities.",
                user_prompt=prompt
            )
            
            # Parsear respuesta JSON desde raw_text
            if 'raw_text' in response:
                try:
                    # Limpiar respuesta antes de parsear JSON
                    raw_text = response['raw_text'].strip()
                    # Buscar JSON válido en la respuesta
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

def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calcula similitud semántica usando embeddings
    """
    try:
        # Verificar si embeddings están disponibles
        if not ai_services.embedding_model:
            print(f"      ⚠️ Embeddings no disponibles, usando similitud básica")
            # Fallback: similitud básica por palabras comunes
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if len(words1) == 0 or len(words2) == 0:
                return 0.0
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            return intersection / union if union > 0 else 0.0
        
        # Usar el embedding model de Quantex
        embedding1 = ai_services.embedding_model.encode([text1])
        embedding2 = ai_services.embedding_model.encode([text2])
        
        # Calcular cosine similarity
        similarity = cosine_similarity(embedding1, embedding2)[0][0]
        return float(similarity)
        
    except Exception as e:
        print(f"      ⚠️ Error calculando similitud: {e}")
        # Fallback: similitud básica
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0.0

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

def does_url_exist_in_db(url: str) -> bool:
    """
    (Versión Grafo Unificado)
    Verifica si una URL ya existe como un nodo de tipo 'Documento'
    buscando dentro de la columna 'properties'.
    """
    try:
        # La nueva consulta busca en la tabla 'nodes'.
        response = db.supabase.table('nodes') \
            .select('id', count='exact') \
            .eq('type', 'Documento') \
            .eq('properties->>original_url', url.strip()) \
            .execute()
        
        # La lógica de conteo es la misma.
        if response.count > 0:
            return True
        return False
    except Exception as e:
        print(f"      -> ⚠️  Error durante la verificación de URL en DB: {e}")
        return False

def analyze_feed_context(feed_entries: List[Dict]) -> List[str]:
    """
    Analiza el contexto del feed para detectar duplicados
    """
    context = []
    for entry in feed_entries[:20]:  # Primeras 20 noticias
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        context.append(f"{title} - {summary[:100]}...")
    return context

def check_historical_duplicates(title: str, summary: str) -> Tuple[float, List[str]]:
    """
    Consulta Supabase para duplicados históricos
    """
    try:
        # Query directa a Supabase para documentos de los últimos 30 días
        try:
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            result = db.supabase.table("nodes").select("properties").eq("type", "Documento").gte("created_at", thirty_days_ago.isoformat()).execute()
        except Exception as e:
            print(f"      ⚠️ Error en query de duplicados: {e}")
            return 0.0, []
        
        if not result.data:
            return 0.0, []
        
        max_similarity = 0.0
        similar_titles = []
        
        for row in result.data:
            properties = row.get('properties', {})
            if not properties:
                continue
            hist_title = properties.get('ai_summary', '')[:100] if properties.get('ai_summary') else ''
            hist_summary = properties.get('ai_summary', '') if properties.get('ai_summary') else ''
            
            # Calcular similitud semántica
            similarity = calculate_semantic_similarity(
                f"{title} {summary}",
                f"{hist_title} {hist_summary}"
            )
            
            if similarity > max_similarity:
                max_similarity = similarity
            
            if similarity > 0.7:  # Umbral de similitud
                similar_titles.append(hist_title)
        
        return max_similarity, similar_titles[:5]
        
    except Exception as e:
        print(f"      ⚠️ Error consultando duplicados históricos: {e}")
        return 0.0, []

def process_fxstreet_feed():
    """
    Procesa específicamente el feed de FXStreet para pruebas
    """
    print("--- 🧪 PRUEBA FXSTREET - Source Monitor (Versión 1.0) ---")
    
    # Configuración específica para FXStreet
    feed_url = "https://www.fxstreet.com/rss/news"
    target_name = "Noticias de Forex"
    publisher = "FXStreet"
    keywords = ["forex", "divisas", "CLP", "EUR", "DXY"]
    
    # Configuración del filtro inteligente
    filter_config = {
        "specific_keywords": ["CLP", "EUR/USD", "DXY"],
        "general_keywords": ["forex", "divisas"],
        "filter_logic": "specific_or_general",
        "exclude_keywords": ["CHF", "JPY", "AUD", "CAD", "GBP", "NZD"],
        "target_pairs": ["EUR/USD", "USD/CLP", "CLP/USD"]
    }
    
    print(f"📰 Procesando Feed: {target_name}")
    print(f"🔗 URL: {feed_url}")
    print(f"🏷️ Keywords: {keywords}")
    
    try:
        # Cargar feed
        print("  -> Cargando feed...")
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            print("  ❌ No se encontraron entradas en el feed")
            return
        
        print(f"  -> Feed cargado: {len(feed.entries)} noticias encontradas")
        
        # Analizar contexto del feed
        feed_context = analyze_feed_context(feed.entries)
        print(f"  -> Contexto del feed analizado: {len(feed_context)} noticias de referencia")
        
        # Inicializar screening agent
        screening_agent = NewsScreeningAgent("CLP/EUR/DXY", keywords)
        
        # Inicializar motor de ingesta
        print("🏭 Inicializando Motor de Ingesta Centralizado...")
        ingestion_engine = KnowledgeGraphIngestionEngine()
        
        # Contadores
        processed = 0
        existing = 0
        prefiltered = 0
        rejected_screening = 0
        duplicated = 0
        scrape_errors = 0
        
        # Procesar solo las primeras 3 entradas para prueba de duplicados
        for i, entry in enumerate(feed.entries[:3]):
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            url = entry.get('link', '')
            
            print(f"\n    -> Analizando: '{title[:60]}...'")
            
            # 1. Prefiltro mejorado
            print(f"      🔍 Aplicando prefiltro...")
            if not enhanced_prefilter(title, summary, keywords, filter_config):
                print(f"      ⏭️  Prefiltro: No keywords found - Título: '{title[:50]}...'")
                prefiltered += 1
                continue
            print(f"      ✅ Prefiltro: Pasó - Título: '{title[:50]}...'")
            
            # 2. Verificar si ya existe (usar método de source_monitor)
            if does_url_exist_in_db(url):
                existing += 1
                print(f"      ⏭️  Ya existe en DB")
                continue
            
            # 3. Análisis de similitud en feed actual
            feed_similarity = 0.0
            if i > 0:  # Solo si hay noticias anteriores
                for other_entry in feed.entries[:i]:
                    other_title = other_entry.get('title', '')
                    other_summary = other_entry.get('summary', '')
                    similarity = calculate_semantic_similarity(
                        f"{title} {summary}",
                        f"{other_title} {other_summary}"
                    )
                    feed_similarity = max(feed_similarity, similarity)
            
            print(f"      📊 Similitud máxima en feed: {feed_similarity:.2f}")
            
            # 4. Consultar duplicados históricos
            print(f"      🔍 Consultando Supabase para duplicados...")
            try:
                historical_similarity, similar_titles = check_historical_duplicates(title, summary)
                print(f"      📊 Similitud máxima histórica: {historical_similarity:.2f}")
            except Exception as e:
                print(f"      ⚠️ Error en consulta de duplicados: {e}")
                historical_similarity = 0.0
                similar_titles = []
            
            # 5. Scrapeo profundo PRIMERO
            try:
                print(f"      -> 🔥 Realizando scrapeo profundo de: {url}")
                print(f"        -> Intento 1 de 3...")
                
                # Scrapeo con Firecrawl
                scrape_result = get_firecrawl_scrape(url)
                
                if not scrape_result or not scrape_result.get('markdown'):
                    print(f"        ❌ Scrapeo falló para: {url}")
                    scrape_errors += 1
                    continue
                
                # Mostrar solo el link del contenido scrapeado
                print(f"        📄 Contenido scrapeado: {url}")
                
                print(f"        -> 🧹 Limpiando contenido scrapeado...")
                
                # Limpiar contenido
                content = scrape_result['markdown']
                print(f"        -> ✅ Limpieza completada.")
                
                # Generar hash del contenido para detección de duplicados
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                scraped_time = datetime.now(timezone.utc).isoformat()
                
            except Exception as e:
                print(f"      ❌ Error en scrapeo: {e}")
                scrape_errors += 1
                continue
            
            # 6. Screening IA con CONTENIDO COMPLETO
            print(f"        📄 Longitud del contenido para screening: {len(content)} caracteres")
            print(f"        📄 Primeros 200 chars del contenido: {content[:200]}...")
            
            screening_result = screening_agent.screen_with_full_content(
                title, summary, content, url, publisher,
                feed_similarity, historical_similarity,
                similar_titles, feed_context
            )
            
            print(f"      🤖 Screening IA: {screening_result.get('reasoning', 'Sin reasoning')}")
            print(f"      📊 Novedad: {screening_result.get('novelty_score', 0):.2f}")
            print(f"      🎯 Confianza: {screening_result.get('confidence', 0):.2f}")
            
            # 6. Decisión final
            if not screening_result.get('relevant', False):
                print(f"      ⏭️  Rechazado por screening: {screening_result.get('recommended_action', 'ignore')}")
                rejected_screening += 1
                continue
            
            if screening_result.get('duplicate_analysis', {}).get('is_duplicate', False):
                print(f"      ⏭️  Duplicado detectado: {screening_result.get('duplicate_analysis', {}).get('similarity_level', 'unknown')}")
                duplicated += 1
                continue
            
            # 7. Procesamiento (ya tenemos el contenido)
            impact_level = screening_result.get('impact_level', 'medium')
            print(f"      ✅ Aprobado para ingesta: {impact_level} impact")
            
            # 8. Ingesta al grafo de conocimiento
            try:
                source_context = {
                    "source_type": "Noticia Continua",
                    "source": publisher,  # Mapear publisher a source
                    "topic": target_name,  # Mapear target_name a topic
                    "original_url": url,  # Mapear url a original_url
                    "hash": content_hash,  # Hash del contenido para detección de duplicados
                    "status": "ACTIVE",  # Estado del documento
                    "scraped_time": scraped_time,  # Tiempo exacto del scrapeo
                    "publisher": publisher,
                    "feed_url": feed_url,
                    "target_name": target_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),  # Agregar timestamp
                    "screening_metadata": {
                        "ai_confidence": screening_result.get('confidence', 0),
                        "novelty_score": screening_result.get('novelty_score', 0),
                        "impact_level": impact_level,
                        "feed_similarity": feed_similarity,
                        "historical_similarity": historical_similarity,
                        "similar_titles": similar_titles,
                        "reasoning": screening_result.get('reasoning', ''),
                        "duplicate_analysis": screening_result.get('duplicate_analysis', {})
                    }
                }
                
                print(f"--- 🏭 Iniciando Línea de Ensamblaje (Modo Grafo) para fuente: {publisher} ---")
                
                # Ingestar documento
                print(f"        -> 🧠 Enviando a IA para resumen y extracción...")
                result = ingestion_engine.ingest_document(
                    raw_text=content,
                    source_context=source_context
                )
                
                if result and result.get('success'):
                    processed += 1
                    print(f"      -> ✅ Documento procesado exitosamente")
                    
                    # Mostrar el resumen generado por la IA
                    if 'nodes' in result and result['nodes']:
                        # Obtener el primer nodo (documento principal)
                        first_node = result['nodes'][0]
                        node_id = first_node.get('node_id', '')
                        
                        # Consultar el nodo en Supabase para obtener el resumen
                        try:
                            # Usar consulta directa a Supabase para evitar problemas de filtros
                            node_data = db.supabase.table("nodes").select("properties").eq("id", node_id).execute()
                            
                            if node_data.data and len(node_data.data) > 0:
                                properties = node_data.data[0].get('properties', {})
                                ai_summary = properties.get('ai_summary', 'Sin resumen disponible')
                                print(f"        📝 Resumen IA: {ai_summary}")
                            else:
                                print(f"        📝 Resumen IA: No se pudo obtener el resumen")
                                
                        except Exception as e:
                            print(f"        📝 Resumen IA: Error obteniendo resumen: {e}")
                    
                    print(f"        📊 Resultado de ingesta: {result}")
                else:
                    print(f"      -> ❌ Error en procesamiento: {result}")
                
            except Exception as e:
                print(f"      ❌ Error en procesamiento: {e}")
                continue
        
        # Resumen final
        print(f"\n  -> Resumen: {processed} procesadas, {existing} ya existían, {prefiltered} prefiltradas, {rejected_screening} rechazadas por screening, {duplicated} duplicadas, {scrape_errors} errores de scrapeo")
        
        # Verificación adicional de duplicados
        print(f"\n  🔍 Verificación de duplicados en DB:")
        try:
            all_docs = db.supabase.table("nodes").select("id, properties").eq("type", "Documento").execute()
            if all_docs.data:
                print(f"    📊 Total documentos en DB: {len(all_docs.data)}")
                urls = []
                hashes = []
                for doc in all_docs.data:
                    props = doc.get('properties', {})
                    if props.get('original_url'):
                        urls.append(props['original_url'])
                    if props.get('hash'):
                        hashes.append(props['hash'])
                
                print(f"    📊 URLs únicas: {len(set(urls))} de {len(urls)}")
                print(f"    📊 Hashes únicos: {len(set(hashes))} de {len(hashes)}")
                
                # Mostrar duplicados si los hay
                if len(urls) != len(set(urls)):
                    print(f"    ⚠️  URLs duplicadas encontradas!")
                if len(hashes) != len(set(hashes)):
                    print(f"    ⚠️  Hashes duplicados encontrados!")
            else:
                print(f"    📊 No hay documentos en DB")
        except Exception as e:
            print(f"    ❌ Error verificando duplicados: {e}")
        
        if processed > 0:
            print(f"  -> ✅ Se procesaron {processed} noticias nuevas de este feed.")
        else:
            print(f"  -> ✅ No se encontraron noticias nuevas para procesar.")
        
    except Exception as e:
        print(f"❌ Error procesando feed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("--- Iniciando Vigilante de Fuentes (v11.0 Metodo Robusto) ---")
    
    # Inicializar servicios
    ai_services.initialize()
    
    # Ejecutar prueba de FXStreet
    process_fxstreet_feed()
    
    print("--- ✅ Prueba FXStreet finalizada. ---")

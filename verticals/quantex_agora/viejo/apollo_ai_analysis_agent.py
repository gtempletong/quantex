#!/usr/bin/env python3
"""
Apollo AI Analysis Agent
Agent con IA pura para análisis completo de empresas y clasificación de prospectos
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
from bs4 import BeautifulSoup
import re

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApolloAIAnalysisAgent:
    """Agent con IA pura para análisis completo de empresas y prospectos"""
    
    def __init__(self, llm_provider: str = "openai"):
        """
        Inicializar agent con IA
        
        Args:
            llm_provider: "openai", "claude", "gemini", o "existing"
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        self.llm_provider = llm_provider
        
        # Inicializar cliente LLM
        self.llm_client = self._initialize_llm_client()
        
        logger.info(f"Apollo AI Analysis Agent inicializado con {llm_provider}")
    
    def _initialize_llm_client(self):
        """Inicializar cliente LLM según el proveedor"""
        if self.llm_provider == "openai":
            return self._init_openai_client()
        elif self.llm_provider == "claude":
            return self._init_claude_client()
        elif self.llm_provider == "gemini":
            return self._init_gemini_client()
        elif self.llm_provider == "existing":
            return self._init_existing_client()
        else:
            raise ValueError(f"Proveedor LLM no soportado: {self.llm_provider}")
    
    def _init_openai_client(self):
        """Inicializar cliente OpenAI"""
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            return openai
        except ImportError:
            raise ImportError("Instala openai: pip install openai")
    
    def _init_claude_client(self):
        """Inicializar cliente Claude"""
        try:
            import anthropic
            return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except ImportError:
            raise ImportError("Instala anthropic: pip install anthropic")
    
    def _init_gemini_client(self):
        """Inicializar cliente Gemini"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            return genai.GenerativeModel('gemini-pro')
        except ImportError:
            raise ImportError("Instala google-generativeai: pip install google-generativeai")
    
    def _init_existing_client(self):
        """Usar sistema LLM existente de Quantex"""
        try:
            # Importar el sistema LLM existente
            from quantex.core.ai_service_manager import AIServiceManager
            return AIServiceManager()
        except ImportError:
            logger.warning("No se pudo importar sistema LLM existente, usando OpenAI")
            return self._init_openai_client()
    
    def collect_company_data(self, company_data: Dict) -> Dict[str, Any]:
        """
        Recolecta TODA la información posible de una empresa
        
        Returns:
            Diccionario con toda la información recolectada
        """
        collected_data = {
            'basic_info': company_data,
            'website_content': '',
            'linkedin_content': '',
            'google_search_results': '',
            'business_insights': {},
            'financial_indicators': {},
            'market_position': {},
            'contact_opportunities': []
        }
        
        # 1. Scrapear website principal
        website = company_data.get('website')
        if website:
            collected_data['website_content'] = self._scrape_website_comprehensive(website)
        
        # 2. Scrapear LinkedIn de la empresa
        linkedin_url = company_data.get('linkedin_url')
        if linkedin_url:
            collected_data['linkedin_content'] = self._scrape_linkedin_company(linkedin_url)
        
        # 3. Búsqueda en Google para contexto adicional
        company_name = company_data.get('name', '')
        if company_name:
            collected_data['google_search_results'] = self._google_search_company(company_name)
        
        # 4. Extraer insights estructurados
        collected_data['business_insights'] = self._extract_structured_insights(collected_data)
        
        return collected_data
    
    def _scrape_website_comprehensive(self, url: str) -> str:
        """Scrapea website de forma comprehensiva"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer contenido estructurado
            content_parts = []
            
            # Meta tags importantes
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('name') in ['description', 'keywords'] or meta.get('property'):
                    content_parts.append(f"Meta: {meta.get('content', '')}")
            
            # Títulos y subtítulos
            for tag in ['h1', 'h2', 'h3', 'h4']:
                for element in soup.find_all(tag):
                    text = element.get_text().strip()
                    if text and len(text) > 5:
                        content_parts.append(f"{tag.upper()}: {text}")
            
            # Párrafos de contenido
            paragraphs = soup.find_all('p')
            for p in paragraphs[:20]:  # Limitar para no sobrecargar
                text = p.get_text().strip()
                if len(text) > 30:
                    content_parts.append(f"P: {text}")
            
            # Listas (productos, servicios, etc.)
            for ul in soup.find_all(['ul', 'ol']):
                items = ul.find_all('li')
                if items:
                    list_text = " | ".join([li.get_text().strip() for li in items[:10]])
                    content_parts.append(f"Lista: {list_text}")
            
            return '\n'.join(content_parts[:50])  # Limitar contenido total
            
        except Exception as e:
            logger.debug(f"Error scraping website {url}: {e}")
            return ""
    
    def _scrape_linkedin_company(self, linkedin_url: str) -> str:
        """Scrapea información de LinkedIn de la empresa"""
        try:
            # LinkedIn requiere autenticación, por ahora retornamos URL
            return f"LinkedIn URL: {linkedin_url}"
        except Exception as e:
            logger.debug(f"Error scraping LinkedIn {linkedin_url}: {e}")
            return ""
    
    def _google_search_company(self, company_name: str) -> str:
        """Búsqueda en Google para contexto adicional"""
        try:
            # Implementación básica - en producción usarías Google Search API
            search_query = f'"{company_name}" empresa importación exportación'
            return f"Búsqueda sugerida: {search_query}"
        except Exception as e:
            logger.debug(f"Error en búsqueda Google: {e}")
            return ""
    
    def _extract_structured_insights(self, collected_data: Dict) -> Dict[str, Any]:
        """Extrae insights estructurados de los datos recolectados"""
        insights = {
            'business_model': '',
            'target_markets': [],
            'products_services': [],
            'company_size_indicator': '',
            'industry_sector': '',
            'international_activity': False,
            'financial_indicators': [],
            'competitive_advantages': [],
            'growth_opportunities': []
        }
        
        # Análisis básico de contenido
        all_content = ' '.join([
            collected_data.get('website_content', ''),
            collected_data.get('linkedin_content', ''),
            collected_data.get('google_search_results', '')
        ]).lower()
        
        # Detectar actividad internacional
        international_keywords = ['import', 'export', 'internacional', 'global', 'trade', 'comercio exterior']
        insights['international_activity'] = any(keyword in all_content for keyword in international_keywords)
        
        # Detectar modelo de negocio
        if 'b2b' in all_content or 'empresas' in all_content:
            insights['business_model'] = 'B2B'
        elif 'b2c' in all_content or 'consumidores' in all_content:
            insights['business_model'] = 'B2C'
        
        return insights
    
    def analyze_with_ai(self, person_data: Dict, company_data: Dict, collected_data: Dict) -> Dict[str, Any]:
        """
        Análisis completo con IA
        
        Returns:
            Análisis completo con clasificación y insights
        """
        
        # Construir prompt comprehensivo
        prompt = self._build_analysis_prompt(person_data, company_data, collected_data)
        
        # Llamar a IA
        ai_response = self._call_llm(prompt)
        
        # Parsear respuesta
        analysis = self._parse_ai_response(ai_response)
        
        return analysis
    
    def _build_analysis_prompt(self, person_data: Dict, company_data: Dict, collected_data: Dict) -> str:
        """Construye prompt comprehensivo para IA"""
        
        prompt = f"""
Eres un analista experto en prospección B2B para servicios financieros. Analiza este prospecto para Quantex (servicios financieros para empresas importadoras/exportadoras).

=== DATOS DE LA PERSONA ===
Nombre: {person_data.get('full_name', 'N/A')}
Título: {person_data.get('title', 'N/A')}
Seniority: {person_data.get('seniority', 'N/A')}
Email: {person_data.get('email', 'N/A')}
LinkedIn: {person_data.get('linkedin_url', 'N/A')}
Teléfono: {person_data.get('phone', 'N/A')}

=== DATOS DE LA EMPRESA ===
Nombre: {company_data.get('name', 'N/A')}
Industria: {company_data.get('industry', 'N/A')}
Empleados: {company_data.get('employee_count', 'N/A')}
Revenue: {company_data.get('annual_revenue', 'N/A')}
Ubicación: {company_data.get('location', 'N/A')}
Website: {company_data.get('website', 'N/A')}
Keywords: {company_data.get('keywords', 'N/A')}

=== CONTENIDO DEL WEBSITE ===
{collected_data.get('website_content', 'No disponible')[:2000]}

=== CRITERIOS DE EVALUACIÓN ===
1. ¿Es empresa importadora/exportadora o tiene actividad internacional?
2. ¿Es la persona dueño/director/gerente general/CFO con poder de decisión?
3. ¿Tiene potencial para servicios financieros (financiamiento, seguros, etc.)?
4. ¿Qué información relevante hay para personalizar comunicación?

Responde en JSON con esta estructura exacta:
{{
    "company_analysis": {{
        "is_import_export": true/false,
        "business_model": "B2B/B2C/Mixed",
        "industry_sector": "descripción del sector",
        "company_size": "Small/Medium/Large",
        "international_activity": true/false,
        "financial_sophistication": "Low/Medium/High"
    }},
    "person_analysis": {{
        "is_decision_maker": true/false,
        "seniority_level": "C-Suite/Senior/Mid/Entry",
        "financial_responsibility": true/false,
        "contact_quality": "High/Medium/Low"
    }},
    "quantex_fit": {{
        "ai_score": 0-100,
        "ai_classification": "INCLUIR/REVISAR/EXCLUIR",
        "confidence_level": "High/Medium/Low",
        "reasoning": "explicación detallada del score"
    }},
    "personalization_insights": {{
        "company_pain_points": ["lista de posibles problemas"],
        "growth_opportunities": ["oportunidades de crecimiento"],
        "financial_needs": ["necesidades financieras identificadas"],
        "communication_hooks": ["ideas para personalizar email"],
        "pitch_angles": ["ángulos específicos para el pitch"]
    }},
    "next_steps": {{
        "research_priority": "High/Medium/Low",
        "contact_method": "Email/LinkedIn/Phone",
        "follow_up_timeline": "sugerencia de timing"
    }}
}}
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Llama al LLM según el proveedor configurado"""
        try:
            if self.llm_provider == "openai":
                response = self.llm_client.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            
            elif self.llm_provider == "claude":
                response = self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
            elif self.llm_provider == "gemini":
                response = self.llm_client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 2000
                    }
                )
                return response.text
            
            elif self.llm_provider == "existing":
                # Usar sistema existente
                return self.llm_client.generate_response(prompt)
            
        except Exception as e:
            logger.error(f"Error llamando LLM: {e}")
            return '{"error": "Error en análisis IA"}'
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parsea respuesta de IA a diccionario"""
        try:
            # Limpiar respuesta si tiene markdown
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta IA: {e}")
            return {
                "error": "Error parseando respuesta IA",
                "raw_response": response
            }
    
    def analyze_prospect_complete(self, person_id: str) -> Dict[str, Any]:
        """
        Análisis completo de un prospecto
        
        Returns:
            Análisis completo con toda la información
        """
        logger.info(f"Iniciando análisis completo de prospecto: {person_id}")
        
        # 1. Obtener datos básicos
        person_result = self.supabase.table('apollo_persons').select('*').eq('id', person_id).execute()
        if not person_result.data:
            return {'error': 'Persona no encontrada'}
        
        person_data = person_result.data[0]
        
        # 2. Obtener datos de empresa
        company_data = {}
        if person_data.get('company_id'):
            company_result = self.supabase.table('apollo_companies').select('*').eq('id', person_data['company_id']).execute()
            if company_result.data:
                company_data = company_result.data[0]
        
        # 3. Recolectar información adicional
        collected_data = self.collect_company_data(company_data)
        
        # 4. Análisis con IA
        ai_analysis = self.analyze_with_ai(person_data, company_data, collected_data)
        
        # 5. Preparar resultado final
        result = {
            'person_id': person_id,
            'person_data': person_data,
            'company_data': company_data,
            'collected_data': collected_data,
            'ai_analysis': ai_analysis,
            'analysis_timestamp': datetime.now().isoformat(),
            'llm_provider': self.llm_provider
        }
        
        # 6. Actualizar base de datos
        if 'ai_analysis' in ai_analysis and 'quantex_fit' in ai_analysis['ai_analysis']:
            quantex_fit = ai_analysis['ai_analysis']['quantex_fit']
            self.supabase.table('apollo_persons').update({
                'ai_classification': quantex_fit.get('ai_classification'),
                'ai_score': quantex_fit.get('ai_score')
            }).eq('id', person_id).execute()
        
        return result
    
    def analyze_all_prospects(self, limit: int = 50) -> Dict[str, Any]:
        """
        Analiza todos los prospectos sin clasificar
        
        Returns:
            Estadísticas del análisis
        """
        logger.info(f"Iniciando análisis masivo (límite: {limit})")
        
        # Obtener prospectos sin clasificar
        result = self.supabase.table('apollo_persons').select('id').is_('ai_classification', 'null').limit(limit).execute()
        
        if not result.data:
            return {'message': 'No hay prospectos sin clasificar'}
        
        prospect_ids = [p['id'] for p in result.data]
        logger.info(f"Analizando {len(prospect_ids)} prospectos con IA")
        
        stats = {
            'total_analyzed': 0,
            'incluir': 0,
            'revisar': 0,
            'excluir': 0,
            'errors': 0,
            'results': []
        }
        
        for person_id in prospect_ids:
            try:
                analysis = self.analyze_prospect_complete(person_id)
                
                if 'error' in analysis:
                    stats['errors'] += 1
                    continue
                
                stats['total_analyzed'] += 1
                
                # Contar clasificaciones
                ai_classification = analysis.get('ai_analysis', {}).get('quantex_fit', {}).get('ai_classification', 'EXCLUIR')
                stats[ai_classification.lower()] += 1
                
                stats['results'].append({
                    'person_id': person_id,
                    'person_name': analysis['person_data'].get('full_name'),
                    'company_name': analysis['person_data'].get('company_name'),
                    'ai_classification': ai_classification,
                    'ai_score': analysis.get('ai_analysis', {}).get('quantex_fit', {}).get('ai_score', 0)
                })
                
                logger.info(f"✅ {analysis['person_data'].get('full_name')} - {ai_classification}")
                
            except Exception as e:
                logger.error(f"Error analizando {person_id}: {e}")
                stats['errors'] += 1
        
        return stats


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apollo AI Analysis Agent')
    parser.add_argument('--person-id', help='Analizar persona específica por ID')
    parser.add_argument('--analyze-all', action='store_true', help='Analizar todos los prospectos sin clasificar')
    parser.add_argument('--limit', type=int, default=50, help='Límite de prospectos a analizar')
    parser.add_argument('--llm', choices=['openai', 'claude', 'gemini', 'existing'], 
                       default='existing', help='Proveedor LLM a usar')
    
    args = parser.parse_args()
    
    try:
        agent = ApolloAIAnalysisAgent(llm_provider=args.llm)
        
        if args.person_id:
            # Analizar persona específica
            result = agent.analyze_prospect_complete(args.person_id)
            print("\n" + "=" * 80)
            print("🤖 ANÁLISIS COMPLETO CON IA")
            print("=" * 80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.analyze_all:
            # Analizar todos
            stats = agent.analyze_all_prospects(args.limit)
            print("\n" + "=" * 80)
            print("📊 RESUMEN DE ANÁLISIS MASIVO")
            print("=" * 80)
            print(f"Total analizados: {stats['total_analyzed']}")
            print(f"✅ INCLUIR: {stats['incluir']}")
            print(f"⚠️  REVISAR: {stats['revisar']}")
            print(f"❌ EXCLUIR: {stats['excluir']}")
            print(f"❌ Errores: {stats['errors']}")
            
        else:
            print("Usa --person-id <id> o --analyze-all")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


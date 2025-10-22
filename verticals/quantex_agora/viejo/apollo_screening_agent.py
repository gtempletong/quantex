#!/usr/bin/env python3
"""
Apollo Screening Agent
Analiza prospectos de apollo_persons con criterios específicos para Quantex
"""

import os
import sys
import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
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


class ApolloScreeningAgent:
    """Agent para analizar y clasificar prospectos de Apollo con criterios específicos"""
    
    def __init__(self):
        """Inicializar agent"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("Apollo Screening Agent inicializado")
    
    def is_import_export_company(self, company_data: Dict) -> Tuple[bool, str]:
        """
        Determina si una empresa es importadora/exportadora
        
        Returns:
            (es_importadora, razon)
        """
        # Campos a analizar
        industry = (company_data.get('industry') or '').lower()
        keywords = (company_data.get('keywords') or '').lower()
        website = company_data.get('website', '')
        
        # Palabras clave de importación/exportación
        import_export_keywords = [
            'import', 'export', 'importación', 'exportación', 'importadora', 'exportadora',
            'comercio exterior', 'trade', 'trading', 'distribuidor', 'distribuidora',
            'comercializadora', 'comercializador', 'internacional', 'global',
            'freight', 'logistics', 'shipping', 'customs', 'aduana'
        ]
        
        # Palabras clave de industria relacionada
        industry_keywords = [
            'manufacturing', 'manufactura', 'production', 'producción',
            'food', 'alimentos', 'beverages', 'bebidas', 'agriculture', 'agricultura',
            'mining', 'minería', 'textile', 'textil', 'chemical', 'química',
            'automotive', 'automotriz', 'electronics', 'electrónica'
        ]
        
        # Verificar keywords
        for keyword in import_export_keywords:
            if keyword in keywords or keyword in industry:
                return True, f"Keyword encontrado: {keyword}"
        
        # Verificar industria relacionada
        for keyword in industry_keywords:
            if keyword in industry:
                return True, f"Industria relacionada: {keyword}"
        
        # Si tiene website, analizar contenido
        if website:
            try:
                website_content = self._scrape_website_content(website)
                if website_content:
                    for keyword in import_export_keywords:
                        if keyword in website_content.lower():
                            return True, f"Website contiene: {keyword}"
            except Exception as e:
                logger.debug(f"Error scraping website {website}: {e}")
        
        return False, "No cumple criterios de importación/exportación"
    
    def is_target_seniority(self, person_data: Dict) -> Tuple[bool, str]:
        """
        Determina si la persona tiene el seniority objetivo
        
        Returns:
            (es_target, razon)
        """
        title = (person_data.get('title') or '').lower()
        seniority = (person_data.get('seniority') or '').lower()
        
        # Títulos objetivo
        target_titles = [
            'owner', 'propietario', 'dueño', 'socio', 'partner',
            'director', 'directora', 'ceo', 'gerente general', 'general manager',
            'cfo', 'gerente de finanzas', 'finance manager', 'financial director',
            'president', 'presidente', 'chairman', 'chairwoman'
        ]
        
        # Seniority objetivo
        target_seniority = [
            'c-suite', 'c suite', 'c-level', 'c level', 'executive', 'ejecutivo',
            'senior', 'sénior', 'director', 'directora', 'manager', 'gerente'
        ]
        
        # Verificar título
        for target_title in target_titles:
            if target_title in title:
                return True, f"Título objetivo: {target_title}"
        
        # Verificar seniority
        for target_senior in target_seniority:
            if target_senior in seniority:
                return True, f"Seniority objetivo: {target_senior}"
        
        return False, f"Título/Seniority no objetivo: {title} / {seniority}"
    
    def _scrape_website_content(self, url: str) -> Optional[str]:
        """
        Extrae contenido relevante del website de la empresa
        
        Returns:
            Contenido de texto del website
        """
        try:
            # Asegurar que tenga protocolo
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer texto de elementos relevantes
            content_parts = []
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content_parts.append(meta_desc['content'])
            
            # Títulos principales
            for tag in ['h1', 'h2', 'h3']:
                for element in soup.find_all(tag):
                    if element.get_text().strip():
                        content_parts.append(element.get_text().strip())
            
            # Párrafos de contenido
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if len(text) > 20:  # Solo párrafos sustanciales
                    content_parts.append(text)
            
            return ' '.join(content_parts[:10])  # Limitar contenido
            
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
            return None
    
    def extract_company_insights(self, company_data: Dict) -> Dict[str, str]:
        """
        Extrae insights relevantes de la empresa para personalización
        
        Returns:
            Diccionario con insights para email personalizado
        """
        insights = {
            'industry': company_data.get('industry', ''),
            'employee_count': company_data.get('employee_count', ''),
            'annual_revenue': company_data.get('annual_revenue', ''),
            'location': company_data.get('location', ''),
            'website_content': '',
            'business_model': '',
            'target_markets': '',
            'key_products': ''
        }
        
        # Scrapear website si existe
        website = company_data.get('website')
        if website:
            website_content = self._scrape_website_content(website)
            if website_content:
                insights['website_content'] = website_content[:500]  # Limitar
                
                # Extraer información específica
                insights.update(self._extract_business_insights(website_content))
        
        return insights
    
    def _extract_business_insights(self, content: str) -> Dict[str, str]:
        """
        Extrae insights específicos del contenido del website
        """
        insights = {
            'business_model': '',
            'target_markets': '',
            'key_products': ''
        }
        
        content_lower = content.lower()
        
        # Detectar modelo de negocio
        if any(word in content_lower for word in ['b2b', 'business to business', 'empresas']):
            insights['business_model'] = 'B2B'
        elif any(word in content_lower for word in ['b2c', 'business to consumer', 'consumidores']):
            insights['business_model'] = 'B2C'
        
        # Detectar mercados objetivo
        markets = []
        if 'chile' in content_lower:
            markets.append('Chile')
        if 'latam' in content_lower or 'latinoamérica' in content_lower:
            markets.append('Latinoamérica')
        if 'internacional' in content_lower or 'global' in content_lower:
            markets.append('Internacional')
        
        if markets:
            insights['target_markets'] = ', '.join(markets)
        
        # Detectar productos clave (simplificado)
        product_keywords = ['productos', 'servicios', 'soluciones', 'línea de productos']
        for keyword in product_keywords:
            if keyword in content_lower:
                # Buscar contexto alrededor de la palabra
                start = content_lower.find(keyword)
                if start != -1:
                    context = content[start:start+200]
                    insights['key_products'] = context[:100]
                    break
        
        return insights
    
    def calculate_ai_score(self, person_data: Dict, company_data: Dict, 
                          company_insights: Dict) -> Tuple[int, str]:
        """
        Calcula score AI basado en criterios específicos
        
        Returns:
            (score, razon)
        """
        score = 0
        reasons = []
        
        # Criterio 1: Empresa importadora/exportadora (40 puntos)
        is_import_export, import_reason = self.is_import_export_company(company_data)
        if is_import_export:
            score += 40
            reasons.append(f"✅ {import_reason}")
        else:
            reasons.append(f"❌ {import_reason}")
        
        # Criterio 2: Seniority objetivo (30 puntos)
        is_target_seniority, seniority_reason = self.is_target_seniority(person_data)
        if is_target_seniority:
            score += 30
            reasons.append(f"✅ {seniority_reason}")
        else:
            reasons.append(f"❌ {seniority_reason}")
        
        # Criterio 3: Tiene email (10 puntos)
        if person_data.get('email'):
            score += 10
            reasons.append("✅ Tiene email")
        else:
            reasons.append("❌ Sin email")
        
        # Criterio 4: Tiene LinkedIn (10 puntos)
        if person_data.get('linkedin_url'):
            score += 10
            reasons.append("✅ Tiene LinkedIn")
        else:
            reasons.append("❌ Sin LinkedIn")
        
        # Criterio 5: Información de empresa disponible (10 puntos)
        if company_insights.get('website_content'):
            score += 10
            reasons.append("✅ Website con información")
        else:
            reasons.append("❌ Sin información de website")
        
        return score, ' | '.join(reasons)
    
    def classify_prospect(self, person_id: str) -> Dict[str, any]:
        """
        Clasifica un prospecto específico
        
        Returns:
            Diccionario con clasificación completa
        """
        # Obtener datos de la persona
        person_result = self.supabase.table('apollo_persons').select('*').eq('id', person_id).execute()
        if not person_result.data:
            return {'error': 'Persona no encontrada'}
        
        person_data = person_result.data[0]
        
        # Obtener datos de la empresa si existe
        company_data = {}
        if person_data.get('company_id'):
            company_result = self.supabase.table('apollo_companies').select('*').eq('id', person_data['company_id']).execute()
            if company_result.data:
                company_data = company_result.data[0]
        
        # Análisis
        is_import_export, import_reason = self.is_import_export_company(company_data)
        is_target_seniority, seniority_reason = self.is_target_seniority(person_data)
        company_insights = self.extract_company_insights(company_data)
        ai_score, score_reason = self.calculate_ai_score(person_data, company_data, company_insights)
        
        # Clasificación final
        if ai_score >= 70:
            ai_classification = 'INCLUIR'
        elif ai_score >= 50:
            ai_classification = 'REVISAR'
        else:
            ai_classification = 'EXCLUIR'
        
        return {
            'person_id': person_id,
            'person_name': person_data.get('full_name'),
            'company_name': person_data.get('company_name'),
            'is_import_export': is_import_export,
            'is_target_seniority': is_target_seniority,
            'ai_score': ai_score,
            'ai_classification': ai_classification,
            'score_reason': score_reason,
            'company_insights': company_insights,
            'import_reason': import_reason,
            'seniority_reason': seniority_reason
        }
    
    def screen_all_prospects(self, limit: int = 100) -> Dict[str, any]:
        """
        Analiza todos los prospectos sin clasificar
        
        Returns:
            Estadísticas del screening
        """
        logger.info(f"Iniciando screening de prospectos (límite: {limit})")
        
        # Obtener prospectos sin clasificar
        result = self.supabase.table('apollo_persons').select('id').is_('ai_classification', 'null').limit(limit).execute()
        
        if not result.data:
            return {'message': 'No hay prospectos sin clasificar'}
        
        prospect_ids = [p['id'] for p in result.data]
        logger.info(f"Analizando {len(prospect_ids)} prospectos")
        
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
                classification = self.classify_prospect(person_id)
                
                if 'error' in classification:
                    stats['errors'] += 1
                    continue
                
                stats['total_analyzed'] += 1
                stats[classification['ai_classification'].lower()] += 1
                stats['results'].append(classification)
                
                # Actualizar en base de datos
                self.supabase.table('apollo_persons').update({
                    'ai_classification': classification['ai_classification'],
                    'ai_score': classification['ai_score']
                }).eq('id', person_id).execute()
                
                logger.info(f"✅ {classification['person_name']} - {classification['ai_classification']} ({classification['ai_score']})")
                
            except Exception as e:
                logger.error(f"Error analizando {person_id}: {e}")
                stats['errors'] += 1
        
        return stats


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apollo Screening Agent')
    parser.add_argument('--person-id', help='Analizar persona específica por ID')
    parser.add_argument('--screen-all', action='store_true', help='Analizar todos los prospectos sin clasificar')
    parser.add_argument('--limit', type=int, default=100, help='Límite de prospectos a analizar')
    
    args = parser.parse_args()
    
    try:
        agent = ApolloScreeningAgent()
        
        if args.person_id:
            # Analizar persona específica
            result = agent.classify_prospect(args.person_id)
            print("\n" + "=" * 80)
            print("🔍 ANÁLISIS DE PROSPECTO")
            print("=" * 80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.screen_all:
            # Analizar todos
            stats = agent.screen_all_prospects(args.limit)
            print("\n" + "=" * 80)
            print("📊 RESUMEN DE SCREENING")
            print("=" * 80)
            print(f"Total analizados: {stats['total_analyzed']}")
            print(f"✅ INCLUIR: {stats['incluir']}")
            print(f"⚠️  REVISAR: {stats['revisar']}")
            print(f"❌ EXCLUIR: {stats['excluir']}")
            print(f"❌ Errores: {stats['errors']}")
            
        else:
            print("Usa --person-id <id> o --screen-all")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


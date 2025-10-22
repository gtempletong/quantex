#!/usr/bin/env python3
"""
Script para cruzar clasificaciones: Empresa → Personas
Busca personas en apollo_persons relacionadas con empresas clasificadas
y copia la clasificación de la empresa a las personas
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


class CompanyToPersonClassifier:
    """Cruza clasificaciones de empresas con personas"""
    
    def __init__(self):
        """Inicializar clasificador"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        print("✅ Company to Person Classifier inicializado")
    
    def find_companies_with_classification(self):
        """Buscar empresas con clasificación de IA"""
        # Obtener todas las empresas y filtrar en Python
        result = self.supabase.table('apollo_companies').select('id, name, ai_score, ai_classification').execute()
        
        # Filtrar empresas con clasificación
        companies_with_classification = [c for c in result.data if c.get('ai_classification')]
        
        if not companies_with_classification:
            print("❌ No hay empresas con clasificación")
            return []
        
        print(f"📊 Empresas con clasificación: {len(companies_with_classification)}")
        return companies_with_classification
    
    def find_persons_by_company_name(self, company_name: str):
        """Buscar personas por nombre de empresa"""
        # Buscar variaciones del nombre
        search_terms = [
            company_name,
            company_name.replace(' ', ''),
            company_name.replace(' ', '_'),
            company_name.replace(' ', '-')
        ]
        
        persons = []
        for term in search_terms:
            result = self.supabase.table('apollo_persons').select('*').ilike('company_name', f'%{term}%').execute()
            if result.data:
                persons.extend(result.data)
        
        # Eliminar duplicados por ID
        seen_ids = set()
        unique_persons = []
        for person in persons:
            if person['id'] not in seen_ids:
                seen_ids.add(person['id'])
                unique_persons.append(person)
        
        return unique_persons
    
    def update_person_classification(self, person_id: str, company_score: int, company_classification: str, company_name: str) -> bool:
        """Actualizar clasificación de persona basada en empresa"""
        try:
            # Usar columnas nuevas: company_ai_score, company_ai_classification, company_analyzed
            result = self.supabase.table('apollo_persons').update({
                'company_ai_score': company_score,
                'company_ai_classification': company_classification,
                'company_analyzed': company_name
            }).eq('id', person_id).execute()
            
            return result.data is not None
        except Exception as e:
            print(f"   ❌ Error actualizando persona {person_id}: {e}")
            return False
    
    def classify_persons_for_company(self, company: dict) -> dict:
        """Clasificar personas de una empresa específica"""
        company_name = company['name']
        company_id = company['id']
        company_score = company['ai_score']
        company_classification = company['ai_classification']
        
        print(f"\n🏢 Empresa: {company_name}")
        print(f"   Score: {company_score}/100")
        print(f"   Clasificación: {company_classification}")
        
        # Buscar personas
        persons = self.find_persons_by_company_name(company_name)
        
        if not persons:
            print(f"   ⚠️  No se encontraron personas para esta empresa")
            return {
                'company_name': company_name,
                'persons_found': 0,
                'persons_updated': 0
            }
        
        print(f"   👥 Personas encontradas: {len(persons)}")
        
        # Actualizar cada persona
        updated_count = 0
        for person in persons:
            person_name = person['full_name']
            person_id = person['id']
            person_title = person.get('title', 'N/A')
            
            success = self.update_person_classification(
                person_id, 
                company_score, 
                company_classification, 
                company_name
            )
            
            if success:
                updated_count += 1
                print(f"   ✅ {person_name} ({person_title})")
        
        return {
            'company_name': company_name,
            'persons_found': len(persons),
            'persons_updated': updated_count
        }
    
    def run_classification(self, company_name_filter: str = None):
        """Ejecutar clasificación completa"""
        print("=" * 80)
        print("🔄 CRUCE DE CLASIFICACIONES: EMPRESA → PERSONAS")
        print("=" * 80)
        
        # Buscar empresas clasificadas
        companies = self.find_companies_with_classification()
        
        if not companies:
            print("❌ No hay empresas clasificadas para procesar")
            return
        
        # Filtrar por nombre si se especifica
        if company_name_filter:
            companies = [c for c in companies if company_name_filter.lower() in c['name'].lower()]
            if not companies:
                print(f"❌ No se encontró empresa con nombre '{company_name_filter}'")
                return
            print(f"\n🎯 Filtrando por empresa: {company_name_filter}")
        
        print(f"\n📊 Procesando {len(companies)} empresa(s)...")
        
        stats = {
            'total_companies': len(companies),
            'total_persons_found': 0,
            'total_persons_updated': 0,
            'companies_with_persons': 0,
            'companies_without_persons': 0
        }
        
        # Procesar cada empresa
        for company in companies:
            result = self.classify_persons_for_company(company)
            
            stats['total_persons_found'] += result['persons_found']
            stats['total_persons_updated'] += result['persons_updated']
            
            if result['persons_found'] > 0:
                stats['companies_with_persons'] += 1
            else:
                stats['companies_without_persons'] += 1
        
        # Mostrar resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN")
        print("=" * 80)
        print(f"Empresas procesadas: {stats['total_companies']}")
        print(f"Empresas con personas: {stats['companies_with_persons']}")
        print(f"Empresas sin personas: {stats['companies_without_persons']}")
        print(f"Personas encontradas: {stats['total_persons_found']}")
        print(f"Personas actualizadas: {stats['total_persons_updated']}")
        print("=" * 80)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clasificar personas basado en clasificación de empresas')
    parser.add_argument('--company', help='Filtrar por nombre de empresa específica')
    
    args = parser.parse_args()
    
    try:
        classifier = CompanyToPersonClassifier()
        classifier.run_classification(company_name_filter=args.company)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

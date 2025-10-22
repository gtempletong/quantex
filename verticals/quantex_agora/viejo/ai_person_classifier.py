#!/usr/bin/env python3
"""
AI Person Classifier
Clasifica personas basándose en:
1. Score de la empresa donde trabaja
2. Si es gerente relevante en toma de decisiones financieras
"""

import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


class AIPersonClassifier:
    """Clasifica personas basándose en empresa + cargo financiero"""
    
    def __init__(self):
        """Inicializar clasificador"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        print("✅ AI Person Classifier inicializado")
    
    def is_financial_decision_maker(self, title: str, seniority: str) -> tuple:
        """
        Determina si la persona es un tomador de decisiones financieras
        
        Returns:
            (es_decision_maker, razon, score)
        """
        if not title:
            return False, "Sin título", 0
        
        title_lower = title.lower()
        seniority_lower = (seniority or '').lower()
        
        # Cargos financieros clave
        financial_keywords = [
            'cfo', 'chief financial officer', 'director financiero', 'gerente de finanzas',
            'gerente financiero', 'contralor', 'controller', 'tesorero', 'treasurer',
            'director de finanzas', 'financial director', 'financial manager',
            'gerente general', 'general manager', 'ceo', 'presidente', 'president',
            'dueño', 'owner', 'propietario', 'socio', 'partner'
        ]
        
        # Cargos de nivel senior que toman decisiones
        senior_keywords = [
            'director', 'gerente', 'manager', 'jefe', 'head', 'leader'
        ]
        
        # Verificar cargo financiero directo
        for keyword in financial_keywords:
            if keyword in title_lower:
                return True, f"Cargo financiero: {keyword}", 50
        
        # Verificar si es senior + tiene responsabilidad
        is_senior = any(keyword in title_lower for keyword in senior_keywords)
        has_seniority = 'c-suite' in seniority_lower or 'c suite' in seniority_lower or 'executive' in seniority_lower
        
        if is_senior or has_seniority:
            # Verificar si tiene alguna responsabilidad financiera
            financial_responsibility_keywords = [
                'finanzas', 'financial', 'contabilidad', 'accounting', 'presupuesto', 'budget',
                'tesorería', 'treasury', 'inversión', 'investment'
            ]
            
            if any(keyword in title_lower for keyword in financial_responsibility_keywords):
                return True, f"Senior con responsabilidad financiera: {title}", 40
            else:
                return False, f"Senior pero sin responsabilidad financiera: {title}", 20
        
        return False, f"No es tomador de decisiones financieras: {title}", 0
    
    def calculate_person_score(self, company_score: int, is_decision_maker: bool, decision_maker_score: int) -> int:
        """
        Calcula score final de la persona
        
        Args:
            company_score: Score de la empresa (0-100)
            is_decision_maker: Si es tomador de decisiones
            decision_maker_score: Score por ser tomador de decisiones (0-50)
        
        Returns:
            Score final (0-100)
        """
        # Score base: 50% del score de la empresa
        base_score = company_score // 2
        
        # Score adicional por ser tomador de decisiones
        decision_score = decision_maker_score if is_decision_maker else 0
        
        # Score total
        total_score = base_score + decision_score
        
        # Asegurar que no exceda 100
        return min(total_score, 100)
    
    def determine_person_classification(self, person_score: int, is_decision_maker: bool) -> str:
        """Determina clasificación basada en score y si es tomador de decisiones"""
        # Solo INCLUIR si es tomador de decisiones financieras
        if is_decision_maker and person_score >= 70:
            return "INCLUIR"
        elif is_decision_maker and person_score >= 50:
            return "REVISAR"
        else:
            # Cualquier persona que NO es gerente/director/dueño queda EXCLUIR
            return "EXCLUIR"
    
    def classify_person(self, person_id: str) -> dict:
        """Clasificar una persona específica"""
        
        # Obtener datos de la persona
        result = self.supabase.table('apollo_persons').select('*').eq('id', person_id).execute()
        
        if not result.data:
            return {"error": "Persona no encontrada"}
        
        person = result.data[0]
        
        # Verificar que tenga clasificación de empresa
        company_score = person.get('company_ai_score')
        company_classification = person.get('company_ai_classification')
        
        if company_score is None or not company_classification:
            return {
                "error": "Persona no tiene clasificación de empresa",
                "person_name": person.get('full_name')
            }
        
        # Analizar si es tomador de decisiones financieras
        title = person.get('title', '')
        seniority = person.get('seniority', '')
        
        is_decision_maker, reason, decision_maker_score = self.is_financial_decision_maker(title, seniority)
        
        # Calcular score final
        person_score = self.calculate_person_score(company_score, is_decision_maker, decision_maker_score)
        
        # Determinar clasificación
        person_classification = self.determine_person_classification(person_score, is_decision_maker)
        
        return {
            "person_id": person_id,
            "person_name": person.get('full_name'),
            "title": title,
            "company_name": person.get('company_name'),
            "company_score": company_score,
            "company_classification": company_classification,
            "is_decision_maker": is_decision_maker,
            "decision_maker_reason": reason,
            "decision_maker_score": decision_maker_score,
            "person_score": person_score,
            "person_classification": person_classification
        }
    
    def classify_all_persons_with_company_score(self):
        """Clasificar todas las personas que tienen score de empresa"""
        
        print("=" * 80)
        print("🤖 CLASIFICACIÓN DE PERSONAS")
        print("=" * 80)
        
        # Buscar personas con score de empresa
        result = self.supabase.table('apollo_persons').select('id, full_name, title, company_name, company_ai_score, company_ai_classification').execute()
        
        # Filtrar personas con score de empresa
        persons_with_company_score = [p for p in result.data if p.get('company_ai_score') is not None]
        
        if not persons_with_company_score:
            print("❌ No hay personas con score de empresa")
            return
        
        persons = persons_with_company_score
        print(f"\n📊 Personas a clasificar: {len(persons)}")
        
        stats = {
            'total': 0,
            'incluir': 0,
            'revisar': 0,
            'excluir': 0,
            'decision_makers': 0,
            'updated': 0
        }
        
        # Clasificar cada persona
        for person in persons:
            person_id = person['id']
            person_name = person['full_name']
            title = person.get('title', 'N/A')
            
            classification = self.classify_person(person_id)
            
            if 'error' in classification:
                print(f"⚠️  {person_name}: {classification['error']}")
                continue
            
            stats['total'] += 1
            
            # Contar clasificaciones
            person_classification = classification['person_classification']
            stats[person_classification.lower()] += 1
            
            if classification['is_decision_maker']:
                stats['decision_makers'] += 1
            
            # Actualizar en base de datos
            try:
                update_result = self.supabase.table('apollo_persons').update({
                    'ai_score': classification['person_score'],
                    'ai_classification': person_classification
                }).eq('id', person_id).execute()
                
                if update_result.data:
                    stats['updated'] += 1
                    print(f"✅ {person_name} ({title}) - {person_classification} ({classification['person_score']})")
            
            except Exception as e:
                print(f"❌ Error actualizando {person_name}: {e}")
        
        # Mostrar resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN")
        print("=" * 80)
        print(f"Total clasificadas: {stats['total']}")
        print(f"✅ INCLUIR: {stats['incluir']}")
        print(f"⚠️  REVISAR: {stats['revisar']}")
        print(f"❌ EXCLUIR: {stats['excluir']}")
        print(f"🎯 Tomadores de decisiones: {stats['decision_makers']}")
        print(f"💾 Actualizadas en DB: {stats['updated']}")
        print("=" * 80)


def main():
    """Función principal"""
    try:
        classifier = AIPersonClassifier()
        classifier.classify_all_persons_with_company_score()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Sistema Completo: Análisis de Empresa con Perplexity + IA
Combina análisis de Perplexity y clasificación con IA en un solo flujo
"""

import os
import sys
import json
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

# Importar función de Perplexity existente
from quantex.core.web_tools import get_perplexity_synthesis


class CompleteCompanyAnalyzer:
    """Sistema completo: Perplexity + IA"""
    
    def __init__(self):
        """Inicializar analizador"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        print("✅ Complete Company Analyzer inicializado")
    
    def get_test_company(self):
        """Obtener empresa de prueba"""
        result = self.supabase.table('apollo_companies').select('*').order('created_at', desc=False).limit(1).execute()
        
        if not result.data:
            raise ValueError("No hay empresas en apollo_companies")
        
        company = result.data[0]
        print(f"📋 Empresa: {company['name']}")
        print(f"🌐 Website: {company['website']}")
        
        return company
    
    def build_perplexity_question(self, company_name: str, website: str) -> str:
        """Construir pregunta para Perplexity"""
        question = f"¿A qué se dedica la empresa {company_name} (website: {website}) y qué tamaño tiene?"
        return question
    
    def analyze_with_perplexity(self, company: dict) -> dict:
        """PASO 1: Análisis con Perplexity"""
        print("\n" + "=" * 80)
        print("🔍 PASO 1: ANÁLISIS CON PERPLEXITY")
        print("=" * 80)
        
        company_name = company['name']
        website = company['website']
        
        # Construir pregunta
        question = self.build_perplexity_question(company_name, website)
        print(f"\n❓ Pregunta: {question}")
        
        # Llamar a Perplexity
        print(f"\n🔍 Consultando Perplexity...")
        
        try:
            response = get_perplexity_synthesis(
                question=question,
                params={"return_citations": True},
                return_full=True
            )
            
            print(f"✅ Respuesta recibida de Perplexity")
            
            # Preparar resultado
            result = {
                "company_id": company['id'],
                "company_name": company_name,
                "website": website,
                "question": question,
                "perplexity_response": response.get("text") if isinstance(response, dict) else response,
                "citations": response.get("citations") if isinstance(response, dict) else [],
                "analysis_timestamp": datetime.now().isoformat(),
                "model_used": "perplexity-sonar-pro"
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error consultando Perplexity: {e}")
            return {
                "company_id": company['id'],
                "company_name": company_name,
                "website": website,
                "question": question,
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    def extract_employee_count(self, perplexity_response: str) -> int:
        """Extraer número de empleados de la respuesta de Perplexity"""
        text = perplexity_response.lower()
        
        # Patrones para encontrar empleados
        patterns = [
            r'(\d+)\s*-\s*(\d+)\s*trabajadores',
            r'(\d+)\s*a\s*(\d+)\s*empleados',
            r'entre\s*(\d+)\s*y\s*(\d+)\s*trabajadores',
            r'(\d+)\s*trabajadores',
            r'(\d+)\s*empleados'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    # Rango: tomar el promedio
                    min_emp, max_emp = matches[0]
                    return (int(min_emp) + int(max_emp)) // 2
                else:
                    # Número único
                    return int(matches[0])
        
        return 0
    
    def determine_company_size(self, employee_count: int) -> tuple:
        """Determinar tamaño de empresa y score"""
        if employee_count == 0:
            return "Desconocido", 0
        
        if employee_count < 50:
            return "Pequeña", 30
        elif employee_count < 100:
            return "Pequeña-Mediana", 40
        elif employee_count < 250:
            return "Mediana", 50  # Target principal
        elif employee_count < 500:
            return "Mediana-Grande", 40
        else:
            return "Grande", 30
    
    def analyze_import_export_activity(self, perplexity_response: str) -> tuple:
        """Analizar actividad de importación/exportación"""
        text = perplexity_response.lower()
        
        # Palabras clave de importación/exportación
        import_export_keywords = [
            'importación', 'exportación', 'import', 'export',
            'comercio exterior', 'internacional', 'distribución internacional',
            'envases descartables', 'productos importados'
        ]
        
        # Verificar actividad internacional
        has_activity = any(keyword in text for keyword in import_export_keywords)
        
        if has_activity:
            return "Importación/Exportación", 50
        else:
            return "Sin actividad internacional", 0
    
    def generate_ai_analysis_report(self, company_name: str, perplexity_response: str, 
                                   employee_count: int, company_size: str, size_score: int,
                                   activity_type: str, activity_score: int, 
                                   total_score: int, classification: str) -> str:
        """Generar informe detallado de análisis"""
        
        report = f"""ANÁLISIS DE EMPRESA: {company_name.upper()}

TAMAÑO DE EMPRESA: {company_size.upper()}
- Empleados estimados: {employee_count} trabajadores
- Score por tamaño: {size_score} puntos
- Evaluación: {'⭐ TARGET PRINCIPAL' if company_size == 'Mediana' else 'Candidato'}

ACTIVIDAD INTERNACIONAL: {activity_type.upper()}
- Score por actividad: {activity_score} puntos
- Evaluación: {'✅ Actividad clara de importación/exportación' if activity_score > 0 else '❌ Sin actividad internacional identificada'}

SCORE TOTAL: {total_score}/100
CLASIFICACIÓN: {classification}

RAZONAMIENTO:
"""
        
        if classification == "INCLUIR":
            report += f"- Empresa {company_size.lower()} con actividad clara de importación/exportación\n"
            report += f"- Ideal para servicios de asesoría en tipo de cambio\n"
            report += f"- Tamaño adecuado para servicios financieros personalizados\n"
        elif classification == "REVISAR":
            report += f"- Empresa {company_size.lower()} con potencial\n"
            report += f"- Requiere evaluación manual adicional\n"
            report += f"- Posible candidato para servicios financieros\n"
        else:
            report += f"- Empresa {company_size.lower()} sin actividad internacional clara\n"
            report += f"- No es candidato principal para servicios de tipo de cambio\n"
            report += f"- Considerar para otros servicios financieros\n"
        
        report += f"""
INFORMACIÓN ADICIONAL:
- Análisis basado en respuesta de Perplexity
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Criterios: Tamaño de empresa + Actividad internacional
"""
        
        return report
    
    def analyze_with_ai(self, perplexity_result: dict) -> dict:
        """PASO 2: Análisis con IA"""
        print("\n" + "=" * 80)
        print("🤖 PASO 2: ANÁLISIS CON IA")
        print("=" * 80)
        
        company_name = perplexity_result['company_name']
        perplexity_response = perplexity_result.get('perplexity_response', '')
        
        if not perplexity_response:
            return {
                "error": "No hay respuesta de Perplexity para analizar",
                "ai_score": 0,
                "ai_classification": "EXCLUIR"
            }
        
        print(f"🔍 Analizando respuesta de Perplexity para {company_name}")
        
        # 1. Extraer número de empleados
        employee_count = self.extract_employee_count(perplexity_response)
        print(f"   👥 Empleados estimados: {employee_count}")
        
        # 2. Determinar tamaño de empresa
        company_size, size_score = self.determine_company_size(employee_count)
        print(f"   📊 Tamaño: {company_size} ({size_score} puntos)")
        
        # 3. Analizar actividad internacional
        activity_type, activity_score = self.analyze_import_export_activity(perplexity_response)
        print(f"   🌐 Actividad: {activity_type} ({activity_score} puntos)")
        
        # 4. Calcular score total
        total_score = size_score + activity_score
        print(f"   🎯 Score total: {total_score}/100")
        
        # 5. Determinar clasificación
        if total_score >= 70:
            classification = "INCLUIR"
        elif total_score >= 50:
            classification = "REVISAR"
        else:
            classification = "EXCLUIR"
        
        print(f"   📋 Clasificación: {classification}")
        
        # 6. Generar informe detallado
        ai_report = self.generate_ai_analysis_report(
            company_name, perplexity_response, employee_count,
            company_size, size_score, activity_type, activity_score,
            total_score, classification
        )
        
        return {
            "ai_score": total_score,
            "ai_classification": classification,
            "ai_analysis_report": ai_report,
            "analysis_details": {
                "employee_count": employee_count,
                "company_size": company_size,
                "size_score": size_score,
                "activity_type": activity_type,
                "activity_score": activity_score,
                "total_score": total_score
            }
        }
    
    def save_to_database(self, company_id: str, perplexity_result: dict, ai_result: dict) -> bool:
        """Guardar resultados en base de datos"""
        print("\n" + "=" * 80)
        print("💾 GUARDANDO EN BASE DE DATOS")
        print("=" * 80)
        
        try:
            update_data = {
                'perplexity_analysis': perplexity_result,
                'ai_score': ai_result.get('ai_score', 0),
                'ai_classification': ai_result.get('ai_classification', 'EXCLUIR'),
                'ai_analysis_report': ai_result.get('ai_analysis_report', '')
            }
            
            result = self.supabase.table('apollo_companies').update(update_data).eq('id', company_id).execute()
            
            if result.data:
                print(f"✅ Todos los datos guardados exitosamente")
                return True
            else:
                print(f"❌ Error guardando en base de datos")
                return False
                
        except Exception as e:
            print(f"❌ Error actualizando base de datos: {e}")
            return False
    
    def run_complete_analysis(self, force: bool = False):
        """Ejecutar análisis completo"""
        print("=" * 80)
        print("🚀 ANÁLISIS COMPLETO: PERPLEXITY + IA")
        print("=" * 80)
        
        try:
            # Obtener empresa de prueba
            company = self.get_test_company()
            
            # Verificar si ya existe análisis (a menos que sea force)
            if not force and company.get('perplexity_analysis'):
                print(f"\n⚠️  Esta empresa ya tiene análisis de Perplexity")
                print(f"   Usa --force para reanalizar")
                
                # Verificar si también tiene análisis de IA
                if company.get('ai_score') is not None:
                    print(f"   ✅ También tiene análisis de IA")
                    print(f"   Score: {company.get('ai_score')}/100")
                    print(f"   Clasificación: {company.get('ai_classification')}")
                    return
                else:
                    print(f"   ⚠️  Tiene Perplexity pero NO tiene análisis de IA")
                    print(f"   Ejecutando solo análisis de IA...")
                    
                    # Solo ejecutar análisis de IA
                    perplexity_result = company['perplexity_analysis']
                    ai_result = self.analyze_with_ai(perplexity_result)
                    saved = self.save_to_database(company['id'], perplexity_result, ai_result)
                    
                    print(f"\n✅ Análisis de IA completado")
                    return
            
            # PASO 1: Análisis con Perplexity
            perplexity_result = self.analyze_with_perplexity(company)
            
            if 'error' in perplexity_result:
                print(f"❌ Error en análisis de Perplexity: {perplexity_result['error']}")
                return
            
            # PASO 2: Análisis con IA
            ai_result = self.analyze_with_ai(perplexity_result)
            
            # Guardar en base de datos
            saved = self.save_to_database(company['id'], perplexity_result, ai_result)
            
            # Mostrar resumen
            print("\n" + "=" * 80)
            print("📊 RESUMEN FINAL")
            print("=" * 80)
            print(f"Empresa: {company['name']}")
            print(f"Score: {ai_result.get('ai_score', 0)}/100")
            print(f"Clasificación: {ai_result.get('ai_classification', 'EXCLUIR')}")
            print(f"Guardado en DB: {'✅ Sí' if saved else '❌ No'}")
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Error en análisis completo: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Análisis completo de empresa con Perplexity + IA')
    parser.add_argument('--force', action='store_true', help='Forzar reanálisis incluso si ya existe')
    
    args = parser.parse_args()
    
    try:
        analyzer = CompleteCompanyAnalyzer()
        analyzer.run_complete_analysis(force=args.force)
    except Exception as e:
        print(f"❌ Error inicializando: {e}")


if __name__ == "__main__":
    main()

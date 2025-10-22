#!/usr/bin/env python3
"""
AI Analysis Agent
Analiza respuesta de Perplexity y genera score + clasificación + informe
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

# Importar sistema LLM existente
from quantex.core.ai_services import ai_services


class AIAnalysisAgent:
    """Agent que analiza respuesta de Perplexity y genera clasificación"""
    
    def __init__(self):
        """Inicializar agent"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        print("✅ AI Analysis Agent inicializado")
    
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
        
        return 0  # No encontrado
    
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
    
    def analyze_perplexity_response(self, company_name: str, perplexity_response: str) -> dict:
        """Analizar respuesta de Perplexity y generar clasificación completa"""
        
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
    
    def analyze_company_from_database(self, company_id: str) -> dict:
        """Analizar empresa desde base de datos"""
        
        # Obtener empresa con análisis de Perplexity
        result = self.supabase.table('apollo_companies').select('*').eq('id', company_id).execute()
        
        if not result.data:
            return {"error": "Empresa no encontrada"}
        
        company = result.data[0]
        company_name = company['name']
        
        # Verificar que tenga análisis de Perplexity
        perplexity_analysis = company.get('perplexity_analysis')
        if not perplexity_analysis:
            return {"error": "No hay análisis de Perplexity disponible"}
        
        perplexity_response = perplexity_analysis.get('perplexity_response', '')
        if not perplexity_response:
            return {"error": "Respuesta de Perplexity vacía"}
        
        print(f"📋 Analizando empresa: {company_name}")
        
        # Analizar respuesta
        analysis = self.analyze_perplexity_response(company_name, perplexity_response)
        
        # Actualizar base de datos
        try:
            update_result = self.supabase.table('apollo_companies').update({
                'ai_score': analysis['ai_score'],
                'ai_classification': analysis['ai_classification'],
                'ai_analysis_report': analysis['ai_analysis_report']
            }).eq('id', company_id).execute()
            
            if update_result.data:
                print(f"✅ Análisis guardado en base de datos")
                analysis['saved_to_database'] = True
            else:
                print(f"❌ Error guardando en base de datos")
                analysis['saved_to_database'] = False
                
        except Exception as e:
            print(f"❌ Error actualizando base de datos: {e}")
            analysis['saved_to_database'] = False
            analysis['database_error'] = str(e)
        
        return analysis
    
    def run_test_analysis(self):
        """Ejecutar análisis de prueba"""
        print("=" * 80)
        print("🤖 ANÁLISIS DE IA: EMPRESA DE PRUEBA")
        print("=" * 80)
        
        try:
            # Usar DPS CHILE (primera empresa con análisis de Perplexity)
            result = self.supabase.table('apollo_companies').select('id, name, perplexity_analysis').limit(10).execute()
            
            if not result.data:
                print("❌ No hay empresas en la base de datos")
                return
            
            # Buscar primera empresa con análisis de Perplexity
            company = None
            for c in result.data:
                if c.get('perplexity_analysis'):
                    company = c
                    break
            
            if not company:
                print("❌ No hay empresas con análisis de Perplexity")
                return
            
            company_id = company['id']
            company_name = company['name']
            
            print(f"🎯 Analizando: {company_name}")
            
            # Ejecutar análisis
            analysis = self.analyze_company_from_database(company_id)
            
            # Mostrar resultado
            print(f"\n📊 RESULTADO DEL ANÁLISIS:")
            print("=" * 80)
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Función principal"""
    try:
        agent = AIAnalysisAgent()
        agent.run_test_analysis()
    except Exception as e:
        print(f"❌ Error inicializando: {e}")


if __name__ == "__main__":
    main()

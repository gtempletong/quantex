#!/usr/bin/env python3
"""
Sistema Completo de Clasificación: Empresas + Personas
1. Analiza empresas con Perplexity + IA
2. Copia clasificación de empresa a personas
3. Clasifica personas por cargo financiero
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


class CompleteClassificationSystem:
    """Sistema completo de clasificación: Empresas + Personas"""
    
    def __init__(self):
        """Inicializar sistema"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        print("✅ Sistema Completo de Clasificación inicializado")
    
    # ==================== PARTE 1: ANÁLISIS DE EMPRESAS ====================
    
    def analyze_company_with_perplexity(self, company: dict) -> dict:
        """PASO 1: Análisis con Perplexity"""
        company_name = company['name']
        website = company['website']
        
        question = f"¿A qué se dedica la empresa {company_name} (website: {website}) y qué tamaño tiene?"
        
        print(f"   ❓ Pregunta: {question}")
        print(f"   🔍 Consultando Perplexity...")
        
        try:
            response = get_perplexity_synthesis(
                question=question,
                params={"return_citations": True},
                return_full=True
            )
            
            print(f"   ✅ Respuesta recibida")
            
            return {
                "company_id": company['id'],
                "company_name": company_name,
                "website": website,
                "company_country": company.get('country'),
                "company_location": company.get('location'),
                "question": question,
                "perplexity_response": response.get("text") if isinstance(response, dict) else response,
                "citations": response.get("citations") if isinstance(response, dict) else [],
                "analysis_timestamp": datetime.now().isoformat(),
                "model_used": "perplexity-sonar-pro"
            }
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                "company_id": company['id'],
                "company_name": company_name,
                "error": str(e)
            }
    
    def extract_employee_count(self, perplexity_response: str) -> int:
        """Extraer número de empleados"""
        text = perplexity_response.lower()
        
        patterns = [
            r'(\d+)\s*-\s*(\d+)\s*trabajadores',
            r'(\d+)\s*a\s*(\d+)\s*empleados',
            r'entre\s*(\d+)\s*y\s*(\d+)\s*trabajadores',
            r'alrededor\s+de\s+(\d+)\s+empleados',
            r'aproximadamente\s+(\d+)\s+empleados',
            r'cerca\s+de\s+(\d+)\s+empleados',
            r'unos?\s+(\d+)\s+empleados',
            r'(\d+)\s*trabajadores',
            r'(\d+)\s*empleados'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    min_emp, max_emp = matches[0]
                    return (int(min_emp) + int(max_emp)) // 2
                else:
                    return int(matches[0])
        
        return 0
    
    def determine_company_size(self, employee_count: int) -> tuple:
        """Determinar tamaño de empresa y score (optimizado para ventaja competitiva)"""
        if employee_count == 0:
            return "Desconocido", 0
        
        # VENTAJA COMPETITIVA: Empresas pequeñas y medianas
        if employee_count < 50:
            return "Pequeña", 45  # ✅ Tu ventaja competitiva
        elif employee_count < 100:
            return "Pequeña-Mediana", 50  # ⭐ SWEET SPOT - Máxima ventaja competitiva
        elif employee_count < 250:
            return "Mediana", 50  # ⭐ TARGET PRINCIPAL - Máxima ventaja competitiva
        elif employee_count < 500:
            return "Mediana-Grande", 35  # ⚠️ Score medio
        else:
            return "Grande", 20  # ❌ Sin ventaja competitiva (grandes corporativos)
    
    def analyze_company_with_ai_complete(self, perplexity_response: str, company_name: str, company_country: str = None, company_location: str = None) -> dict:
        """Análisis COMPLETO con Claude Sonnet 4 - TODO en una sola llamada"""
        
        # Contexto adicional de Apollo.io
        apollo_context = ""
        if company_country or company_location:
            apollo_context = f"\n\nCONTEXTO ADICIONAL (de Apollo.io):\n"
            if company_country:
                apollo_context += f"- País registrado en Apollo: {company_country}\n"
            if company_location:
                apollo_context += f"- Ubicación registrada: {company_location}\n"
        
        prompt = f"""Eres un agente experto en clasificar empresas chilenas para servicios de cobertura cambiaria.

Analiza la siguiente empresa y determina si es un buen target comercial.

INFORMACIÓN DE LA EMPRESA:
{perplexity_response}{apollo_context}

⚠️ FILTRO GEOGRÁFICO:

REGLAS SIMPLES:
- Si claramente opera EN CHILE → Evalúa normalmente
- Si claramente NO opera en Chile (ej: empresa egipcia sin mención de Chile) → EXCLUIR
- Si tienes DUDA sobre la presencia en Chile → Usa REVISAR (para revisión manual)

IMPORTANTE: Los datos vienen de Apollo.io filtrados por Chile, así que probablemente tienen alguna conexión con Chile.

Ante la duda, es mejor clasificar como REVISAR que como EXCLUIR.

CRITERIOS DE EVALUACIÓN:

1. TAMAÑO DE LA EMPRESA (máximo 50 puntos):
   Analiza cuántos empleados tiene la empresa y asigna puntos según:
   
   - Pequeña (<50 empleados): 45 puntos ⭐ Ventaja competitiva alta
   - Pequeña-Mediana (50-100 empleados): 50 puntos ⭐⭐ SWEET SPOT - Target ideal
   - Mediana (100-250 empleados): 50 puntos ⭐⭐ TARGET PRINCIPAL - Target ideal
   - Mediana-Grande (250-500 empleados): 35 puntos - Target secundario
   - Grande (500+ empleados): 20 puntos - Sin ventaja competitiva (corporativos grandes)
   
   IMPORTANTE: Si NO hay número exacto de empleados, haz tu MEJOR ESTIMACIÓN basándote en:
   - Número de tiendas/sucursales mencionadas
   - Alcance geográfico (local, regional, nacional)
   - Tipo de operación (1 tienda = pequeña, cadena = mediana/grande)
   - Volumen de negocio mencionado
   - Clientes que atiende
   
   EJEMPLOS:
   - "Opera 2 tiendas en centros comerciales" → Estima ~20-40 empleados → Pequeña (45 pts)
   - "Cadena con presencia nacional, varias sucursales" → Estima ~100-200 → Mediana (50 pts)
   - "Distribuye a toda la industria nacional" → Estima ~80-150 → Mediana (50 pts)
   
   Solo usa "Desconocido" (0 pts) si realmente NO hay NINGÚN indicador

2. ACTIVIDAD DE IMPORTACIÓN/EXPORTACIÓN (máximo 50 puntos):
   
   REGLA CLAVE: Chile NO fabrica localmente la mayoría de productos manufacturados, ingredientes industriales, maquinaria o tecnología.
   
   Asigna 50 puntos SI:
   - Menciona explícitamente importación/exportación/comercio exterior
   - Vende productos manufacturados (ropa, tecnología, productos para el hogar, etc.)
   - Distribuye ingredientes, materias primas, equipamiento industrial
   - Vende commodities chilenos (cobre, frutas, vino, salmón, madera)
   - Provee/comercializa productos que Chile NO fabrica
   
   Asigna 0 puntos SI:
   - Solo servicios locales (software, consultoría, servicios profesionales)
   - Producción 100% local (panadería, pastelería fresca)
   - Servicios presenciales (restaurantes, clínicas, gimnasios)

3. CLASIFICACIÓN FINAL:
   - EXCLUIR: Si la empresa NO está en Chile (filtro geográfico prioritario)
   - EXCLUIR: Score < 50 (no es target)
   - REVISAR: Score 50-69 (requiere evaluación manual)
   - INCLUIR: Score >= 70 (target prioritario)

RESPONDE EN FORMATO JSON (solo el JSON, sin texto adicional):
{{
  "is_in_chile": true | false,
  "location_reasoning": "<breve explicación de dónde opera la empresa>",
  "employee_count": <número estimado de empleados o 0 si desconocido>,
  "company_size": "Pequeña" | "Pequeña-Mediana" | "Mediana" | "Mediana-Grande" | "Grande" | "Desconocido",
  "size_score": <0-50 si is_in_chile=true, 0 si is_in_chile=false>,
  "size_reasoning": "<breve explicación del tamaño y score asignado>",
  "has_import_export": true | false,
  "import_export_reasoning": "<explicación de por qué sí o no tiene actividad internacional>",
  "activity_score": <0 o 50 si is_in_chile=true, 0 si is_in_chile=false>,
  "total_score": <0 si is_in_chile=false, sino suma de size_score + activity_score>,
  "classification": "EXCLUIR si is_in_chile=false" | "INCLUIR" | "REVISAR" | "EXCLUIR",
  "final_reasoning": "<resumen ejecutivo: por qué es o no es un buen target>"
}}"""

        try:
            import anthropic
            import json
            
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            print(f"      🤖 Consultando Claude Sonnet 4 para análisis COMPLETO...")
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text.strip()
            print(f"      💬 Claude responde...")
            
            # Extraer JSON de la respuesta
            # Buscar el JSON en la respuesta (puede venir con ```json o sin nada)
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = response_text.strip()
            
            # Parsear JSON
            analysis = json.loads(json_text)
            
            # Verificar ubicación
            is_in_chile = analysis.get("is_in_chile", True)  # Default True para compatibilidad
            
            if not is_in_chile:
                print(f"      🌍 Ubicación: FUERA DE CHILE → EXCLUIR automáticamente")
                print(f"      💬 {analysis.get('location_reasoning', 'No opera en Chile')}")
            else:
                print(f"      🇨🇱 Ubicación: CHILE ✅")
            
            print(f"      📊 Tamaño: {analysis['company_size']} ({analysis['size_score']} pts)")
            print(f"      🌐 Import/Export: {'Sí' if analysis['has_import_export'] else 'No'} ({analysis['activity_score']} pts)")
            
            # Normalizar clasificación (máximo 20 caracteres)
            raw_classification = analysis['classification']
            if 'INCLUIR' in raw_classification.upper():
                normalized_classification = 'INCLUIR'
            elif 'REVISAR' in raw_classification.upper():
                normalized_classification = 'REVISAR'
            else:
                normalized_classification = 'EXCLUIR'
            
            print(f"      🎯 Score Total: {analysis['total_score']}/100 → {normalized_classification}")
            
            return {
                "success": True,
                "is_in_chile": is_in_chile,
                "employee_count": analysis["employee_count"],
                "company_size": analysis["company_size"],
                "size_score": analysis["size_score"],
                "has_import_export": analysis["has_import_export"],
                "activity_score": analysis["activity_score"],
                "total_score": analysis["total_score"],
                "classification": normalized_classification,
                "reasoning": {
                    "location": analysis.get("location_reasoning", ""),
                    "size": analysis["size_reasoning"],
                    "import_export": analysis["import_export_reasoning"],
                    "final": analysis["final_reasoning"]
                }
            }
            
        except Exception as e:
            print(f"      ⚠️  Error en análisis completo con Claude: {e}")
            # Fallback al sistema antiguo
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_import_export_activity(self, perplexity_response: str) -> tuple:
        """Analizar actividad de importación/exportación usando IA (Claude)"""
        
        # Prompt embebido para el agente clasificador
        prompt = f"""Eres un agente clasificador de empresas chilenas. Tu trabajo es identificar si tienen actividad de importación/exportación.

REGLA DE ORO: Chile NO fabrica localmente la mayoría de productos manufacturados, ingredientes industriales, maquinaria o tecnología. Si una empresa VENDE o DISTRIBUYE estos productos → casi siempre LOS IMPORTA.

DESCRIPCIÓN DE LA EMPRESA:
{perplexity_response}

RESPONDE "SI" si la empresa:

1. MENCIONA EXPLÍCITAMENTE:
   ✅ "importación", "exportación", "comercio exterior", "internacional"
   ✅ Vende commodities chilenos: cobre, litio, frutas, vino, salmón, madera
   ✅ Opera en mercados extranjeros o tiene clientes internacionales

2. RETAIL / VENTA DE PRODUCTOS MANUFACTURADOS:
   ✅ Ropa, zapatillas, accesorios (marcas internacionales o no)
   ✅ Electrónica, tecnología, computadores, celulares
   ✅ Productos para el hogar, cocina, decoración
   ✅ Juguetes, deportes, fitness, outdoor
   ✅ Muebles, electrodomésticos
   
   EJEMPLO: "vende productos para el hogar de diseño nórdico" → SÍ (importa de Europa)
   EJEMPLO: "retail de zapatillas y ropa urbana" → SÍ (importa de Asia/USA)

3. DISTRIBUCIÓN / PROVISIÓN DE INSUMOS:
   ✅ Ingredientes, materias primas, químicos, aditivos
   ✅ Equipamiento industrial, maquinaria, tecnología
   ✅ Repuestos, herramientas, suministros técnicos
   ✅ Materiales de construcción, ferretería especializada
   
   EJEMPLO: "provee ingredientes y equipamiento para industria alimentaria" → SÍ (importa)
   EJEMPLO: "distribuye insumos para enología" → SÍ (importa)

4. INDICADORES CLAVE:
   ✅ Dice "provee", "distribuye", "comercializa" productos físicos
   ✅ Menciona "marcas internacionales", "productos europeos/asiáticos/americanos"
   ✅ Describe productos que claramente NO se fabrican en Chile

RESPONDE "NO" SOLO si:
   ❌ Producción 100% local (panaderías, pastelerías, alimentos frescos locales)
   ❌ Servicios puros sin productos: software local, consultoría, servicios profesionales
   ❌ Servicios presenciales: restaurantes, clínicas, gimnasios, salones
   ❌ Construcción, inmobiliarias (servicios locales)
   
   EJEMPLO: "plataforma digital SaaS" → NO (software local)
   EJEMPLO: "pastelería con producción local" → NO (fabrica localmente)

FORMATO DE RESPUESTA:
SI - [razón breve de por qué importa/exporta]
o
NO - [razón breve de por qué no tiene comercio internacional]"""

        try:
            import anthropic
            
            # Usar Claude Sonnet 4 para análisis inteligente
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            print(f"      🤖 Consultando IA para análisis de actividad internacional...")
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response = message.content[0].text.strip()
            print(f"      💬 IA responde: {response[:100]}...")
            
            # Analizar respuesta
            if response.upper().startswith("SI"):
                return "Importación/Exportación", 50
            else:
                return "Sin actividad internacional", 0
                
        except Exception as e:
            print(f"      ⚠️  Error en análisis de IA, usando keywords como fallback: {e}")
            # Fallback a keywords si falla la IA
            text = perplexity_response.lower()
        import_export_keywords = [
            'importación', 'exportación', 'import', 'export',
            'comercio exterior', 'internacional', 'distribución internacional',
                'productos importados'
        ]
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
    
    def analyze_company_with_ai(self, perplexity_result: dict) -> dict:
        """PASO 2: Análisis con IA (VERSIÓN COMPLETA CON CLAUDE)"""
        company_name = perplexity_result['company_name']
        perplexity_response = perplexity_result.get('perplexity_response', '')
        
        if not perplexity_response:
            return {
                "error": "No hay respuesta de Perplexity",
                "ai_score": 0,
                "ai_classification": "EXCLUIR"
            }
        
        # INTENTAR ANÁLISIS COMPLETO CON CLAUDE
        print(f"\n   🤖 ANÁLISIS COMPLETO CON CLAUDE SONNET 4")
        
        # Obtener country y location del resultado de Perplexity (viene de apollo_companies)
        company_country = perplexity_result.get('company_country')
        company_location = perplexity_result.get('company_location')
        
        claude_analysis = self.analyze_company_with_ai_complete(
            perplexity_response, 
            company_name,
            company_country,
            company_location
        )
        
        if claude_analysis.get("success"):
            # Claude analizó todo exitosamente
            employee_count = claude_analysis["employee_count"]
            company_size = claude_analysis["company_size"]
            size_score = claude_analysis["size_score"]
            activity_score = claude_analysis["activity_score"]
            total_score = claude_analysis["total_score"]
            classification = claude_analysis["classification"]
            
            # Generar activity_type para el reporte
            activity_type = "Importación/Exportación" if claude_analysis["has_import_export"] else "Sin actividad internacional"
            
            # Generar informe detallado con el razonamiento de Claude
            ai_report = f"""ANÁLISIS DE EMPRESA: {company_name.upper()}

UBICACIÓN GEOGRÁFICA: {'🇨🇱 CHILE' if claude_analysis.get('is_in_chile', True) else '🌍 FUERA DE CHILE'}
- {claude_analysis['reasoning'].get('location', 'Sin información de ubicación')}

TAMAÑO DE EMPRESA: {company_size.upper()}
- Empleados estimados: {employee_count} trabajadores
- Score por tamaño: {size_score} puntos
- Evaluación: {'⭐ TARGET PRINCIPAL' if company_size in ['Mediana', 'Pequeña-Mediana'] else 'Candidato'}
- Razonamiento: {claude_analysis['reasoning']['size']}

ACTIVIDAD INTERNACIONAL: {activity_type.upper()}
- Score por actividad: {activity_score} puntos
- Evaluación: {'✅ Actividad clara de importación/exportación' if activity_score > 0 else '❌ Sin actividad internacional identificada'}
- Razonamiento: {claude_analysis['reasoning']['import_export']}

SCORE TOTAL: {total_score}/100
CLASIFICACIÓN: {classification}

RAZONAMIENTO FINAL:
{claude_analysis['reasoning']['final']}

INFORMACIÓN ADICIONAL:
- Análisis generado por Claude Sonnet 4
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Criterios: Tamaño de empresa + Actividad internacional
"""
            
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
                    "reasoning": claude_analysis['reasoning']
                }
            }
        
        else:
            # FALLBACK: Sistema antiguo (regex + keywords)
            print(f"   ⚠️  Usando sistema antiguo como fallback")
            
        employee_count = self.extract_employee_count(perplexity_response)
        company_size, size_score = self.determine_company_size(employee_count)
        activity_type, activity_score = self.analyze_import_export_activity(perplexity_response)
        
        total_score = size_score + activity_score
        
        if total_score >= 70:
            classification = "INCLUIR"
        elif total_score >= 50:
            classification = "REVISAR"
        else:
            classification = "EXCLUIR"
        
        print(f"   📊 Tamaño: {company_size} ({size_score} puntos)")
        print(f"   🌐 Actividad: {activity_type} ({activity_score} puntos)")
        print(f"   🎯 Score: {total_score}/100 → {classification}")
        
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
                "activity_score": activity_score
            }
        }
    
    # ==================== PARTE 2: CLASIFICACIÓN DE PERSONAS ====================
    
    def find_persons_by_company_name(self, company_name: str):
        """Buscar personas por nombre de empresa"""
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
        
        # Eliminar duplicados
        seen_ids = set()
        unique_persons = []
        for person in persons:
            if person['id'] not in seen_ids:
                seen_ids.add(person['id'])
                unique_persons.append(person)
        
        return unique_persons
    
    def is_financial_decision_maker(self, title: str, seniority: str) -> tuple:
        """Determina si la persona es tomador de decisiones financieras"""
        if not title:
            return False, "Sin título", 0
        
        title_lower = title.lower()
        seniority_lower = (seniority or '').lower()
        
        # Cargos financieros clave
        financial_keywords = [
            'cfo', 'chief financial officer', 'director financiero', 'gerente de finanzas',
            'gerente financiero', 'contralor', 'controller', 'tesorero', 'treasurer',
            'director de finanzas', 'financial director', 'financial manager',
            'gerente general', 'general manager', 'ceo', 'chief executive officer',
            'presidente', 'president', 'dueño', 'owner', 'propietario', 'socio', 'partner'
        ]
        
        # Verificar cargo financiero directo
        for keyword in financial_keywords:
            if keyword in title_lower:
                return True, f"Cargo financiero: {keyword}", 50
        
        # Verificar si es senior
        senior_keywords = ['director', 'gerente', 'manager', 'jefe', 'head', 'leader']
        is_senior = any(keyword in title_lower for keyword in senior_keywords)
        has_seniority = 'c-suite' in seniority_lower or 'c suite' in seniority_lower or 'executive' in seniority_lower
        
        if is_senior or has_seniority:
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
        """Calcula score final de la persona"""
        base_score = company_score // 2
        decision_score = decision_maker_score if is_decision_maker else 0
        return min(base_score + decision_score, 100)
    
    def determine_person_classification(self, person_score: int, is_decision_maker: bool) -> str:
        """Determina clasificación de persona"""
        if is_decision_maker and person_score >= 70:
            return "INCLUIR"
        elif is_decision_maker and person_score >= 50:
            return "REVISAR"
        else:
            return "EXCLUIR"
    
    def classify_persons_for_company(self, company: dict, company_score: int, company_classification: str) -> dict:
        """Clasificar personas de una empresa"""
        company_name = company['name']
        
        # Buscar personas
        persons = self.find_persons_by_company_name(company_name)
        
        if not persons:
            return {'persons_found': 0, 'persons_updated': 0}
        
        print(f"   👥 Personas encontradas: {len(persons)}")
        
        # Si la empresa está EXCLUIDA, marcar todas las personas como EXCLUIR
        if company_classification == "EXCLUIR":
            print(f"   ❌ Empresa EXCLUIDA → Todas las personas se marcan como EXCLUIR")
            updated_count = 0
            for person in persons:
                try:
                    justification = f"❌ EXCLUIR (0/100) - Empresa clasificada como EXCLUIR ({company_score}/100). No es target prioritario."
                    
                    self.supabase.table('apollo_persons').update({
                        'company_ai_score': company_score,
                        'company_ai_classification': company_classification,
                        'company_analyzed': company_name,
                        'ai_score': 0,
                        'ai_classification': 'EXCLUIR',
                        'ai_justification': justification,
                        'ai_analyzed_at': datetime.now().isoformat()
                    }).eq('id', person['id']).execute()
                    updated_count += 1
                except Exception as e:
                    print(f"      ❌ Error actualizando {person['full_name']}: {e}")
            
            return {
                'persons_found': len(persons),
                'persons_updated': updated_count
            }
        
        # Si empresa es INCLUIR o REVISAR, analizar cada persona
        print(f"   ✅ Empresa {company_classification} → Analizando personas individualmente")
        updated_count = 0
        for person in persons:
            person_id = person['id']
            person_name = person['full_name']
            title = person.get('title', '')
            seniority = person.get('seniority', '')
            
            # Analizar si es tomador de decisiones
            is_decision_maker, reason, decision_maker_score = self.is_financial_decision_maker(title, seniority)
            
            # Calcular score
            person_score = self.calculate_person_score(company_score, is_decision_maker, decision_maker_score)
            
            # Clasificación
            person_classification = self.determine_person_classification(person_score, is_decision_maker)
            
            # Generar justificación
            if person_classification == 'INCLUIR':
                justification = f"✅ INCLUIR ({person_score}/100) - {reason}. Empresa: {company_classification} ({company_score}/100)"
            elif person_classification == 'REVISAR':
                justification = f"⚠️ REVISAR ({person_score}/100) - {reason}. Empresa: {company_classification} ({company_score}/100)"
            else:
                justification = f"❌ EXCLUIR ({person_score}/100) - {reason}. Empresa: {company_classification} ({company_score}/100)"
            
            # Actualizar en base de datos
            try:
                self.supabase.table('apollo_persons').update({
                    'company_ai_score': company_score,
                    'company_ai_classification': company_classification,
                    'company_analyzed': company_name,
                    'ai_score': person_score,
                    'ai_classification': person_classification,
                    'ai_justification': justification,
                    'ai_analyzed_at': datetime.now().isoformat()
                }).eq('id', person_id).execute()
                
                updated_count += 1
                if person_classification == 'INCLUIR':
                    print(f"      ✅ {person_name} ({title}) - INCLUIR ({person_score})")
            
            except Exception as e:
                print(f"      ❌ Error actualizando {person_name}: {e}")
        
        return {
            'persons_found': len(persons),
            'persons_updated': updated_count
        }
    
    # ==================== PARTE 2.5: MODO INTERACTIVO DE SELECCIÓN ====================
    
    def interactive_company_selector(self):
        """Modo interactivo: permite seleccionar qué empresas procesar"""
        print("=" * 80)
        print("🎯 MODO INTERACTIVO - SELECCIÓN DE EMPRESAS")
        print("=" * 80)
        
        # Obtener estadísticas
        all_companies = self.supabase.table('apollo_companies').select('*').order('name').execute().data
        companies_without_analysis = [c for c in all_companies if not c.get('perplexity_analysis')]
        companies_with_analysis = [c for c in all_companies if c.get('perplexity_analysis')]
        
        print(f"\n📊 ESTADO:")
        print(f"   Total empresas: {len(all_companies)}")
        print(f"   ✅ Con análisis: {len(companies_with_analysis)}")
        print(f"   ⏳ Sin análisis: {len(companies_without_analysis)}")
        
        while True:
            print("\n" + "=" * 80)
            print("🔍 OPCIONES:")
            print("=" * 80)
            print("1. Ver lista de empresas SIN análisis")
            print("2. Ver lista de empresas CON análisis")
            print("3. Buscar empresa por nombre")
            print("4. Procesar siguiente empresa sin análisis")
            print("5. Procesar múltiples empresas (batch)")
            print("0. Salir")
            
            choice = input("\n👉 Selecciona una opción (0-5): ").strip()
            
            if choice == "0":
                print("\n👋 Saliendo...")
                break
                
            elif choice == "1":
                # Listar empresas sin análisis
                if not companies_without_analysis:
                    print("\n✅ Todas las empresas ya tienen análisis")
                    continue
                    
                print(f"\n📋 EMPRESAS SIN ANÁLISIS ({len(companies_without_analysis)}):")
                for i, company in enumerate(companies_without_analysis, 1):
                    print(f"   {i:3}. {company['name']}")
                
                # Opción para procesar alguna de la lista
                process_num = input(f"\n¿Procesar alguna? (1-{len(companies_without_analysis)} o 'n'): ").strip()
                if process_num.isdigit() and 1 <= int(process_num) <= len(companies_without_analysis):
                    company = companies_without_analysis[int(process_num) - 1]
                    self._process_single_company(company)
                    # Actualizar listas
                    all_companies = self.supabase.table('apollo_companies').select('*').order('name').execute().data
                    companies_without_analysis = [c for c in all_companies if not c.get('perplexity_analysis')]
                    companies_with_analysis = [c for c in all_companies if c.get('perplexity_analysis')]
                    
            elif choice == "2":
                # Listar empresas con análisis
                if not companies_with_analysis:
                    print("\n⚠️ No hay empresas con análisis")
                    continue
                    
                print(f"\n📋 EMPRESAS CON ANÁLISIS ({len(companies_with_analysis)}):")
                for i, company in enumerate(companies_with_analysis, 1):
                    score = company.get('ai_score', 'N/A')
                    classification = company.get('ai_classification', 'N/A')
                    print(f"   {i:3}. {company['name']:<40} | {classification:10} | {score}/100")
                
                # Opción para reprocesar alguna de la lista
                process_num = input(f"\n¿Reprocesar alguna? (1-{len(companies_with_analysis)} o 'n'): ").strip()
                if process_num.isdigit() and 1 <= int(process_num) <= len(companies_with_analysis):
                    company = companies_with_analysis[int(process_num) - 1]
                    confirm = input(f"⚠️  Esta empresa ya tiene análisis. ¿Reprocesar '{company['name']}'? (s/n): ").strip().lower()
                    if confirm == 's':
                        self._process_single_company(company)
                        # Actualizar listas
                        all_companies = self.supabase.table('apollo_companies').select('*').order('name').execute().data
                        companies_without_analysis = [c for c in all_companies if not c.get('perplexity_analysis')]
                        companies_with_analysis = [c for c in all_companies if c.get('perplexity_analysis')]
                    
            elif choice == "3":
                # Buscar por nombre
                search_term = input("\n🔍 Nombre de empresa a buscar: ").strip()
                if not search_term:
                    continue
                    
                matches = [c for c in all_companies if search_term.lower() in c['name'].lower()]
                
                if not matches:
                    print(f"❌ No se encontraron empresas con '{search_term}'")
                    continue
                    
                print(f"\n📋 RESULTADOS ({len(matches)}):")
                for i, company in enumerate(matches, 1):
                    has_analysis = "✅" if company.get('perplexity_analysis') else "⏳"
                    score = company.get('ai_score', '-')
                    classification = company.get('ai_classification', '-')
                    print(f"   {i}. {has_analysis} {company['name']:<40} | {classification:10} | {score}/100")
                
                # Preguntar si quiere procesar alguna
                process = input("\n¿Procesar alguna? (número o 'n'): ").strip()
                if process.isdigit() and 1 <= int(process) <= len(matches):
                    company = matches[int(process) - 1]
                    self._process_single_company(company)
                    # Actualizar listas
                    companies_without_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if not c.get('perplexity_analysis')]
                    companies_with_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if c.get('perplexity_analysis')]
                    
            elif choice == "4":
                # Procesar siguiente sin análisis
                if not companies_without_analysis:
                    print("\n✅ No hay empresas sin análisis")
                    continue
                    
                company = companies_without_analysis[0]
                print(f"\n🎯 Siguiente empresa: {company['name']}")
                confirm = input("¿Procesar esta empresa? (s/n): ").strip().lower()
                
                if confirm == 's':
                    self._process_single_company(company)
                    # Actualizar listas
                    companies_without_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if not c.get('perplexity_analysis')]
                    companies_with_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if c.get('perplexity_analysis')]
                    
            elif choice == "5":
                # Procesar múltiples
                num = input("\n📊 ¿Cuántas empresas procesar? (sin análisis): ").strip()
                if num.isdigit():
                    self.process_companies(limit=int(num), force=False, interactive=False)
                    # Actualizar listas
                    companies_without_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if not c.get('perplexity_analysis')]
                    companies_with_analysis = [c for c in self.supabase.table('apollo_companies').select('*').execute().data if c.get('perplexity_analysis')]
    
    def _process_single_company(self, company: dict):
        """Procesar una sola empresa (helper para modo interactivo)"""
        print(f"\n{'='*80}")
        print(f"🏢 {company['name']}")
        print(f"{'='*80}")
        
        try:
            # PASO 1: Análisis con Perplexity
            perplexity_result = self.analyze_company_with_perplexity(company)
            
            if 'error' in perplexity_result:
                print(f"   ❌ Error en análisis de Perplexity")
                return
            
            # PASO 2: Análisis con IA
            ai_result = self.analyze_company_with_ai(perplexity_result)
            
            if 'error' in ai_result:
                print(f"   ❌ Error en análisis de IA")
                return
            
            # Guardar análisis de empresa
            self.supabase.table('apollo_companies').update({
                'perplexity_analysis': perplexity_result,
                'ai_score': ai_result['ai_score'],
                'ai_classification': ai_result['ai_classification'],
                'ai_analysis_report': ai_result.get('ai_analysis_report')
            }).eq('id', company['id']).execute()
            
            # PASO 3: Clasificar personas
            persons_result = self.classify_persons_for_company(
                company,
                ai_result['ai_score'],
                ai_result['ai_classification']
            )
            
            print(f"\n✅ Empresa procesada exitosamente")
            print(f"   Score: {ai_result['ai_score']}/100")
            print(f"   Clasificación: {ai_result['ai_classification']}")
            print(f"   Personas actualizadas: {persons_result['persons_updated']}")
            
        except Exception as e:
            print(f"   ❌ Error procesando empresa: {e}")
    
    # ==================== PARTE 3: PROCESO COMPLETO ====================
    
    def process_companies(self, limit: int = 10, force: bool = False, interactive: bool = False):
        """Procesar empresas completas"""
        print("=" * 80)
        print("🚀 SISTEMA COMPLETO DE CLASIFICACIÓN")
        print("=" * 80)
        
        # Obtener estadísticas iniciales
        all_companies = self.supabase.table('apollo_companies').select('*').execute().data
        total_companies = len(all_companies)
        companies_with_analysis = len([c for c in all_companies if c.get('perplexity_analysis')])
        companies_without_analysis = total_companies - companies_with_analysis
        
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"   Total de empresas: {total_companies}")
        print(f"   ✅ Con análisis: {companies_with_analysis}")
        print(f"   ⏳ Sin análisis: {companies_without_analysis}")
        print()
        
        # Obtener empresas sin análisis (o todas si force=True)
        if force:
            companies = all_companies
            print(f"🔄 Modo FORCE: reprocesando todas las empresas")
        else:
            companies = [c for c in all_companies if not c.get('perplexity_analysis')]
        
        if not companies:
            print("✅ Todas las empresas ya tienen análisis")
            return
        
        companies_to_process = companies[:limit]
        print(f"\n📊 Procesando {len(companies_to_process)} empresas...")
        
        stats = {
            'companies_processed': 0,
            'companies_incluir': 0,
            'companies_revisar': 0,
            'companies_excluir': 0,
            'total_persons_found': 0,
            'total_persons_updated': 0,
            'persons_incluir': 0
        }
        
        for i, company in enumerate(companies_to_process, 1):
            print(f"\n{'='*80}")
            print(f"🏢 [{i}/{len(companies_to_process)}] {company['name']}")
            print(f"{'='*80}")
            
            try:
                # PASO 1: Análisis con Perplexity
                perplexity_result = self.analyze_company_with_perplexity(company)
                
                if 'error' in perplexity_result:
                    print(f"   ❌ Error en análisis de Perplexity")
                    continue
                
                # PASO 2: Análisis con IA
                ai_result = self.analyze_company_with_ai(perplexity_result)
                
                if 'error' in ai_result:
                    print(f"   ❌ Error en análisis de IA")
                    continue
                
                # Guardar análisis de empresa
                self.supabase.table('apollo_companies').update({
                    'perplexity_analysis': perplexity_result,
                    'ai_score': ai_result['ai_score'],
                    'ai_classification': ai_result['ai_classification'],
                    'ai_analysis_report': ai_result.get('ai_analysis_report')
                }).eq('id', company['id']).execute()
                
                stats['companies_processed'] += 1
                stats[f"companies_{ai_result['ai_classification'].lower()}"] += 1
                
                # PASO 3: Clasificar personas
                persons_result = self.classify_persons_for_company(
                    company,
                    ai_result['ai_score'],
                    ai_result['ai_classification']
                )
                
                stats['total_persons_found'] += persons_result['persons_found']
                stats['total_persons_updated'] += persons_result['persons_updated']
                
                # Contar personas INCLUIR
                persons = self.find_persons_by_company_name(company['name'])
                for person in persons:
                    if person.get('ai_classification') == 'INCLUIR':
                        stats['persons_incluir'] += 1
                
                print(f"   ✅ Empresa procesada: {ai_result['ai_classification']}")
                
                # Modo interactivo: preguntar si continuar
                if interactive and i < len(companies_to_process):
                    remaining = companies_without_analysis - stats['companies_processed']
                    print(f"\n⏳ Empresas restantes sin analizar: {remaining}")
                    response = input("\n¿Continuar con la siguiente empresa? (s/n): ").strip().lower()
                    if response != 's':
                        print("\n🛑 Deteniendo procesamiento...")
                        break
                
            except Exception as e:
                print(f"   ❌ Error procesando empresa: {e}")
        
        # Resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN FINAL")
        print("=" * 80)
        print(f"Empresas procesadas: {stats['companies_processed']}")
        print(f"  ✅ INCLUIR: {stats['companies_incluir']}")
        print(f"  ⚠️  REVISAR: {stats['companies_revisar']}")
        print(f"  ❌ EXCLUIR: {stats['companies_excluir']}")
        print(f"\nPersonas encontradas: {stats['total_persons_found']}")
        print(f"Personas actualizadas: {stats['total_persons_updated']}")
        print(f"Personas INCLUIR: {stats['persons_incluir']}")
        print("=" * 80)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema completo de clasificación')
    parser.add_argument('--limit', type=int, default=10, help='Número de empresas a procesar')
    parser.add_argument('--force', action='store_true', help='Forzar reprocesamiento de empresas ya analizadas')
    parser.add_argument('--company', type=str, help='Procesar una empresa específica por nombre')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo: pregunta después de cada empresa')
    parser.add_argument('--fix-reports', action='store_true', help='Reprocesar solo empresas sin ai_analysis_report')
    parser.add_argument('--menu', action='store_true', help='Modo menú interactivo: selecciona empresas manualmente')
    
    args = parser.parse_args()
    
    try:
        system = CompleteClassificationSystem()
        
        # Modo menú interactivo
        if args.menu:
            system.interactive_company_selector()
            return
        
        # Si se especifica una empresa específica
        if args.company:
            result = system.supabase.table('apollo_companies').select('*').ilike('name', f'%{args.company}%').execute()
            if not result.data:
                print(f"❌ No se encontró empresa con nombre: {args.company}")
                return
            
            if len(result.data) > 1:
                print(f"⚠️  Se encontraron {len(result.data)} empresas:")
                for c in result.data:
                    print(f"   - {c['name']}")
                print(f"Por favor, usa un nombre más específico")
                return
            
            company = result.data[0]
            print(f"🎯 Procesando empresa específica: {company['name']}")
            
            # Procesar esta empresa
            perplexity_result = system.analyze_company_with_perplexity(company)
            if 'error' not in perplexity_result:
                ai_result = system.analyze_company_with_ai(perplexity_result)
                if 'error' not in ai_result:
                    system.supabase.table('apollo_companies').update({
                        'perplexity_analysis': perplexity_result,
                        'ai_score': ai_result['ai_score'],
                        'ai_classification': ai_result['ai_classification'],
                        'ai_analysis_report': ai_result.get('ai_analysis_report')
                    }).eq('id', company['id']).execute()
                    
                    # Clasificar personas
                    persons_result = system.classify_persons_for_company(
                        company,
                        ai_result['ai_score'],
                        ai_result['ai_classification']
                    )
                    
                    print(f"\n✅ Empresa procesada exitosamente")
                    print(f"   Score: {ai_result['ai_score']}/100")
                    print(f"   Clasificación: {ai_result['ai_classification']}")
                    print(f"   Personas actualizadas: {persons_result['persons_updated']}")
        
        elif args.fix_reports:
            # Modo especial: reprocesar solo empresas sin ai_analysis_report
            print("🔧 Modo FIX: Buscando empresas sin ai_analysis_report...")
            all_companies = system.supabase.table('apollo_companies').select('*').execute().data
            
            # Filtrar empresas que tienen perplexity_analysis pero NO tienen ai_analysis_report
            companies_to_fix = [
                c for c in all_companies 
                if c.get('perplexity_analysis') and not c.get('ai_analysis_report')
            ]
            
            if not companies_to_fix:
                print("✅ Todas las empresas con análisis tienen su reporte")
                return
            
            print(f"\n📋 Empresas a reparar: {len(companies_to_fix)}")
            for c in companies_to_fix:
                print(f"   - {c['name']}")
            
            print(f"\n🚀 Reprocesando {len(companies_to_fix)} empresas...")
            
            for i, company in enumerate(companies_to_fix, 1):
                print(f"\n{'='*80}")
                print(f"🏢 [{i}/{len(companies_to_fix)}] {company['name']}")
                print(f"{'='*80}")
                
                try:
                    # Usar el análisis de Perplexity existente
                    perplexity_result = company['perplexity_analysis']
                    
                    # Regenerar análisis de IA
                    ai_result = system.analyze_company_with_ai(perplexity_result)
                    
                    if 'error' not in ai_result:
                        # Actualizar solo el reporte
                        system.supabase.table('apollo_companies').update({
                            'ai_analysis_report': ai_result.get('ai_analysis_report')
                        }).eq('id', company['id']).execute()
                        
                        print(f"   ✅ Reporte generado: {ai_result['ai_classification']} ({ai_result['ai_score']}/100)")
                    else:
                        print(f"   ❌ Error en análisis de IA")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            print(f"\n✅ Reparación completada")
        
        else:
            # Por defecto: modo menú interactivo
            # Solo usa batch automático si el usuario especificó --limit explícitamente
            import sys
            if '--limit' in sys.argv or '--force' in sys.argv or '--interactive' in sys.argv:
                # Usuario quiere modo batch o especificó parámetros
                system.process_companies(limit=args.limit, force=args.force, interactive=args.interactive)
            else:
                # Por defecto: modo menú interactivo
                system.interactive_company_selector()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
LinkedIn Post Generator para Quantex
Genera posts de LinkedIn en PDF basados en reportes de análisis de mercado.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import re

# Agregar el directorio raíz al path para importar módulos de quantex
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import quantex.core.database_manager as db
import quantex.core.llm_manager as llm
from quantex.core.report_aliases import resolve_report_keyword

# Sistema refactorizado - Template unificado con placeholders


class LinkedInPostGenerator:
    def __init__(self, report_type: str = "CLP"):
        self.report_type = report_type.upper()
        
        # Usar template unificado para todos los tipos de informe
        self.template_path = Path(__file__).parent / "linkedin_post_template_unified.html"
            
        self.output_dir = Path(__file__).parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_report_data(self, report_id: str = None, report_keyword: str = None, ticker: str = None) -> dict:
        """Extrae datos del reporte usando la misma lógica que _handle_retrieve_report"""
        try:
            if report_id:
                # Buscar por ID específico (comportamiento original)
                result = db.supabase.table("generated_artifacts").select("*").eq("id", report_id).execute()
                
                if not result.data:
                    raise ValueError(f"No se encontró el reporte con ID: {report_id}")
                
                report = result.data[0]
            else:
                # Replicar la lógica de _handle_retrieve_report
                # Resolver aliases humanos → keyword canónico
                if report_keyword:
                    try:
                        report_keyword = resolve_report_keyword(report_keyword)
                    except Exception:
                        pass
                
                # Validación: debe tener al menos uno de los dos parámetros
                if not report_keyword and not ticker:
                    raise ValueError("No se especificó qué informe recuperar. Debe proporcionar 'report_keyword' O 'ticker'.")
                
                # Usar la función inteligente que puede buscar por cualquiera de los dos parámetros
                report = db.get_latest_report(report_keyword=report_keyword, ticker=ticker, artifact_type_suffix='_final')
                
                if not report:
                    search_criteria = []
                    if report_keyword:
                        search_criteria.append(f"reporte '{report_keyword}'")
                    if ticker:
                        search_criteria.append(f"ticker '{ticker}'")
                    criteria_text = " y ".join(search_criteria)
                    raise ValueError(f"No se encontró un informe final publicado para {criteria_text}.")
            
            # Extraer solo el HTML del informe (full_content)
            html_content = report.get("full_content", "")
            
            return {
                "title": report.get("title", "Análisis de Mercado"),
                "date": report.get("created_at", datetime.now().isoformat()),
                "html_content": html_content
            }
            
        except Exception as e:
            print(f"Error extrayendo datos del reporte: {e}")
            raise
    
    def analyze_html_content(self, html_content: str) -> dict:
        """Analiza el HTML del informe y extrae información existente"""
        try:
            if not html_content:
                return {
                    "titulo": "Análisis de Mercado",
                    "sentencia_clave": "Análisis detallado de drivers clave",
                    "sentimiento": {"porcentaje_alcista": 50, "etiqueta": "Neutral"},
                    "drivers": []
                }
            
            # Prompt específico según el tipo de informe
            if self.report_type == "CLP":
                prompt = f"""
                Analiza este informe CLP (Peso Chileno) completo y luego extrae la información solicitada:

                PASO 1: ANALIZA EL INFORME COMPLETO
                - Lee todo el contenido del informe para entender el contexto completo
                - Identifica los drivers principales mencionados en el análisis
                - Comprende el veredicto táctico y su justificación

                PASO 2: EXTRAE LA INFORMACIÓN SOLICITADA
                1. TÍTULO: Copia exactamente el título del veredicto táctico
                2. SENTENCIA_CLAVE: Copia exactamente la sentencia clave del veredicto táctico
                3. SENTIMIENTO: Copia exactamente los porcentajes de sentimiento
                4. DRIVERS: Para los 3-4 drivers más importantes del análisis:
                   - CONCEPTO: Solo el nombre del driver (ej: "DXY débil", "Cobre resiliente", "Fair value atractivo")
                   - COMENTARIO: Explicación del impacto en una línea (ej: "Favorece fortalecimiento de monedas emergentes")
                   - SENTIMENT: Determina si es POSITIVO, NEUTRAL o NEGATIVO para el peso chileno
                   - FLECHA: ▲ (positivo), ■ (neutral), ▼ (negativo)

                CRITERIOS PARA DRIVERS:
                - Incluye drivers fundamentales (DXY, cobre, fair value, tasas, etc.)
                - Prioriza drivers que tienen impacto directo en USD/CLP
                - Máximo 4 drivers para mantener el post conciso

                HTML del informe (busca el veredicto táctico en la sección azul):
                {html_content[:5000]}...

                IMPORTANTE: El veredicto táctico está en una sección con fondo azul (#007BFF) que contiene:
                - Un H2 con el título del veredicto
                - Un párrafo con la sentencia clave
                
                Responde SOLO con JSON:
                {{
                    "titulo": "título exacto del veredicto",
                    "sentencia_clave": "sentencia clave exacta del veredicto",
                    "sentimiento": {{
                        "porcentaje_alcista": número,
                        "etiqueta": "Alcista/Bajista/Neutral"
                    }},
                    "drivers": [
                        {{
                            "concepto": "SOLO el nombre del driver (ej: 'DXY débil')",
                            "comentario": "explicación del impacto en una línea (ej: 'Favorece fortalecimiento de monedas emergentes')",
                            "sentiment": "bullish/neutral/bearish"
                        }}
                    ]
                }}
                """
            else:  # COBRE
                prompt = f"""
                Analiza este informe COBRE completo y luego extrae la información solicitada:

                PASO 1: ANALIZA EL INFORME COMPLETO
                - Lee todo el contenido del informe para entender el contexto completo
                - Identifica los drivers principales mencionados en el análisis
                - Comprende el veredicto táctico y su justificación

                PASO 2: EXTRAE LA INFORMACIÓN SOLICITADA
                1. TÍTULO: Copia exactamente el título del veredicto táctico
                2. SENTENCIA_CLAVE: Copia exactamente la sentencia clave del veredicto táctico
                3. SENTIMIENTO: Copia exactamente los porcentajes de sentimiento
                4. DRIVERS: Para los 3-4 drivers más importantes del análisis:
                   - CONCEPTO: Solo el nombre del driver (ej: "Demanda china sólida", "Inventarios en caída", "DXY fuerte")
                   - COMENTARIO: Explicación del impacto en una línea (ej: "Soporte fundamental para precios del cobre")
                   - SENTIMENT: Determina si es POSITIVO, NEUTRAL o NEGATIVO para el precio del cobre
                   - FLECHA: ▲ (positivo), ■ (neutral), ▼ (negativo)

                CRITERIOS PARA DRIVERS:
                - Incluye drivers fundamentales (demanda china, inventarios LME/SHFE, DXY, oferta minera, etc.)
                - Prioriza drivers que tienen impacto directo en el precio del cobre
                - Máximo 4 drivers para mantener el post conciso

                HTML del informe (busca el veredicto táctico en la sección azul):
                {html_content[:5000]}...

                IMPORTANTE: El veredicto táctico está en una sección con fondo azul (#007BFF) que contiene:
                - Un H2 con el título del veredicto
                - Un párrafo con la sentencia clave
                
                Responde SOLO con JSON:
                {{
                    "titulo": "título exacto del veredicto",
                    "sentencia_clave": "sentencia clave exacta del veredicto",
                    "sentimiento": {{
                        "porcentaje_alcista": número,
                        "etiqueta": "Alcista/Bajista/Neutral"
                    }},
                    "drivers": [
                        {{
                            "concepto": "SOLO el nombre del driver (ej: 'Demanda china sólida')",
                            "comentario": "explicación del impacto en una línea (ej: 'Soporte fundamental para precios del cobre')",
                            "sentiment": "bullish/neutral/bearish"
                        }}
                    ]
                }}
                """
            
            response = llm.generate_completion(
                task_complexity="complex",
                user_prompt=prompt
            )
            
            # Extraer texto de la respuesta
            response_text = response.get("raw_text", "")
            if response.get("error"):
                print(f"Error del LLM: {response['error']}")
                return {
                    "titulo": "Análisis de Mercado",
                    "sentencia_clave": "Análisis detallado de drivers clave",
                    "sentimiento": {"porcentaje_alcista": 50, "etiqueta": "Neutral"},
                    "drivers": []
                }
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
                return analysis_data
            else:
                # Fallback si no se puede parsear
                return {
                    "titulo": "Análisis de Mercado",
                    "sentencia_clave": "Análisis detallado de drivers clave",
                    "sentimiento": {"porcentaje_alcista": 50, "etiqueta": "Neutral"},
                    "drivers": []
                }
                
        except Exception as e:
            print(f"Error analizando HTML: {e}")
            return {
                "titulo": "Análisis de Mercado",
                "sentimiento": {"porcentaje_alcista": 50, "etiqueta": "Neutral"},
                "drivers": []
            }

    
    
    def fill_template(self, report_data: dict, analysis_data: dict) -> str:
        """Rellena el template unificado con los datos del oráculo"""
        try:
            # Leer el template unificado
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Extraer datos del análisis HTML (datos del oráculo)
            veredicto_titulo = analysis_data.get("titulo", "Análisis de Mercado")
            sentencia_clave = analysis_data.get("sentencia_clave", "Análisis detallado de drivers clave")
            
            # Título dinámico basado en el tipo de reporte (etiqueta humana)
            display_map = {"CLP": "Peso Chileno", "COBRE": "Cobre"}
            titulo_informe = f"Informe Quantex {display_map.get(self.report_type, self.report_type)}"
            
            # Fecha formateada (mes en español, independiente del locale del SO)
            dt = datetime.fromisoformat(report_data["date"].replace('Z', '+00:00'))
            meses_es = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            mes_nombre = meses_es[dt.month - 1].capitalize()
            date = f"{dt.day:02d} de {mes_nombre}, {dt.year}"
            
            # Datos de sentimiento del oráculo
            sentimiento = analysis_data.get("sentimiento", {})
            bullish_pct = sentimiento.get("porcentaje_alcista", 50)
            bearish_pct = 100 - bullish_pct
            sentiment_label = f"Sesgo {sentimiento.get('etiqueta', 'Neutral')} {self.report_type}"
            
            # Generar drivers HTML desde el análisis del oráculo
            drivers_html = ""
            drivers = analysis_data.get("drivers", [])
            for driver in drivers:
                sentiment_class = driver.get("sentiment", "neutral")
                concepto = driver.get("concepto", "")
                comentario = driver.get("comentario", "")
                
                drivers_html += f'''
                <li class="{sentiment_class}">
                    <span class="driver-concept">{concepto}</span>
                    <span class="driver-separator">-</span>
                    <span class="driver-comment">{comentario}</span>
                </li>
                '''
            
            # Reemplazar placeholders con datos del oráculo
            filled_template = template.replace("{{TITULO_INFORME}}", titulo_informe)
            filled_template = filled_template.replace("{{FECHA_INFORME}}", date)
            filled_template = filled_template.replace("{{VEREDICTO_TITULO}}", veredicto_titulo)
            filled_template = filled_template.replace("{{SENTENCIA_CLAVE}}", sentencia_clave)
            filled_template = filled_template.replace("{{SENTIMENT_LABEL}}", sentiment_label)
            filled_template = filled_template.replace("{{BULLISH_PCT}}", str(bullish_pct))
            filled_template = filled_template.replace("{{BEARISH_PCT}}", str(bearish_pct))
            filled_template = filled_template.replace("{{DRIVERS_HTML}}", drivers_html)
            
            return filled_template
            
        except Exception as e:
            print(f"Error rellenando template: {e}")
            raise
    
    def generate_html(self, html_content: str, output_filename: str) -> str:
        """Genera el HTML y lo guarda para conversión a PDF"""
        try:
            output_path = self.output_dir / f"{output_filename}.html"
            
            # Guardar HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML generado exitosamente: {output_path}")
            print("💡 HTML generado para conversión a PDF")
            return str(output_path)
            
        except Exception as e:
            print(f"Error generando HTML: {e}")
            raise
    
    def generate_pdf(self, html_path: str) -> str:
        """Genera PDF desde HTML usando Playwright (solución correcta)"""
        try:
            from playwright.sync_api import sync_playwright
            
            # Crear ruta del PDF
            pdf_path = html_path.replace('.html', '.pdf')
            
            print("🎭 Generando PDF con Playwright...")
            
            with sync_playwright() as p:
                # Lanzar browser
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Cargar HTML
                file_url = f"file://{os.path.abspath(html_path)}"
                page.goto(file_url)
                
                # Esperar a que cargue completamente
                page.wait_for_load_state('networkidle')
                
                # Generar PDF con opciones para mantener estilos
                page.pdf(
                    path=pdf_path,
                    format='A4',
                    margin={
                        'top': '0.3in',
                        'right': '0.3in',
                        'bottom': '0.3in',
                        'left': '0.3in'
                    },
                    print_background=True,  # Mantiene colores de fondo
                    prefer_css_page_size=True
                )
                
                browser.close()
            
            print(f"✅ PDF generado exitosamente: {pdf_path}")
            return pdf_path
            
        except ImportError:
            print("❌ Playwright no está instalado")
            print("💡 Instala con: pip install playwright")
            print("💡 Luego ejecuta: playwright install chromium")
            return None
        except Exception as e:
            print(f"❌ Error generando PDF con Playwright: {e}")
            return None
    
    def generate_png(self, html_path: str, width: int = 1920, height: int = 1080, dpr: int = 2) -> str:
        """Genera PNG horizontal usando Playwright (captura de pantalla)."""
        try:
            from playwright.sync_api import sync_playwright
            png_path = html_path.replace('.html', '.png')

            print("🎭 Generando PNG con Playwright (captura de pantalla)...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=dpr)
                page = context.new_page()
                file_url = f"file://{os.path.abspath(html_path)}"
                page.goto(file_url)
                page.wait_for_load_state('networkidle')
                page.screenshot(path=png_path, type='png', full_page=False)
                browser.close()

            print(f"✅ PNG generado exitosamente: {png_path}")
            return png_path
        except ImportError:
            print("❌ Playwright no está instalado")
            print("💡 Instala con: pip install playwright")
            print("💡 Luego ejecuta: playwright install chromium")
            return None
        except Exception as e:
            print(f"❌ Error generando PNG con Playwright: {e}")
            return None

    def generate_post(self, report_id: str = None, report_keyword: str = None, ticker: str = None, output_filename: str = None) -> str:
        """Genera el post completo de LinkedIn"""
        try:
            if report_id:
                print(f"Generando post para reporte ID: {report_id}")
            elif report_keyword:
                print(f"Generando post para último reporte: {report_keyword}")
            elif ticker:
                print(f"Generando post para último reporte de ticker: {ticker}")
            else:
                raise ValueError("Debe proporcionar report_id, report_keyword o ticker")
            
            # 1. Extraer datos del reporte
            print("Extrayendo datos del reporte...")
            report_data = self.extract_report_data(report_id=report_id, report_keyword=report_keyword, ticker=ticker)
            print(f"📊 Datos extraídos: {report_data['title']}")
            print(f"📅 Fecha: {report_data['date']}")
            print(f"📝 HTML length: {len(report_data['html_content'])} caracteres")
            
            # 2. Analizar HTML del informe
            print("Analizando HTML del informe...")
            analysis_data = self.analyze_html_content(report_data["html_content"])
            print(f"🎯 Análisis extraído: {analysis_data}")
            
            # 3. Rellenar template
            print("Rellenando template...")
            html_content = self.fill_template(report_data, analysis_data)
            
            # 5. Generar PDF
            if not output_filename:
                if report_id:
                    output_filename = f"linkedin_post_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                elif report_keyword:
                    output_filename = f"linkedin_post_{report_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                elif ticker:
                    output_filename = f"linkedin_post_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            print("Generando HTML...")
            html_path = self.generate_html(html_content, output_filename)
            print(f"HTML generado exitosamente: {html_path}")
            
            # 5. Generar PNG horizontal por defecto
            print("Generando PNG (1400x788 @2x)...")
            png_path = self.generate_png(html_path, width=1400, height=788, dpr=2)
            if png_path:
                print(f"PNG generado exitosamente: {png_path}")
            else:
                print("💡 No se pudo generar PNG. Verifica Playwright.")
            
            print("✅ Post generado exitosamente!")
            return html_path, png_path
            
        except Exception as e:
            print(f"❌ Error generando post: {e}")
            raise


def interactive_menu():
    """Menú interactivo para seleccionar el tipo de reporte"""
    print("\n" + "="*50)
    print("🔗 GENERADOR DE POSTS LINKEDIN - QUANTEX")
    print("="*50)
    print("\n¿Qué tipo de informe quieres convertir a post de LinkedIn?")
    print("\n1. CLP (Peso Chileno)")
    print("2. COBRE")
    print("3. Salir")
    
    while True:
        try:
            choice = input("\nSelecciona una opción (1-3): ").strip()
            
            if choice == "1":
                return "CLP"
            elif choice == "2":
                return "COBRE"
            elif choice == "3":
                print("👋 ¡Hasta luego!")
                sys.exit(0)
            else:
                print("❌ Opción inválida. Por favor selecciona 1, 2 o 3.")
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Generador de posts de LinkedIn para Quantex")
    parser.add_argument("--report_id", help="ID del reporte en Supabase")
    parser.add_argument("--report_keyword", help="Tipo de reporte (ej: 'comite_tecnico_mercado', 'mesa_redonda')")
    parser.add_argument("--ticker", help="Ticker específico (ej: 'SPIPSA.INDX', 'COPPER')")
    parser.add_argument("--report_type", help="Tipo de reporte: CLP o COBRE")
    parser.add_argument("--output", help="Nombre del archivo de salida (sin extensión)")
    parser.add_argument("--interactive", action="store_true", help="Modo interactivo")
    
    args = parser.parse_args()
    
    # Determinar el tipo de reporte - siempre mostrar menú interactivo
    if args.report_type:
        report_type = args.report_type.upper()
    else:
        report_type = interactive_menu()
    
    # Validar que se proporcione al menos un parámetro de búsqueda
    if not args.report_id and not args.report_keyword and not args.ticker:
        print("\n🔍 Buscando el último reporte de", report_type)
        # Usar report_keyword específico según el tipo para buscar el último informe
        if report_type == "CLP":
            args.report_keyword = "clp"  # Report keyword del peso chileno
        elif report_type == "COBRE":
            args.report_keyword = "cobre"  # Report keyword del cobre
    
    try:
        generator = LinkedInPostGenerator(report_type=report_type)
        html_path, pdf_path = generator.generate_post(
            report_id=args.report_id,
            report_keyword=args.report_keyword,
            ticker=args.ticker,
            output_filename=args.output
        )
        
        print(f"\n🎉 Post generado:")
        print(f"📄 HTML: {html_path}")
        if pdf_path:
            print(f"📄 PDF: {pdf_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

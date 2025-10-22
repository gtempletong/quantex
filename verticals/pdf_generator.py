"""
Generador de PDF simple y funcional para reportes de Mesa Redonda
Basado en la lógica que funciona en test_pdf_simple.py
Ahora incluye soporte para WeasyPrint con página gigante (sin líneas blancas)
"""

from playwright.sync_api import sync_playwright
from weasyprint import HTML


def generate_pdf_html(html_content: str, report_keyword: str = None) -> str:
    """
    Genera HTML mejorado para PDF con fondo negro sutil.
    
    Args:
        html_content: HTML original del reporte
        report_keyword: Tipo de reporte (clp, cobre, etc.)
        
    Returns:
        str: HTML mejorado con CSS para PDF
    """
    
    # CSS sutil para fondo negro (preserva formatos y márgenes)
    pdf_css = """
    <style>
        @page {
            background: #000000;
        }
        html {
            background: #000000;
        }
    </style>
    """
    
    # Insertar CSS al inicio del HTML
    enhanced_html = pdf_css + html_content
    
    return enhanced_html


def add_pdf_css_for_mesa_redonda(html_content: str) -> str:
    """
    Función específica para Mesa Redonda con CSS sutil.
    
    Args:
        html_content: HTML original
        
    Returns:
        str: HTML con CSS para PDF
    """
    return generate_pdf_html(html_content, "mesa_redonda")


def html_to_pdf_with_playwright(html_content: str) -> bytes:
    """
    Convierte HTML a PDF usando Playwright directamente.
    
    Args:
        html_content: HTML a convertir
        
    Returns:
        bytes: Contenido del PDF en bytes
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Cargar HTML
            page.set_content(html_content)
            
            # Esperar a que cargue completamente
            page.wait_for_load_state('networkidle')
            
            # Generar PDF con márgenes correctos
            pdf_bytes = page.pdf(
                format='A4',
                margin={
                    'top': '1in',
                    'right': '1in',
                    'bottom': '1in',
                    'left': '1in'
                },
                print_background=True,
                prefer_css_page_size=True
            )
            
            browser.close()
            
        return pdf_bytes
        
    except Exception as e:
        print(f"❌ Error generando PDF con Playwright: {e}")
        return None


# Función principal para compatibilidad con database_manager.py
def generate_pdf_for_report(html_content: str, report_keyword: str = None) -> bytes:
    """
    Función principal que genera PDF para cualquier reporte.
    
    Args:
        html_content: HTML original del reporte
        report_keyword: Tipo de reporte
        
    Returns:
        bytes: Contenido del PDF en bytes
    """
    
    # Generar HTML mejorado
    enhanced_html = generate_pdf_html(html_content, report_keyword)
    
    # Convertir a PDF
    pdf_bytes = html_to_pdf_with_playwright(enhanced_html)
    
    return pdf_bytes


if __name__ == "__main__":
    # Prueba simple
    test_html = """
    <html>
        <body style="background: #121212; color: white; padding: 20px;">
            <h1>Test PDF</h1>
            <p>Este es un test del generador de PDF.</p>
        </body>
    </html>
    """
    
    pdf_bytes = generate_pdf_for_report(test_html)
    
    if pdf_bytes:
        with open("test_pdf_generator.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✅ PDF generado: test_pdf_generator.pdf")
    else:
        print("❌ Error generando PDF")


def generate_pdf_with_wkhtmltopdf(html_content: str) -> bytes:
    """
    Genera PDF usando wkhtmltopdf con página optimizada para reportes CLP/Cobre.
    
    Características:
    - Página de 1 metro (1000mm) sin saltos de página
    - Fondo negro sin líneas blancas
    - Sentiment bar visible con colores
    - Título y fecha centrados
    - Contenido principal alineado a la izquierda
    
    Args:
        html_content: HTML original del reporte
        
    Returns:
        bytes: PDF generado
    """
    import pdfkit
    
    # CSS optimizado para reportes CLP/Cobre
    wkhtmltopdf_css = """
    <style>
    @page {
        size: A4;
        margin: 0;
        background: #000;
    }
    
    html, body {
        background: #000;
        color: #fff;
        margin: 0;
        padding: 0;
    }
    
    .content {
        padding: 18mm 15mm 20mm 15mm;
        box-sizing: border-box;
    }
    
    /* Centrar solo la tabla principal */
    table {
        margin: 0 auto;
        border-collapse: collapse;
    }
    
    /* Centrar elementos específicos */
    td[align="center"] {
        text-align: center !important;
    }
    
    /* Centrar título y fecha específicamente */
    h1 {
        text-align: center !important;
    }
    
    /* Centrar la fecha (párrafo después del h1) */
    h1 + p {
        text-align: center !important;
    }
    
    /* Forzar que las celdas de contenido principal sean left-aligned */
    td[style*="padding: 20px"] {
        text-align: left !important;
    }
    </style>
    """
    
    # Crear HTML con estructura optimizada (SIN modificar HTML original)
    enhanced_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        {wkhtmltopdf_css}
    </head>
    <body>
        <div class="content">
            {html_content}
        </div>
    </body>
    </html>
    """
    
    # Configuración optimizada para página de 1.25 metros
    options = {
        'page-size': 'A4',
        'margin-top': '0',
        'margin-right': '0',
        'margin-bottom': '0',
        'margin-left': '0',
        'encoding': "UTF-8",
        'no-outline': None,
        'print-media-type': None,
        'background': None,
        'disable-smart-shrinking': None,
        'page-height': '1250mm',  # Página de 1.25 metros - optimizado para Cobre
        'page-width': '210mm'
    }
    
    # Generar PDF con wkhtmltopdf
    pdf_bytes = pdfkit.from_string(enhanced_html, False, options=options)
    
    return pdf_bytes
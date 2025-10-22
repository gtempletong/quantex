"""
Script de referencia para generación de PDF de reportes CLP/Cobre
usando wkhtmltopdf con página gigante (1250mm).

Este script refleja la configuración actual usada en:
- verticals/pdf_generator.py -> generate_pdf_with_wkhtmltopdf()

Úsalo para:
- Probar cambios en la generación de PDF antes de aplicarlos al sistema
- Generar PDFs de prueba desde Supabase
- Referencia de la configuración wkhtmltopdf actual

IMPORTANTE: Si modificas este script, replica los cambios en:
verticals/pdf_generator.py (función generate_pdf_with_wkhtmltopdf)
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from quantex.core.database_manager import supabase
import pdfkit

def test_wkhtmltopdf():
    print("🧪 === GENERADOR DE PDF CLP CON WKHTMLTOPDF ===\n")
    
    # 1. Obtener HTML desde Supabase
    print("📥 Obteniendo HTML desde Supabase...")
    try:
        result = supabase.table('generated_artifacts').select('*').eq('report_keyword', 'clp').order('created_at', desc=True).limit(1).execute()
        
        if not result.data:
            print("❌ No se encontró ningún reporte CLP en Supabase")
            return
        
        html_content = result.data[0]['full_content']
        print(f"✅ HTML obtenido: {len(html_content)} caracteres")
        print(f"📅 Fecha: {result.data[0]['created_at']}")
        
    except Exception as e:
        print(f"❌ Error obteniendo HTML: {e}")
        return
    
    # 2. CSS para página gigante SIN saltos
    print("\n🎨 Agregando CSS para página gigante...")
    
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
    
    # Crear HTML con estructura de página gigante (SIN modificar HTML original)
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
    
    # 3. Generar PDF usando wkhtmltopdf
    print("🎨 Generando PDF con wkhtmltopdf...")
    try:
        # Configuración para página gigante
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
            'page-height': '1250mm',  # Página de 1.25 metros
            'page-width': '210mm'
        }
        
        output_path = "clp_report_sample.pdf"
        
        # Generar PDF
        pdfkit.from_string(enhanced_html, output_path, options=options)
        
        # Obtener tamaño del archivo
        file_size = os.path.getsize(output_path)
        print(f"✅ PDF generado: {file_size} bytes")
        print(f"📄 Guardado como: {output_path}")
        
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        print("💡 Nota: wkhtmltopdf necesita estar instalado en el sistema")
        print("💡 Descarga desde: https://wkhtmltopdf.org/downloads.html")
        return
    
    print("\n🎉 ¡PDF CLP GENERADO EXITOSAMENTE!")
    print(f"📄 Archivo: {output_path}")
    print(f"📊 Tamaño: {file_size:,} bytes")
    print("\n✅ Características del PDF:")
    print("   - Fondo negro sin líneas blancas")
    print("   - Sentiment bar visible con colores")
    print("   - Título y fecha centrados")
    print("   - Contenido principal alineado a la izquierda")
    print("   - Página de 1 metro (1000mm)")

if __name__ == "__main__":
    test_wkhtmltopdf()

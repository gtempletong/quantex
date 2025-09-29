# quantex/pipelines/price_ingestor/inspector_supabase.py (Versión con Reporte HTML)

import os
import sys
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def generate_schema_report_html(schema_data: dict):
    """
    Toma un diccionario con la estructura de la base de datos y genera un reporte HTML.
    """
    print(" -> 📄 Generando reporte HTML del esquema...")
    
    tables_html = ""
    for table_name, columns in schema_data.items():
        columns_html = "<ul>"
        for col in columns:
            columns_html += f"<li><b>{col['name']}</b> ({col['type']})</li>"
        columns_html += "</ul>"
        
        tables_html += f"""
        <div class="table-container">
            <h2>📋 Tabla: {table_name}</h2>
            {columns_html}
        </div>
        """

    html_template = f"""
    <html>
    <head>
        <title>Reporte de Esquema de Supabase</title>
        <style>
            body {{ font-family: sans-serif; background-color: #1a1a1a; color: #e0e0e0; padding: 20px; }}
            h1 {{ color: #007BFF; border-bottom: 2px solid #007BFF; padding-bottom: 10px; }}
            h2 {{ color: #a0aec0; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); grid-gap: 20px; }}
            .table-container {{ background-color: #2c2c2c; border: 1px solid #444; border-radius: 8px; padding: 0 20px 10px 20px; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ background-color: #383838; margin-bottom: 5px; padding: 8px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>🗺️ Mapa del Esquema de la Base de Datos Quantex</h1>
        <p>Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="container">
            {tables_html}
        </div>
    </body>
    </html>
    """
    
    report_filename = "reporte_esquema_supabase.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"\n--- ✅ Reporte Finalizado. Abre el archivo '{report_filename}' en tu navegador. ---")

def inspeccionar_schema():
    """
    Se conecta a Supabase, extrae el esquema y devuelve un diccionario estructurado.
    """
    schema_data = {}
    try:
        load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
        db_password = os.getenv("SUPABASE_DB_PASSWORD")
        if not db_password:
            print("❌ Error: La variable SUPABASE_DB_PASSWORD no se encontró en el archivo .env")
            return None
        
        # Las credenciales se pueden dejar hardcodeadas aquí ya que son estándar de Supabase, excepto la pass.
        conn_string = f"dbname='postgres' user='postgres.ikhfknlyhuyygyvoofdu' host='aws-0-us-east-1.pooler.supabase.com' password='{db_password}' port='6543'"
        
        conn = psycopg2.connect(conn_string)
        print("✅ Conexión a Supabase exitosa.")
        cur = conn.cursor()
        
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;
        """)
        
        tablas = cur.fetchall()
        if not tablas:
            print("\nNo se encontraron tablas.")
            return None
            
        print(f"\n🔎 Se encontraron {len(tablas)} tablas. Analizando columnas...")
        
        for tabla in tablas:
            nombre_tabla = tabla[0]
            schema_data[nombre_tabla] = []
            cur.execute("""
                SELECT column_name, data_type FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public' ORDER BY ordinal_position;
            """, (nombre_tabla,))
            
            columnas = cur.fetchall()
            for columna in columnas:
                schema_data[nombre_tabla].append({'name': columna[0], 'type': columna[1]})

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}", file=sys.stderr)
        return None
        
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
            print("\n🔌 Conexión cerrada.")
            
    return schema_data

if __name__ == '__main__':
    datos_esquema = inspeccionar_schema()
    if datos_esquema:
        generate_schema_report_html(datos_esquema)
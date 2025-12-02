"""
Script para exportar precios de cobre desde Supabase a Google Sheets
Ejecutar: python export_copper_to_google_sheets.py

Configuración requerida en .env:
- GOOGLE_CREDENTIALS_FILE: ruta al archivo JSON de credenciales de Google (ej: google_credentials.json)
- COPPER_SHEET_URL: URL del Google Sheet donde exportar (opcional, se puede pasar como parámetro)
- COPPER_SHEET_TAB: nombre de la pestaña/hoja (default: "Precios Cobre")
"""

import os
import sys
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

# Cargar variables de entorno
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Agregar project root al path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import gspread
except ImportError:
    print("❌ Error: gspread no está instalado. Instala con: pip install gspread")
    sys.exit(1)

from quantex.core.database_manager import supabase


def export_copper_to_google_sheets(
    sheet_url: str = None,
    sheet_tab: str = None,
    clear_existing: bool = False
):
    """
    Exporta datos de cobre desde Supabase a Google Sheets
    
    Args:
        sheet_url: URL del Google Sheet (o None para usar variable de entorno)
        sheet_tab: Nombre de la pestaña (o None para usar default)
        clear_existing: Si True, limpia los datos existentes antes de escribir
    """
    
    # 1. Configuración
    creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
    if not os.path.exists(creds_path):
        print(f"❌ Error: No se encontró el archivo de credenciales: {creds_path}")
        print("💡 Configura GOOGLE_CREDENTIALS_FILE en .env o coloca google_credentials.json en el directorio raíz")
        return False
    
    sheet_url = sheet_url or os.getenv("COPPER_SHEET_URL")
    if not sheet_url:
        print("❌ Error: No se especificó URL del Google Sheet")
        print("💡 Configura COPPER_SHEET_URL en .env o pásalo como parámetro")
        return False
    
    sheet_tab = sheet_tab or os.getenv("COPPER_SHEET_TAB", "Precios Cobre")
    
    try:
        # 2. Obtener datos desde Supabase
        print("📊 Conectando a Supabase...")
        print("📥 Obteniendo datos desde vw_copper_prices...")
        
        # Consultar la vista usando el cliente de Supabase
        result = supabase.table('vw_copper_prices')\
            .select('*')\
            .order('fecha', desc=False)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            print("⚠️ No se encontraron datos en la vista vw_copper_prices")
            return False
        
        # Convertir a DataFrame
        df = pd.DataFrame(result.data)
        
        print(f"✅ Obtenidos {len(df)} registros")
        print(f"📅 Rango: {df['fecha'].min()} a {df['fecha'].max()}")
        print(f"📋 Columnas: {', '.join(df.columns.tolist())}")
        
        # 3. Conectar a Google Sheets
        print(f"\n📄 Conectando a Google Sheets...")
        print(f"   URL: {sheet_url}")
        print(f"   Pestaña: {sheet_tab}")
        
        client = gspread.service_account(filename=creds_path)
        
        # Abrir spreadsheet por URL o por key
        try:
            sh = client.open_by_url(sheet_url)
        except Exception:
            # Extraer ID si viene como key
            if "/d/" in sheet_url:
                sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                sh = client.open_by_key(sheet_id)
            else:
                raise
        
        sheet_title = getattr(sh, 'title', 'desconocido')
        print(f"✅ Spreadsheet abierto: '{sheet_title}'")
        
        # 4. Obtener o crear worksheet
        try:
            ws = sh.worksheet(sheet_tab)
            print(f"✅ Worksheet '{sheet_tab}' encontrado")
        except Exception:
            print(f"📝 Creando nueva pestaña '{sheet_tab}'...")
            ws = sh.add_worksheet(
                title=sheet_tab,
                rows=str(len(df) + 10),
                cols=str(len(df.columns))
            )
            print(f"✅ Pestaña '{sheet_tab}' creada")
        
        # 5. Preparar datos para escribir
        # Convertir DataFrame a lista de listas
        headers = df.columns.tolist()
        values = df.values.tolist()
        
        # 6. Escribir datos
        if clear_existing:
            print("🗑️ Limpiando datos existentes...")
            ws.clear()
        
        print(f"📝 Escribiendo {len(values)} filas de datos...")
        
        # Escribir headers
        ws.update('A1', [headers], value_input_option='USER_ENTERED')
        print("✅ Headers escritos")
        
        # Escribir datos (empezando desde la fila 2)
        if values:
            # Escribir en lotes para evitar límites de API
            batch_size = 1000
            for i in range(0, len(values), batch_size):
                batch = values[i:i + batch_size]
                start_row = 2 + i
                end_row = start_row + len(batch) - 1
                range_name = f"A{start_row}:{chr(64 + len(headers))}{end_row}"
                
                ws.update(range_name, batch, value_input_option='USER_ENTERED')
                print(f"   ✅ Filas {start_row}-{end_row} escritas ({len(batch)} registros)")
        
        # 7. Formatear (opcional)
        try:
            # Congelar primera fila (headers)
            ws.freeze(rows=1)
            print("✅ Primera fila congelada")
        except Exception as e:
            print(f"⚠️ No se pudo formatear: {e}")
        
        # 8. Resumen final
        all_values = ws.get_all_values()
        total_rows = len(all_values)
        
        print(f"\n🎉 Exportación completada exitosamente!")
        print(f"📊 Total de filas en el sheet: {total_rows} (incluyendo header)")
        print(f"📋 Columnas exportadas: {len(headers)}")
        print(f"📅 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Exportar datos de cobre desde Supabase a Google Sheets')
    parser.add_argument('--url', type=str, help='URL del Google Sheet')
    parser.add_argument('--tab', type=str, help='Nombre de la pestaña')
    parser.add_argument('--clear', action='store_true', help='Limpiar datos existentes antes de escribir')
    
    args = parser.parse_args()
    
    success = export_copper_to_google_sheets(
        sheet_url=args.url,
        sheet_tab=args.tab,
        clear_existing=args.clear
    )
    
    sys.exit(0 if success else 1)



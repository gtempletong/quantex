"""
Sistema unificado para extraer datos de cobre desde vw_copper_prices
Soporta exportación a: Excel (.xlsx), Google Sheets, CSV

Uso:
    # Exportar a Excel
    python export_copper_data.py --format excel
    
    # Exportar a Google Sheets
    python export_copper_data.py --format sheets --url "https://..."
    
    # Exportar a CSV
    python export_copper_data.py --format csv
"""

import os
import sys
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from typing import Optional

# Cargar variables de entorno
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Agregar project root al path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from quantex.core.database_manager import supabase


class CopperDataExporter:
    """Sistema para extraer y exportar datos de cobre desde vw_copper_prices"""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        
    def fetch_data_from_supabase(self, limit: Optional[int] = None) -> bool:
        """
        Extrae datos desde vw_copper_prices en Supabase
        
        Args:
            limit: Número máximo de registros (None = todos)
            
        Returns:
            True si se obtuvieron datos exitosamente
        """
        try:
            print("📊 Conectando a Supabase...")
            print("📥 Extrayendo datos desde vw_copper_prices...")
            
            query = supabase.table('vw_copper_prices')\
                .select('*')\
                .order('fecha', desc=False)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            
            if not result.data or len(result.data) == 0:
                print("⚠️ No se encontraron datos en vw_copper_prices")
                return False
            
            self.df = pd.DataFrame(result.data)
            
            print(f"✅ Datos extraídos exitosamente")
            print(f"   📊 Registros: {len(self.df)}")
            print(f"   📅 Rango: {self.df['fecha'].min()} a {self.df['fecha'].max()}")
            print(f"   📋 Columnas: {len(self.df.columns)}")
            print(f"   📝 Columnas: {', '.join(self.df.columns.tolist())}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error extrayendo datos: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_to_excel(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Exporta datos a archivo Excel (.xlsx)
        
        Args:
            filename: Nombre del archivo (None = auto-generado)
            
        Returns:
            Ruta del archivo creado o None si falló
        """
        if self.df is None or self.df.empty:
            print("❌ No hay datos para exportar. Ejecuta fetch_data_from_supabase() primero.")
            return None
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"precios_cobre_{timestamp}.xlsx"
            
            filepath = os.path.join(PROJECT_ROOT, filename)
            
            print(f"📝 Exportando a Excel: {filepath}")
            
            # Exportar con formato
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                self.df.to_excel(writer, sheet_name='Precios Cobre', index=False)
                
                # Formatear la hoja
                worksheet = writer.sheets['Precios Cobre']
                
                # Ajustar ancho de columnas
                for idx, col in enumerate(self.df.columns, 1):
                    max_length = max(
                        self.df[col].astype(str).map(len).max(),
                        len(str(col))
                    )
                    worksheet.column_dimensions[chr(64 + idx)].width = min(max_length + 2, 30)
                
                # Congelar primera fila
                worksheet.freeze_panes = 'A2'
            
            print(f"✅ Archivo Excel creado: {filepath}")
            print(f"   📊 {len(self.df)} registros exportados")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error exportando a Excel: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def export_to_csv(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Exporta datos a archivo CSV
        
        Args:
            filename: Nombre del archivo (None = auto-generado)
            
        Returns:
            Ruta del archivo creado o None si falló
        """
        if self.df is None or self.df.empty:
            print("❌ No hay datos para exportar. Ejecuta fetch_data_from_supabase() primero.")
            return None
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"precios_cobre_{timestamp}.csv"
            
            filepath = os.path.join(PROJECT_ROOT, filename)
            
            print(f"📝 Exportando a CSV: {filepath}")
            
            self.df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            print(f"✅ Archivo CSV creado: {filepath}")
            print(f"   📊 {len(self.df)} registros exportados")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error exportando a CSV: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def export_to_google_sheets(
        self,
        sheet_url: str,
        sheet_tab: str = "Precios Cobre",
        clear_existing: bool = False
    ) -> bool:
        """
        Exporta datos a Google Sheets
        
        Args:
            sheet_url: URL del Google Sheet
            sheet_tab: Nombre de la pestaña
            clear_existing: Si True, limpia datos existentes antes de escribir
            
        Returns:
            True si se exportó exitosamente
        """
        if self.df is None or self.df.empty:
            print("❌ No hay datos para exportar. Ejecuta fetch_data_from_supabase() primero.")
            return False
        
        try:
            import gspread
        except ImportError:
            print("❌ Error: gspread no está instalado. Instala con: pip install gspread")
            return False
        
        try:
            creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
            if not os.path.exists(creds_path):
                print(f"❌ Error: No se encontró el archivo de credenciales: {creds_path}")
                return False
            
            print(f"📄 Conectando a Google Sheets...")
            print(f"   URL: {sheet_url}")
            print(f"   Pestaña: {sheet_tab}")
            
            client = gspread.service_account(filename=creds_path)
            
            # Abrir spreadsheet
            try:
                sh = client.open_by_url(sheet_url)
            except Exception:
                if "/d/" in sheet_url:
                    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                    sh = client.open_by_key(sheet_id)
                else:
                    raise
            
            sheet_title = getattr(sh, 'title', 'desconocido')
            print(f"✅ Spreadsheet abierto: '{sheet_title}'")
            
            # Obtener o crear worksheet
            try:
                ws = sh.worksheet(sheet_tab)
                print(f"✅ Worksheet '{sheet_tab}' encontrado")
            except Exception:
                print(f"📝 Creando nueva pestaña '{sheet_tab}'...")
                ws = sh.add_worksheet(
                    title=sheet_tab,
                    rows=str(len(self.df) + 10),
                    cols=str(len(self.df.columns))
                )
                print(f"✅ Pestaña '{sheet_tab}' creada")
            
            # Preparar datos
            headers = self.df.columns.tolist()
            values = self.df.values.tolist()
            
            # Escribir datos
            if clear_existing:
                print("🗑️ Limpiando datos existentes...")
                ws.clear()
            
            print(f"📝 Escribiendo {len(values)} filas de datos...")
            
            # Escribir headers
            ws.update('A1', [headers], value_input_option='USER_ENTERED')
            print("✅ Headers escritos")
            
            # Escribir datos en lotes
            if values:
                batch_size = 1000
                for i in range(0, len(values), batch_size):
                    batch = values[i:i + batch_size]
                    start_row = 2 + i
                    end_row = start_row + len(batch) - 1
                    range_name = f"A{start_row}:{chr(64 + len(headers))}{end_row}"
                    
                    ws.update(range_name, batch, value_input_option='USER_ENTERED')
                    print(f"   ✅ Filas {start_row}-{end_row} escritas ({len(batch)} registros)")
            
            # Formatear
            try:
                ws.freeze(rows=1)
                print("✅ Primera fila congelada")
            except Exception:
                pass
            
            print(f"\n🎉 Exportación a Google Sheets completada!")
            print(f"   📊 Total de filas: {len(values) + 1} (incluyendo header)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exportando a Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_summary(self) -> dict:
        """Obtiene un resumen de los datos cargados"""
        if self.df is None or self.df.empty:
            return {"error": "No hay datos cargados"}
        
        return {
            "total_records": len(self.df),
            "columns": self.df.columns.tolist(),
            "date_range": {
                "min": str(self.df['fecha'].min()),
                "max": str(self.df['fecha'].max())
            },
            "sample_data": self.df.head(3).to_dict('records')
        }


def main():
    """Función principal con CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sistema de extracción y exportación de datos de cobre desde vw_copper_prices'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['excel', 'csv', 'sheets'],
        required=True,
        help='Formato de exportación'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Número máximo de registros a extraer (None = todos)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Nombre del archivo de salida (solo para excel/csv)'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='URL del Google Sheet (solo para sheets)'
    )
    parser.add_argument(
        '--tab',
        type=str,
        default='Precios Cobre',
        help='Nombre de la pestaña en Google Sheets (default: Precios Cobre)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Limpiar datos existentes en Google Sheets antes de escribir'
    )
    
    args = parser.parse_args()
    
    # Crear exporter
    exporter = CopperDataExporter()
    
    # Extraer datos
    print("=" * 60)
    print("🚀 SISTEMA DE EXTRACCIÓN DE DATOS DE COBRE")
    print("=" * 60)
    
    if not exporter.fetch_data_from_supabase(limit=args.limit):
        print("❌ No se pudieron extraer datos. Abortando.")
        sys.exit(1)
    
    # Exportar según formato
    print("\n" + "=" * 60)
    print(f"📤 EXPORTANDO A: {args.format.upper()}")
    print("=" * 60)
    
    success = False
    
    if args.format == 'excel':
        result = exporter.export_to_excel(filename=args.output)
        success = result is not None
        
    elif args.format == 'csv':
        result = exporter.export_to_csv(filename=args.output)
        success = result is not None
        
    elif args.format == 'sheets':
        sheet_url = args.url or os.getenv("COPPER_SHEET_URL")
        if not sheet_url:
            print("❌ Error: Se requiere --url o COPPER_SHEET_URL en .env")
            sys.exit(1)
        
        success = exporter.export_to_google_sheets(
            sheet_url=sheet_url,
            sheet_tab=args.tab,
            clear_existing=args.clear
        )
    
    # Resumen final
    print("\n" + "=" * 60)
    if success:
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        summary = exporter.get_summary()
        print(f"   📊 Total registros: {summary['total_records']}")
        print(f"   📅 Rango: {summary['date_range']['min']} a {summary['date_range']['max']}")
    else:
        print("❌ PROCESO FALLÓ")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()



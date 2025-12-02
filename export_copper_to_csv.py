"""
Script para exportar precios de cobre desde Supabase a Excel (.xlsx)
Ejecutar: python export_copper_to_csv.py
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import datetime

# Cargar variables de entorno
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def export_copper_prices_to_excel():
    """Exporta datos completos de cobre desde vw_copper_prices a Excel"""
    
    # Credenciales de conexión
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    if not db_password:
        print("❌ Error: SUPABASE_DB_PASSWORD no encontrada en .env")
        return None
    
    # Connection string para el pooler
    conn_string = (
        f"host='aws-0-us-east-1.pooler.supabase.com' "
        f"port='6543' "
        f"dbname='postgres' "
        f"user='postgres.ikhfknlyhuyygyvoofdu' "
        f"password='{db_password}'"
    )
    
    try:
        print("📊 Conectando a Supabase...")
        conn = psycopg2.connect(conn_string)
        
        # Query para obtener datos completos de la vista vw_copper_prices
        query = """
        SELECT 
            fecha,
            precio_comex,
            precio_lme,
            precio_shfe,
            inventarios_comex,
            inventarios_lme,
            inventarios_shfe,
            inventarios_totales,
            usdcny_forex
        FROM public.vw_copper_prices
        ORDER BY fecha DESC;
        """
        
        print("📥 Obteniendo datos desde vw_copper_prices...")
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("⚠️ No se encontraron datos en la vista vw_copper_prices")
            conn.close()
            return None
        
        # Generar nombre de archivo con fecha
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"precios_cobre_{timestamp}.xlsx"
        filepath = os.path.join(PROJECT_ROOT, filename)
        
        # Exportar a Excel con formato
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Precios Cobre', index=False)
            
            # Obtener la hoja para formatear
            worksheet = writer.sheets['Precios Cobre']
            
            # Ajustar ancho de columnas
            for idx, col in enumerate(df.columns, 1):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(64 + idx)].width = min(max_length + 2, 20)
        
        print(f"✅ Datos exportados exitosamente a Excel!")
        print(f"📁 Archivo: {filepath}")
        print(f"📊 Registros: {len(df)}")
        print(f"📅 Rango: {df['fecha'].min()} a {df['fecha'].max()}")
        print(f"📋 Columnas: {', '.join(df.columns.tolist())}")
        
        conn.close()
        
        return filepath
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    export_copper_prices_to_excel()


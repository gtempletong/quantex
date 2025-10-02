#!/usr/bin/env python3
"""
Script para analizar todas las columnas del Excel y verificar que no se nos quede ningún campo importante.
"""

import pandas as pd
import sys
import os

# Agregar el path del proyecto principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def analyze_excel_columns():
    """
    Analiza todas las columnas de la hoja "7000 ACTUALIZACION" del Excel.
    """
    excel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'GERENTES ALTOS EJECUTIVOS 2023 ACT.xlsx'))
    sheet_name = "7000 ACTUALIZACION"
    
    print(f"Analizando columnas de la hoja '{sheet_name}'")
    print(f"Archivo: {excel_path}")
    print("=" * 80)
    
    try:
        # Leer solo las primeras 5 filas para ver la estructura
        df = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=5)
        
        print(f"Total de columnas encontradas: {len(df.columns)}")
        print(f"Total de filas en el archivo: {len(pd.read_excel(excel_path, sheet_name=sheet_name))}")
        print("\n" + "=" * 80)
        
        # Mostrar todas las columnas con ejemplos
        print("COLUMNAS ENCONTRADAS:")
        print("-" * 80)
        
        for i, col in enumerate(df.columns, 1):
            print(f"{i:2d}. {col}")
            
            # Mostrar algunos ejemplos de valores no nulos
            non_null_values = df[col].dropna().head(3).tolist()
            if non_null_values:
                examples = [str(val)[:50] + "..." if len(str(val)) > 50 else str(val) for val in non_null_values]
                print(f"    Ejemplos: {', '.join(examples)}")
            else:
                print("    (Sin valores en las primeras 5 filas)")
            print()
        
        print("=" * 80)
        print("ANALISIS DE CAMPOS:")
        print("-" * 80)
        
        # Campos que ya estamos mapeando
        current_fields = {
            'Rut': 'rut_empresa',
            'RazonSocial': 'razon_social', 
            'NombreFantasia': 'nombre_fantasia',
            'TipoEmpresa': 'tipo_empresa',
            'ACTIVIDAD ECONOMICA': 'actividad_economica',
            'Direccion': 'direccion',
            'Comuna': 'comuna',
            'Ciudad': 'ciudad',
            'Region': 'region',
            'Pais': 'pais',
            'SitioWeb': 'sitio_web'
        }
        
        print("CAMPOS YA MAPEADOS:")
        for excel_col, db_col in current_fields.items():
            if excel_col in df.columns:
                print(f"  OK {excel_col} -> {db_col}")
            else:
                print(f"  ERROR {excel_col} -> {db_col} (NO ENCONTRADO)")
        
        print("\nCAMPOS NO MAPEADOS:")
        unmapped_fields = []
        for col in df.columns:
            if col not in current_fields:
                unmapped_fields.append(col)
                print(f"  ? {col}")
        
        if not unmapped_fields:
            print("  (Todos los campos estan mapeados)")
        
        print("\n" + "=" * 80)
        print("RECOMENDACIONES:")
        print("-" * 80)
        
        if unmapped_fields:
            print("CAMPOS NO MAPEADOS ENCONTRADOS. Considera si alguno es importante:")
            for field in unmapped_fields:
                print(f"   - {field}")
            print("\n¿Alguno de estos campos deberia agregarse a la tabla 'empresas'?")
        else:
            print("Todos los campos estan correctamente mapeados.")
        
        # Mostrar estadísticas de completitud
        print(f"\nESTADISTICAS DE COMPLETITUD (primeras 5 filas):")
        print("-" * 80)
        for col in df.columns:
            non_null_count = df[col].notna().sum()
            percentage = (non_null_count / len(df)) * 100
            print(f"  {col}: {non_null_count}/5 ({percentage:.1f}%)")
        
    except FileNotFoundError:
        print(f"ERROR: El archivo Excel no se encontro en '{excel_path}'")
    except Exception as e:
        print(f"ERROR al analizar el Excel: {e}")

if __name__ == "__main__":
    analyze_excel_columns()

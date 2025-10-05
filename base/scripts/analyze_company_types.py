#!/usr/bin/env python3
"""
Script para analizar los tipos de empresa y tamaños únicos en el Excel.
"""

import pandas as pd
import sys
import os

# Agregar el path del proyecto principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def analyze_company_types():
    """
    Analiza los tipos de empresa y tamaños únicos en todas las hojas del Excel.
    """
    excel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'GERENTES ALTOS EJECUTIVOS 2023 ACT.xlsx'))
    
    print("Analizando tipos de empresa y tamaños en el Excel...")
    print("=" * 80)
    
    # Hojas a analizar (las primeras 4)
    sheets_to_analyze = [
        "7000 ACTUALIZACION",
        "7000 HISTORICO", 
        "7000 NUEVOS",
        "7000 ELIMINADOS"
    ]
    
    all_tipo_empresa = set()
    all_tamaño = set()
    
    for sheet_name in sheets_to_analyze:
        try:
            print(f"\nHoja: {sheet_name}")
            print("-" * 40)
            
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            print(f"Total filas: {len(df)}")
            
            # Analizar TipoEmpresa
            if 'TipoEmpresa' in df.columns:
                tipo_empresa_values = df['TipoEmpresa'].dropna().unique()
                print(f"TipoEmpresa únicos: {sorted(tipo_empresa_values)}")
                all_tipo_empresa.update(tipo_empresa_values)
            
            # Analizar columna de tamaño (buscar diferentes nombres posibles)
            tamaño_columns = ['Tamaño', 'tamaño', 'TAMAÑO', 'Tamano', 'TAMANO', 'TipoEmpresa']
            tamaño_found = False
            
            for col in tamaño_columns:
                if col in df.columns:
                    tamaño_values = df[col].dropna().unique()
                    print(f"{col} únicos: {sorted(tamaño_values)}")
                    all_tamaño.update(tamaño_values)
                    tamaño_found = True
                    break
            
            if not tamaño_found:
                print("No se encontró columna de tamaño")
                
        except Exception as e:
            print(f"Error procesando hoja {sheet_name}: {e}")
    
    print("\n" + "=" * 80)
    print("RESUMEN GENERAL:")
    print("-" * 80)
    print(f"Todos los TipoEmpresa únicos: {sorted(all_tipo_empresa)}")
    print(f"Todos los tamaños únicos: {sorted(all_tamaño)}")
    
    print("\n" + "=" * 80)
    print("RECOMENDACIONES PARA FILTRO:")
    print("-" * 80)
    
    # Identificar valores que probablemente sean empresas grandes
    large_company_indicators = []
    small_company_indicators = []
    
    for value in all_tipo_empresa:
        value_str = str(value).strip().upper()
        if any(keyword in value_str for keyword in ['PYME', 'MICRO', 'PEQUEÑA', 'PEQUEÑO']):
            small_company_indicators.append(value)
        elif any(keyword in value_str for keyword in ['GRANDE', 'GRAN', 'S.A.', 'SOCIEDAD']):
            large_company_indicators.append(value)
        else:
            print(f"  ? {value} - Revisar manualmente")
    
    print(f"Empresas PEQUEÑAS (excluir): {small_company_indicators}")
    print(f"Empresas GRANDES (incluir): {large_company_indicators}")
    
    # Generar código de filtro
    print("\n" + "=" * 80)
    print("CODIGO DE FILTRO SUGERIDO:")
    print("-" * 80)
    print("def should_process_empresa(tipo_empresa, tamaño=None):")
    print("    if pd.isna(tipo_empresa):")
    print("        return False")
    print("    ")
    print("    tipo_empresa = str(tipo_empresa).strip().upper()")
    print("    ")
    print("    # Excluir empresas pequeñas")
    exclude_values = [f"'{val}'" for val in small_company_indicators]
    print(f"    excluded_types = [{', '.join(exclude_values)}]")
    print("    ")
    print("    if tipo_empresa in excluded_types:")
    print("        return False")
    print("    ")
    print("    return True")

if __name__ == "__main__":
    analyze_company_types()












































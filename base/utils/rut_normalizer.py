#!/usr/bin/env python3
"""
Utilidades para normalización y validación de RUTs chilenos
"""

import re
import pandas as pd

def calculate_dv(rut_number):
    """
    Calcula el dígito verificador de un RUT chileno
    """
    rut_str = str(rut_number).zfill(8)  # Asegurar 8 dígitos
    multipliers = [2, 3, 4, 5, 6, 7, 2, 3]
    
    total = 0
    for i, digit in enumerate(rut_str):
        total += int(digit) * multipliers[i]
    
    remainder = total % 11
    dv = 11 - remainder
    
    if dv == 11:
        return '0'
    elif dv == 10:
        return 'K'
    else:
        return str(dv)

def normalize_rut(rut_value):
    """
    Normaliza un RUT a formato estándar '12345678-9'
    
    Args:
        rut_value: RUT en cualquier formato (string, int, float, NaN)
    
    Returns:
        str: RUT normalizado en formato '12345678-9' o None si es inválido
    """
    if pd.isna(rut_value) or rut_value == '' or rut_value is None:
        return None
    
    # Convertir a string y limpiar
    rut_str = str(rut_value).strip().upper()
    
    # Remover espacios y caracteres especiales excepto guión
    rut_str = re.sub(r'[^\d\-K]', '', rut_str)
    
    # Si ya tiene formato correcto, validarlo
    if '-' in rut_str:
        parts = rut_str.split('-')
        if len(parts) == 2:
            number_part = parts[0]
            dv_part = parts[1]
            
            # Validar que el número sea válido
            if number_part.isdigit() and len(number_part) <= 8:
                # Validar dígito verificador
                expected_dv = calculate_dv(number_part)
                if dv_part == expected_dv:
                    return f"{number_part.zfill(8)}-{dv_part}"
                else:
                    # RUT con DV incorrecto, corregirlo
                    return f"{number_part.zfill(8)}-{expected_dv}"
    
    # Si es solo número, calcular DV
    if rut_str.isdigit() and len(rut_str) <= 8:
        dv = calculate_dv(rut_str)
        return f"{rut_str.zfill(8)}-{dv}"
    
    # Si contiene K pero no guión
    if 'K' in rut_str:
        number_part = re.sub(r'[^\d]', '', rut_str)
        if number_part.isdigit() and len(number_part) <= 8:
            return f"{number_part.zfill(8)}-K"
    
    return None

def validate_rut(rut_value):
    """
    Valida si un RUT es válido
    
    Args:
        rut_value: RUT a validar
    
    Returns:
        bool: True si es válido, False si no
    """
    normalized = normalize_rut(rut_value)
    return normalized is not None

def extract_rut_number(rut_value):
    """
    Extrae solo el número del RUT (sin DV)
    
    Args:
        rut_value: RUT en cualquier formato
    
    Returns:
        str: Número del RUT o None si es inválido
    """
    normalized = normalize_rut(rut_value)
    if normalized:
        return normalized.split('-')[0]
    return None

def extract_rut_dv(rut_value):
    """
    Extrae solo el dígito verificador del RUT
    
    Args:
        rut_value: RUT en cualquier formato
    
    Returns:
        str: Dígito verificador o None si es inválido
    """
    normalized = normalize_rut(rut_value)
    if normalized:
        return normalized.split('-')[1]
    return None

def format_rut_for_display(rut_value):
    """
    Formatea un RUT para mostrar (con puntos)
    
    Args:
        rut_value: RUT en cualquier formato
    
    Returns:
        str: RUT formateado como '12.345.678-9' o None si es inválido
    """
    normalized = normalize_rut(rut_value)
    if normalized:
        number, dv = normalized.split('-')
        # Agregar puntos cada 3 dígitos desde la derecha
        formatted_number = f"{int(number):,}".replace(',', '.')
        return f"{formatted_number}-{dv}"
    return None

# Función de conveniencia para usar en pandas
def normalize_rut_series(series):
    """
    Normaliza una serie de pandas con RUTs
    
    Args:
        series: pandas Series con RUTs
    
    Returns:
        pandas Series: Serie con RUTs normalizados
    """
    return series.apply(normalize_rut)

# Ejemplos de uso
if __name__ == "__main__":
    # Test cases
    test_ruts = [
        "12345678-9",
        "12345678",
        "12345678K",
        "12345678-0",
        "12345678-1",
        "1234567-8",
        "123456789-0",
        "",
        None,
        "invalid",
        "12.345.678-9"
    ]
    
    print("=== TEST DE NORMALIZACIÓN DE RUTs ===")
    for rut in test_ruts:
        normalized = normalize_rut(rut)
        valid = validate_rut(rut)
        formatted = format_rut_for_display(rut)
        
        print(f"Input: {rut}")
        print(f"  Normalizado: {normalized}")
        print(f"  Válido: {valid}")
        print(f"  Formateado: {formatted}")
        print()




























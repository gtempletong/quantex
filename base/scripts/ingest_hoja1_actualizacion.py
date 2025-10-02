#!/usr/bin/env python3
"""
Script de ingesta para Hoja 1: "7000 ACTUALIZACION"
Procesa 27,788 empresas de la base de datos de gerentes
"""

import pandas as pd
import sys
import os
from datetime import datetime
import logging

# Agregar el path del proyecto principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from quantex.core import database_manager as db
from rut_normalizer import normalize_rut, validate_rut

def setup_logging():
    """Configurar logging para el script"""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'ingest_hoja1_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# Función normalize_rut ahora importada desde utils

def validate_empresa_data(row):
    """
    Valida que los datos obligatorios estén presentes y filtra solo empresas GRANDE
    """
    required_fields = ['Rut', 'RazonSocial']
    
    for field in required_fields:
        if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
            return False, f"Campo obligatorio faltante: {field}"
    
    # Validar RUT
    rut = normalize_rut(row.get('Rut'))
    if not rut or not validate_rut(row.get('Rut')):
        return False, "RUT inválido o faltante"
    
    # FILTRO: Solo empresas GRANDE
    tipo_empresa = str(row.get('TipoEmpresa', '')).strip()
    if tipo_empresa != 'GRANDE':
        return False, f"Empresa no es GRANDE (tipo: {tipo_empresa})"
    
    return True, "OK"

def process_hoja1():
    """
    Procesa la Hoja 1: "7000 ACTUALIZACION" - SOLO EMPRESAS GRANDE
    """
    logger = setup_logging()
    logger.info("=== INICIANDO PROCESAMIENTO HOJA 1: 7000 ACTUALIZACION (SOLO EMPRESAS GRANDE) ===")
    
    # Ruta del archivo Excel
    excel_path = os.path.join(os.path.dirname(__file__), '..', 'GERENTES ALTOS EJECUTIVOS 2023 ACT.xlsx')
    
    if not os.path.exists(excel_path):
        logger.error(f"Archivo Excel no encontrado: {excel_path}")
        return
    
    try:
        # Leer la hoja
        logger.info("Leyendo hoja '7000 ACTUALIZACION'...")
        df = pd.read_excel(excel_path, sheet_name='7000 ACTUALIZACION')
        logger.info(f"Hoja cargada: {df.shape[0]} filas x {df.shape[1]} columnas")
        
        # Estadísticas iniciales
        total_rows = len(df)
        processed = 0
        inserted = 0
        skipped_validation = 0
        skipped_duplicate = 0
        skipped_not_grande = 0  # Nueva estadística para empresas no grandes
        errors = 0
        
        logger.info(f"Procesando {total_rows} empresas...")
        
        # Procesar cada fila
        for index, row in df.iterrows():
            processed += 1
            
            if processed % 1000 == 0:
                logger.info(f"Procesadas {processed}/{total_rows} empresas...")
            
            try:
                # Validar datos
                is_valid, validation_msg = validate_empresa_data(row)
                if not is_valid:
                    if "no es GRANDE" in validation_msg:
                        skipped_not_grande += 1
                    else:
                        logger.warning(f"Fila {index}: {validation_msg}")
                        skipped_validation += 1
                    continue
                
                # Normalizar RUT
                rut_empresa = normalize_rut(row.get('Rut'))
                
                # Verificar si ya existe en Supabase
                existing = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_empresa).execute()
                if existing.data:
                    skipped_duplicate += 1
                    continue
                
                # Preparar datos para inserción
                empresa_data = {
                    'rut_empresa': rut_empresa,
                    'razon_social': str(row.get('RazonSocial', '')).strip(),
                    'nombre_fantasia': str(row.get('NombreFantasia', '')).strip() if pd.notna(row.get('NombreFantasia')) else None,
                    'tipo_empresa': str(row.get('TipoEmpresa', '')).strip() if pd.notna(row.get('TipoEmpresa')) else None,
                    'actividad_economica': str(row.get('ACTIVIDAD ECONOMICA', '')).strip() if pd.notna(row.get('ACTIVIDAD ECONOMICA')) else None,
                    'direccion': str(row.get('Direccion', '')).strip() if pd.notna(row.get('Direccion')) else None,
                    'comuna': str(row.get('Comuna', '')).strip() if pd.notna(row.get('Comuna')) else None,
                    'ciudad': str(row.get('Ciudad', '')).strip() if pd.notna(row.get('Ciudad')) else None,
                    'region': str(row.get('Region', '')).strip() if pd.notna(row.get('Region')) else None,
                    'pais': 'Chile',
                    'sitio_web': str(row.get('SitioWeb', '')).strip() if pd.notna(row.get('SitioWeb')) else None,
                    'cod_act': str(row.get('COD ACT', '')).strip() if pd.notna(row.get('COD ACT')) else None  # ← NUEVO CAMPO
                }
                
                # Limpiar valores vacíos
                empresa_data = {k: v if v != '' else None for k, v in empresa_data.items()}
                
                # Insertar en Supabase
                result = db.supabase.table('empresas').insert(empresa_data).execute()
                
                if result.data:
                    inserted += 1
                else:
                    logger.error(f"Error insertando empresa {rut_empresa}")
                    errors += 1
                
            except Exception as e:
                logger.error(f"Error procesando fila {index}: {e}")
                errors += 1
        
        # Estadísticas finales
        logger.info("=== RESUMEN FINAL ===")
        logger.info(f"Total procesadas: {processed}")
        logger.info(f"Insertadas: {inserted}")
        logger.info(f"Saltadas por no ser GRANDE: {skipped_not_grande}")
        logger.info(f"Saltadas por validación: {skipped_validation}")
        logger.info(f"Saltadas por duplicados: {skipped_duplicate}")
        logger.info(f"Errores: {errors}")
        
        logger.info("=== PROCESAMIENTO COMPLETADO ===")
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        raise

if __name__ == "__main__":
    process_hoja1()

#!/usr/bin/env python3
"""
Script de ingesta para tabla PERSONAS desde Hoja 1: "7000 ACTUALIZACION"
Procesa contactos de empresas GRANDE únicamente
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
    
    log_file = os.path.join(log_dir, f'ingest_personas_hoja1_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def validate_persona_data(row):
    """
    Valida que los datos del contacto estén presentes y que la empresa sea GRANDE
    """
    # Verificar que la empresa sea GRANDE
    tipo_empresa = str(row.get('TipoEmpresa', '')).strip()
    if tipo_empresa != 'GRANDE':
        return False, f"Empresa no es GRANDE (tipo: {tipo_empresa})"
    
    # Verificar que haya datos de contacto
    nombre_contacto = str(row.get('NombreContacto', '')).strip()
    if pd.isna(row.get('NombreContacto')) or nombre_contacto == '':
        return False, "Nombre de contacto faltante"
    
    # Solo verificar que haya nombre de contacto (sin filtrar por datos de contacto)
    
    return True, "OK"

def process_personas_hoja1():
    """
    Procesa contactos de la Hoja 1: "7000 ACTUALIZACION" - SOLO EMPRESAS GRANDE
    """
    logger = setup_logging()
    logger.info("=== INICIANDO PROCESAMIENTO PERSONAS HOJA 1: 7000 ACTUALIZACION (SOLO EMPRESAS GRANDE) ===")
    
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
        skipped_not_grande = 0
        skipped_no_contacto = 0
        skipped_empresa_no_existe = 0  # Nueva estadística
        skipped_duplicate = 0
        errors = 0
        
        logger.info(f"Procesando {total_rows} registros para extraer contactos...")
        
        # Procesar cada fila
        for index, row in df.iterrows():
            processed += 1
            
            if processed % 1000 == 0:
                logger.info(f"Procesadas {processed}/{total_rows} filas...")
            
            try:
                # Validar datos del contacto
                is_valid, validation_msg = validate_persona_data(row)
                if not is_valid:
                    if "no es GRANDE" in validation_msg:
                        skipped_not_grande += 1
                    else:
                        logger.warning(f"Fila {index}: {validation_msg}")
                        skipped_no_contacto += 1
                    continue
                
                # Normalizar RUT empresa usando el mismo normalizador que el script de empresas
                rut_empresa = normalize_rut(row.get('Rut'))
                if not rut_empresa:
                    logger.warning(f"Fila {index}: RUT empresa faltante o inválido")
                    skipped_no_contacto += 1
                    continue
                
                # VERIFICAR que la empresa exista en la tabla empresas (con RUT normalizado)
                empresa_exists = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_empresa).execute()
                if not empresa_exists.data:
                    logger.warning(f"Fila {index}: Empresa {rut_empresa} no existe en tabla empresas - saltando contacto")
                    skipped_empresa_no_existe += 1
                    continue
                
                # Verificar si ya existe este contacto para esta empresa
                # (asumiendo que no hay duplicados por ahora, pero registramos)
                existing = db.supabase.table('personas').select('id').eq('rut_empresa', rut_empresa).eq('nombre_contacto', str(row.get('NombreContacto', '')).strip()).execute()
                if existing.data:
                    skipped_duplicate += 1
                    continue
                
                # Preparar datos para inserción
                persona_data = {
                    'rut_empresa': rut_empresa,
                    'nombre_contacto': str(row.get('NombreContacto', '')).strip(),
                    'cargo_contacto': str(row.get('CargoContacto', '')).strip() if pd.notna(row.get('CargoContacto')) else None,
                    'celular_contacto': str(row.get('CelularContacto', '')).strip() if pd.notna(row.get('CelularContacto')) else None,
                    'telefono_contacto': str(row.get('TelefonoContacto', '')).strip() if pd.notna(row.get('TelefonoContacto')) else None,
                    'email_contacto': str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else None,
                    'tipo_empresa': str(row.get('TipoEmpresa', '')).strip(),  # NUEVO: Para auditoría
                    'fuente_datos': '7000 ACTUALIZACION',
                    'estado': 'ACTIVO'
                }
                
                # Limpiar valores vacíos
                persona_data = {k: v if v != '' else None for k, v in persona_data.items()}
                
                # Insertar en Supabase
                result = db.supabase.table('personas').insert(persona_data).execute()
                
                if result.data:
                    inserted += 1
                else:
                    logger.error(f"Error insertando contacto para empresa {rut_empresa}")
                    errors += 1
                
            except Exception as e:
                logger.error(f"Error procesando fila {index}: {e}")
                errors += 1
        
        # Estadísticas finales
        logger.info("=== RESUMEN FINAL ===")
        logger.info(f"Total procesadas: {processed}")
        logger.info(f"Insertadas: {inserted}")
        logger.info(f"Saltadas por no ser GRANDE: {skipped_not_grande}")
        logger.info(f"Saltadas por falta de contacto: {skipped_no_contacto}")
        logger.info(f"Saltadas por empresa no existe: {skipped_empresa_no_existe}")
        logger.info(f"Saltadas por duplicados: {skipped_duplicate}")
        logger.info(f"Errores: {errors}")
        
        logger.info("=== PROCESAMIENTO COMPLETADO ===")
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        raise

if __name__ == "__main__":
    process_personas_hoja1()

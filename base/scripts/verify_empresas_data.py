#!/usr/bin/env python3
"""
Script de verificación para datos de empresas GRANDE en Supabase
Verifica calidad, completitud y consistencia de los datos insertados
"""

import pandas as pd
import sys
import os
from datetime import datetime
import logging

# Agregar el path del proyecto principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from quantex.core import database_manager as db

def setup_logging():
    """Configurar logging para el script"""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'verify_empresas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def verify_empresas_data():
    """
    Verifica la calidad y completitud de los datos de empresas en Supabase
    """
    logger = setup_logging()
    logger.info("=== VERIFICACIÓN DE DATOS EMPRESAS GRANDE ===")
    
    try:
        # 1. Obtener todos los datos de empresas
        logger.info("Obteniendo datos de Supabase...")
        result = db.supabase.table('empresas').select('*').execute()
        
        if not result.data:
            logger.error("No se encontraron datos en la tabla empresas")
            return
        
        empresas_data = result.data
        total_empresas = len(empresas_data)
        logger.info(f"Total empresas en Supabase: {total_empresas}")
        
        # 2. Convertir a DataFrame para análisis
        df = pd.DataFrame(empresas_data)
        
        # 3. Verificaciones básicas
        logger.info("\n=== VERIFICACIONES BÁSICAS ===")
        
        # Verificar que todas sean empresas GRANDE
        tipo_empresa_counts = df['tipo_empresa'].value_counts()
        logger.info(f"Distribución por tipo de empresa:\n{tipo_empresa_counts}")
        
        if 'GRANDE' not in tipo_empresa_counts or tipo_empresa_counts['GRANDE'] != total_empresas:
            logger.warning("⚠️ No todas las empresas son de tipo GRANDE")
        else:
            logger.info("✅ Todas las empresas son de tipo GRANDE")
        
        # 4. Verificaciones de completitud de campos
        logger.info("\n=== VERIFICACIÓN DE COMPLETITUD ===")
        
        required_fields = ['rut_empresa', 'razon_social', 'tipo_empresa']
        optional_fields = ['nombre_fantasia', 'actividad_economica', 'direccion', 
                          'comuna', 'ciudad', 'region', 'sitio_web', 'cod_act']
        
        for field in required_fields:
            null_count = df[field].isnull().sum()
            if null_count > 0:
                logger.error(f"❌ Campo obligatorio '{field}' tiene {null_count} valores nulos")
            else:
                logger.info(f"✅ Campo '{field}' completo ({total_empresas} valores)")
        
        for field in optional_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                percentage = (null_count / total_empresas) * 100
                logger.info(f"📊 Campo '{field}': {total_empresas - null_count}/{total_empresas} completos ({100-percentage:.1f}%)")
        
        # 5. Verificaciones de calidad de datos
        logger.info("\n=== VERIFICACIÓN DE CALIDAD ===")
        
        # Verificar RUTs únicos
        rut_duplicates = df['rut_empresa'].duplicated().sum()
        if rut_duplicates > 0:
            logger.error(f"❌ Se encontraron {rut_duplicates} RUTs duplicados")
        else:
            logger.info(f"✅ Todos los RUTs son únicos ({total_empresas})")
        
        # Verificar formato de RUTs
        rut_pattern = r'^\d{7,8}-[0-9K]$'
        invalid_ruts = df[~df['rut_empresa'].str.match(rut_pattern, na=False)]
        if len(invalid_ruts) > 0:
            logger.warning(f"⚠️ Se encontraron {len(invalid_ruts)} RUTs con formato inválido")
            logger.warning(f"RUTs problemáticos: {invalid_ruts['rut_empresa'].tolist()}")
        else:
            logger.info("✅ Todos los RUTs tienen formato válido")
        
        # 6. Análisis geográfico
        logger.info("\n=== ANÁLISIS GEOGRÁFICO ===")
        
        if 'region' in df.columns:
            region_counts = df['region'].value_counts().head(10)
            logger.info(f"Top 10 regiones:\n{region_counts}")
        
        if 'ciudad' in df.columns:
            ciudad_counts = df['ciudad'].value_counts().head(10)
            logger.info(f"Top 10 ciudades:\n{ciudad_counts}")
        
        # 7. Análisis de actividades económicas
        logger.info("\n=== ANÁLISIS ECONÓMICO ===")
        
        if 'actividad_economica' in df.columns:
            actividad_counts = df['actividad_economica'].value_counts().head(10)
            logger.info(f"Top 10 actividades económicas:\n{actividad_counts}")
        
        # 8. Verificaciones adicionales
        logger.info("\n=== VERIFICACIONES ADICIONALES ===")
        
        # Verificar que país sea Chile
        if 'pais' in df.columns:
            paises = df['pais'].value_counts()
            logger.info(f"Distribución por país:\n{paises}")
        
        # Verificar sitios web válidos
        if 'sitio_web' in df.columns:
            web_count = df['sitio_web'].notna().sum()
            logger.info(f"Empresas con sitio web: {web_count}/{total_empresas} ({(web_count/total_empresas)*100:.1f}%)")
        
        # 9. Resumen final
        logger.info("\n=== RESUMEN FINAL ===")
        logger.info(f"✅ Total empresas verificadas: {total_empresas}")
        logger.info(f"✅ Todas son empresas GRANDE: {'Sí' if tipo_empresa_counts.get('GRANDE', 0) == total_empresas else 'No'}")
        logger.info(f"✅ RUTs únicos: {'Sí' if rut_duplicates == 0 else 'No'}")
        logger.info(f"✅ Formato RUTs válido: {'Sí' if len(invalid_ruts) == 0 else 'No'}")
        
        logger.info("=== VERIFICACIÓN COMPLETADA ===")
        
    except Exception as e:
        logger.error(f"Error durante la verificación: {e}")
        raise

if __name__ == "__main__":
    verify_empresas_data()



















































#!/usr/bin/env python3
"""
Script de prueba para la nueva configuración YAML del Source Monitor
"""

import sys
import os

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.config_loader import get_config_loader

def test_config_loading():
    """Prueba la carga de configuración desde YAML"""
    print("Probando carga de configuracion YAML...")
    
    try:
        config_loader = get_config_loader()
        print("Configurador cargado exitosamente")
        
        # Obtener resumen de configuración
        summary = config_loader.get_config_summary()
        print(f"\nResumen de configuracion:")
        print(f"  - Fuentes RSS totales: {summary['total_rss_sources']}")
        print(f"  - Fuentes RSS activas: {summary['active_rss_sources']}")
        print(f"  - Fuentes web totales: {summary['total_web_sources']}")
        print(f"  - Fuentes web activas: {summary['active_web_sources']}")
        print(f"  - Categorias: {summary['total_categories']}")
        print(f"  - Version: {summary['config_version']}")
        print(f"  - Ultima actualizacion: {summary['last_updated']}")
        
        return True
        
    except Exception as e:
        print(f"Error al cargar configuracion: {e}")
        return False

def test_rss_sources():
    """Prueba la obtención de fuentes RSS"""
    print("\nProbando obtencion de fuentes RSS...")
    
    try:
        config_loader = get_config_loader()
        
        # Obtener todas las fuentes RSS
        all_sources = config_loader.get_rss_sources(active_only=False)
        print(f"Total de fuentes RSS: {len(all_sources)}")
        
        # Obtener solo fuentes activas
        active_sources = config_loader.get_rss_sources(active_only=True)
        print(f"Fuentes RSS activas: {len(active_sources)}")
        
        # Mostrar detalles de fuentes activas
        if active_sources:
            print(f"\nFuentes RSS activas:")
            for source in active_sources:
                print(f"  - {source['target_name']} ({source['id']})")
                print(f"    URL: {source['source_url']}")
                print(f"    Publisher: {source.get('publisher', 'N/A')}")
                print(f"    Filtros: {len(source.get('filter_keywords', []))} palabras clave")
                print(f"    Keywords: {source.get('filter_keywords', [])}")
                print()
        
        return True
        
    except Exception as e:
        print(f"Error al obtener fuentes RSS: {e}")
        return False

def test_categories():
    """Prueba la obtención de categorías"""
    print("\nProbando obtencion de categorias...")
    
    try:
        config_loader = get_config_loader()
        categories = config_loader.get_categories()
        
        print(f"Categorias encontradas: {len(categories)}")
        
        for cat_id, cat_info in categories.items():
            print(f"  - {cat_id}: {cat_info['name']}")
            print(f"    Descripcion: {cat_info['description']}")
            print(f"    Prioridad: {cat_info['priority']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"Error al obtener categorias: {e}")
        return False

def test_source_by_category():
    """Prueba la obtención de fuentes por categoría"""
    print("\nProbando obtencion de fuentes por categoria...")
    
    try:
        config_loader = get_config_loader()
        categories = config_loader.get_categories()
        
        for cat_id in categories.keys():
            sources = config_loader.get_sources_by_category(cat_id, active_only=True)
            print(f"  - {cat_id}: {len(sources)} fuentes activas")
        
        return True
        
    except Exception as e:
        print(f"Error al obtener fuentes por categoria: {e}")
        return False

def test_global_settings():
    """Prueba la obtención de configuración global"""
    print("\nProbando configuracion global...")
    
    try:
        config_loader = get_config_loader()
        global_settings = config_loader.get_global_settings()
        
        print(f"Configuracion global:")
        for key, value in global_settings.items():
            print(f"  - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"Error al obtener configuracion global: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("INICIANDO PRUEBAS DE CONFIGURACION YAML")
    print("=" * 50)
    
    tests = [
        test_config_loading,
        test_rss_sources,
        test_categories,
        test_source_by_category,
        test_global_settings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 30)
    
    print(f"\nRESULTADOS: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("Todas las pruebas pasaron exitosamente!")
        return True
    else:
        print("Algunas pruebas fallaron")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

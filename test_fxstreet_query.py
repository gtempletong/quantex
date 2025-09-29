#!/usr/bin/env python3
"""
Mini script para probar diferentes queries de FXStreet
y encontrar la combinación correcta de source/topic
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el proyecto al path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db

def test_fxstreet_queries():
    """Prueba diferentes combinaciones de queries para FXStreet"""
    
    print("[TEST] Probando diferentes queries para FXStreet...")
    
    # Obtener fecha de hace 2 días
    time_filter = datetime.now() - timedelta(days=2)
    
    # Lista de combinaciones a probar
    test_cases = [
        {
            "name": "Original (source + topic completo)",
            "source": "FXStreet",
            "topic": "Noticias de Forex"
        },
        {
            "name": "Solo source, sin topic",
            "source": "FXStreet", 
            "topic": None
        },
        {
            "name": "Source + topic simplificado",
            "source": "FXStreet",
            "topic": "Forex"
        },
        {
            "name": "Source + solo 'Noticias'",
            "source": "FXStreet",
            "topic": "Noticias"
        },
        {
            "name": "Source con wildcard + topic completo",
            "source": "%FXStreet%",
            "topic": "Noticias de Forex"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Source: '{test_case['source']}'")
        print(f"   Topic: '{test_case['topic']}'")
        
        try:
            # Construir query
            query = db.supabase.table('nodes').select('content, properties').eq('type', 'Documento')
            
            # Agregar filtro de source
            if test_case['source']:
                if '%' in test_case['source']:
                    query = query.ilike('properties->>source', test_case['source'])
                else:
                    query = query.ilike('properties->>source', f"%{test_case['source']}%")
            
            # Agregar filtro de topic
            if test_case['topic']:
                query = query.ilike('properties->>topic', f"%{test_case['topic']}%")
            
            # Agregar filtro de tiempo y límite
            query = query.gte('properties->>timestamp', time_filter.isoformat()).order('properties->>timestamp', desc=True).limit(5)
            
            # Ejecutar query
            response = query.execute()
            
            print(f"   [OK] Encontrados: {len(response.data)} documentos")
            
            if response.data:
                print("   [DOCS] Primeros documentos:")
                for j, item in enumerate(response.data[:2], 1):
                    content_preview = item.get('content', '')[:100] + "..." if item.get('content') else "Sin contenido"
                    print(f"      {j}. {content_preview}")
                    
                    # Mostrar propiedades relevantes
                    props = item.get('properties', {})
                    print(f"         Source: {props.get('source', 'N/A')}")
                    print(f"         Topic: {props.get('topic', 'N/A')}")
                    print(f"         Timestamp: {props.get('timestamp', 'N/A')}")
            else:
                print("   [ERROR] No se encontraron documentos")
                
        except Exception as e:
            print(f"   [ERROR] Error en query: {e}")
    
    print(f"\n[TARGET] Recomendacion:")
    print("   Usa la combinación que encuentre más documentos.")
    print("   Si ninguna funciona, el problema podría estar en:")
    print("   - El campo 'properties' no tiene la estructura esperada")
    print("   - Los datos están en campos diferentes")
    print("   - Hay un problema de encoding o caracteres especiales")

if __name__ == "__main__":
    test_fxstreet_queries()

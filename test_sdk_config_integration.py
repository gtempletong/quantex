#!/usr/bin/env python3
"""
Test de integración de SDKConfig con Supabase
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio del proyecto al path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_sdk_config_integration():
    """Prueba la integración de SDKConfig con Supabase"""
    
    print("🔗 Probando integración SDKConfig + Supabase...")
    print("=" * 50)
    
    # Test 1: Importar SDKConfig
    print("\n📦 Test 1: Importar SDKConfig")
    try:
        from quantex.core.agents.modular_agent.sdk_config import SDKConfig
        print("✅ SDKConfig importado correctamente")
    except Exception as e:
        print(f"❌ Error importando SDKConfig: {e}")
        return
    
    # Test 2: Obtener configuración
    print("\n🔧 Test 2: Obtener configuración de Supabase")
    try:
        config = SDKConfig.get_supabase_config()
        print(f"✅ Config obtenida: {config}")
    except Exception as e:
        print(f"❌ Error obteniendo config: {e}")
        return
    
    # Test 3: Crear cliente Supabase con SDKConfig
    print("\n🔗 Test 3: Crear cliente Supabase con SDKConfig")
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(config['url'], config['key'])
        print("✅ Cliente Supabase creado con SDKConfig")
    except Exception as e:
        print(f"❌ Error creando cliente: {e}")
        return
    
    # Test 4: Query de prueba
    print("\n🔍 Test 4: Query de prueba")
    try:
        response = supabase.table('personas').select('id, nombre_contacto').limit(1).execute()
        print(f"✅ Query exitoso: {len(response.data)} registros")
        if response.data:
            print(f"   Primer registro: {response.data[0]}")
    except Exception as e:
        print(f"❌ Error en query: {e}")
    
    # Test 5: Comparar con método directo
    print("\n🔄 Test 5: Comparar con método directo")
    try:
        # Método directo (como en runner.py)
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        supabase_direct = create_client(supabase_url, supabase_key)
        
        # Query con método directo
        response_direct = supabase_direct.table('personas').select('id, nombre_contacto').limit(1).execute()
        
        # Comparar resultados
        if response.data == response_direct.data:
            print("✅ Ambos métodos producen el mismo resultado")
        else:
            print("❌ Los métodos producen resultados diferentes")
            
    except Exception as e:
        print(f"❌ Error en comparación: {e}")
    
    print("\n✅ Tests de integración completados!")

if __name__ == "__main__":
    test_sdk_config_integration()




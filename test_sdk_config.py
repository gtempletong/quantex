#!/usr/bin/env python3
"""
Test básico de SDKConfig para verificar si funciona
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio del proyecto al path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_sdk_config():
    """Prueba básica de SDKConfig"""
    
    print("🔧 Probando SDKConfig...")
    print("=" * 50)
    
    # Test 1: Importar SDKConfig
    print("\n📦 Test 1: Importar SDKConfig")
    try:
        from quantex.core.agents.modular_agent.sdk_config import SDKConfig
        print("✅ SDKConfig importado correctamente")
    except Exception as e:
        print(f"❌ Error importando SDKConfig: {e}")
        return
    
    # Test 2: Verificar variables de entorno
    print("\n🔍 Test 2: Verificar variables de entorno")
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"SUPABASE_URL: {'✅' if supabase_url else '❌'}")
    print(f"SUPABASE_SERVICE_KEY: {'✅' if supabase_key else '❌'}")
    print(f"SUPABASE_ANON_KEY: {'✅' if supabase_anon_key else '❌'}")
    
    # Test 3: Probar get_supabase_config
    print("\n🔧 Test 3: Probar get_supabase_config()")
    try:
        config = SDKConfig.get_supabase_config()
        print(f"✅ Config obtenida: {config}")
    except Exception as e:
        print(f"❌ Error en get_supabase_config: {e}")
    
    # Test 4: Probar get_brevo_config
    print("\n📧 Test 4: Probar get_brevo_config()")
    try:
        config = SDKConfig.get_brevo_config()
        print(f"✅ Config obtenida: {config}")
    except Exception as e:
        print(f"❌ Error en get_brevo_config: {e}")
    
    # Test 5: Probar get_airtable_config
    print("\n📊 Test 5: Probar get_airtable_config()")
    try:
        config = SDKConfig.get_airtable_config()
        print(f"✅ Config obtenida: {config}")
    except Exception as e:
        print(f"❌ Error en get_airtable_config: {e}")
    
    print("\n✅ Tests completados!")

if __name__ == "__main__":
    test_sdk_config()




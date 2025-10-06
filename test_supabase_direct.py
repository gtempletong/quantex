#!/usr/bin/env python3
"""
Test directo de conexión a Supabase para entender cómo funciona
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_supabase_connection():
    """Prueba la conexión directa a Supabase"""
    
    print("🔗 Probando conexión directa a Supabase...")
    print("=" * 50)
    
    # Test 1: Verificar variables
    print("\n📋 Test 1: Verificar variables de entorno")
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"SUPABASE_URL: {'✅' if supabase_url else '❌'} {supabase_url}")
    print(f"SUPABASE_SERVICE_KEY: {'✅' if supabase_service_key else '❌'} {supabase_service_key[:20] if supabase_service_key else 'None'}...")
    print(f"SUPABASE_ANON_KEY: {'✅' if supabase_anon_key else '❌'}")
    
    # Test 2: Importar SDK
    print("\n📦 Test 2: Importar SDK Supabase")
    try:
        from supabase import create_client, Client
        print("✅ SDK Supabase importado correctamente")
    except Exception as e:
        print(f"❌ Error importando SDK: {e}")
        return
    
    # Test 3: Crear cliente con SERVICE KEY
    print("\n🔧 Test 3: Crear cliente con SERVICE_KEY")
    try:
        supabase_service = create_client(supabase_url, supabase_service_key)
        print("✅ Cliente creado con SERVICE_KEY")
    except Exception as e:
        print(f"❌ Error creando cliente con SERVICE_KEY: {e}")
        return
    
    # Test 4: Query simple con SERVICE KEY
    print("\n🔍 Test 4: Query simple con SERVICE_KEY")
    try:
        response = supabase_service.table('personas').select('id, nombre_contacto').limit(1).execute()
        print(f"✅ Query exitoso: {len(response.data)} registros")
        if response.data:
            print(f"   Primer registro: {response.data[0]}")
    except Exception as e:
        print(f"❌ Error en query con SERVICE_KEY: {e}")
    
    # Test 5: Crear cliente con ANON KEY (si existe)
    if supabase_anon_key:
        print("\n🔧 Test 5: Crear cliente con ANON_KEY")
        try:
            supabase_anon = create_client(supabase_url, supabase_anon_key)
            print("✅ Cliente creado con ANON_KEY")
            
            # Test 6: Query simple con ANON KEY
            print("\n🔍 Test 6: Query simple con ANON_KEY")
            try:
                response = supabase_anon.table('personas').select('id, nombre_contacto').limit(1).execute()
                print(f"✅ Query exitoso: {len(response.data)} registros")
                if response.data:
                    print(f"   Primer registro: {response.data[0]}")
            except Exception as e:
                print(f"❌ Error en query con ANON_KEY: {e}")
                
        except Exception as e:
            print(f"❌ Error creando cliente con ANON_KEY: {e}")
    else:
        print("\n⏭️  Test 5: Saltado (ANON_KEY no disponible)")
    
    print("\n✅ Tests completados!")

if __name__ == "__main__":
    test_supabase_connection()




#!/usr/bin/env python3
"""
Test de runner.py con SDKConfig integrado
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio del proyecto al path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_runner_with_sdkconfig():
    """Prueba el runner.py con SDKConfig integrado"""
    
    print("🔧 Probando runner.py con SDKConfig...")
    print("=" * 50)
    
    # Test 1: Importar runner
    print("\n📦 Test 1: Importar runner")
    try:
        from quantex.core.agents.modular_agent.runner import execute_tool
        print("✅ Runner importado correctamente")
    except Exception as e:
        print(f"❌ Error importando runner: {e}")
        return
    
    # Test 2: Probar supabase.find_person con SDKConfig
    print("\n🔍 Test 2: Probar supabase.find_person")
    try:
        result = execute_tool({
            "tool": "supabase.find_person",
            "params": {
                "search_term": "Juan",
                "search_type": "name"
            }
        })
        print(f"✅ supabase.find_person: {result.get('ok', False)}")
        if result.get('ok') and result.get('found'):
            person = result['person']
            print(f"   Encontrado: {person['nombre_contacto']}")
        else:
            print(f"   Error: {result.get('error', 'No encontrado')}")
    except Exception as e:
        print(f"❌ Error en supabase.find_person: {e}")
    
    # Test 3: Probar llm.compose_email
    print("\n📧 Test 3: Probar llm.compose_email")
    try:
        result = execute_tool({
            "tool": "llm.compose_email",
            "params": {
                "recipient_name": "Juan Pérez",
                "recipient_company": "Empresa Test",
                "email_purpose": "Seguimiento de reunión",
                "tone": "professional"
            }
        })
        print(f"✅ llm.compose_email: {result.get('ok', False)}")
        if result.get('ok'):
            print(f"   Asunto: {result.get('subject', 'N/A')}")
            print(f"   Contenido: {len(result.get('html_content', ''))} caracteres")
        else:
            print(f"   Error: {result.get('error', 'Error desconocido')}")
    except Exception as e:
        print(f"❌ Error en llm.compose_email: {e}")
    
    # Test 4: Probar brevo.send_email (simulado)
    print("\n📤 Test 4: Probar brevo.send_email (simulado)")
    try:
        result = execute_tool({
            "tool": "brevo.send_email",
            "params": {
                "to": ["test@example.com"],
                "subject": "Test con SDKConfig",
                "html_body": "<p>Email de prueba</p>"
            }
        })
        print(f"✅ brevo.send_email: {result.get('ok', False)}")
        if result.get('ok'):
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
        else:
            print(f"   Error: {result.get('error', 'Error desconocido')}")
    except Exception as e:
        print(f"❌ Error en brevo.send_email: {e}")
    
    print("\n✅ Tests con SDKConfig completados!")

if __name__ == "__main__":
    test_runner_with_sdkconfig()




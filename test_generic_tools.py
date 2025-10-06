#!/usr/bin/env python3
"""
Test de herramientas genéricas del sistema modular
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv('C:/Quantex/.env')

def test_generic_tools():
    """Test de herramientas genéricas"""
    
    print("🚀 TESTING HERRAMIENTAS GENÉRICAS DEL SISTEMA MODULAR")
    print("=" * 60)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        # Test 1: Listar tablas
        print("\n🗂️ TEST 1: Listar tablas de la base de datos")
        print("-" * 40)
        result1 = run_agent("¿Qué tablas hay en la base de datos?", auto_approve=True)
        print(f"✅ RESULTADO TEST 1: {result1}")
        
        # Test 2: Query SQL genérico - personas sin emails
        print("\n📊 TEST 2: Query SQL - personas que no han recibido emails")
        print("-" * 40)
        result2 = run_agent("Encuentra personas que no han recibido emails usando SQL", auto_approve=True)
        print(f"✅ RESULTADO TEST 2: {result2}")
        
        # Test 3: Query SQL con JOIN
        print("\n🔗 TEST 3: Query SQL con JOIN - contactos y empresas")
        print("-" * 40)
        result3 = run_agent("Lista todos los contactos con el nombre de su empresa usando SQL", auto_approve=True)
        print(f"✅ RESULTADO TEST 3: {result3}")
        
        # Test 4: Comparar con herramienta específica
        print("\n🔍 TEST 4: Comparar con herramienta específica")
        print("-" * 40)
        result4 = run_agent("Busca a Gavin Templeton usando la herramienta específica", auto_approve=True)
        print(f"✅ RESULTADO TEST 4: {result4}")
        
        # Test 5: Query complejo
        print("\n🎯 TEST 5: Query complejo - múltiples condiciones")
        print("-" * 40)
        result5 = run_agent("Encuentra contactos que trabajan en empresas y no han recibido emails", auto_approve=True)
        print(f"✅ RESULTADO TEST 5: {result5}")
        
        print("\n🎉 TODOS LOS TESTS COMPLETADOS")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generic_tools()




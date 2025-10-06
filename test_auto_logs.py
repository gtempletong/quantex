#!/usr/bin/env python3
"""
Test automático del sistema modular con logs visibles
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv('C:/Quantex/.env')

def test_auto_logs():
    """Test automático con logs visibles"""
    
    print("🚀 INICIANDO TEST AUTOMÁTICO DEL SISTEMA MODULAR")
    print("=" * 60)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        # Test 1: Búsqueda simple
        print("\n🔍 TEST 1: Buscar a Gavin Templeton")
        print("-" * 40)
        result1 = run_agent("Busca a Gavin Templeton", auto_approve=True)
        print(f"\n✅ RESULTADO TEST 1: {result1}")
        
        # Test 2: Redacción de email
        print("\n📝 TEST 2: Redactar email para Gavin")
        print("-" * 40)
        result2 = run_agent("Busca a Gavin y redacta un email para él sobre seguimiento de proyecto", auto_approve=True)
        print(f"\n✅ RESULTADO TEST 2: {result2}")
        
        # Test 3: Flujo completo (sin envío)
        print("\n📧 TEST 3: Flujo completo (SIN envío)")
        print("-" * 40)
        result3 = run_agent("Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo", auto_approve=True)
        print(f"\n✅ RESULTADO TEST 3: {result3}")
        
        print("\n🎉 TODOS LOS TESTS COMPLETADOS")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_logs()




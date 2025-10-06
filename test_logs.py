#!/usr/bin/env python3
"""
Script simple para probar logs del sistema modular
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

def test_simple_query():
    """Test simple con logs visibles"""
    
    print("🧪 Testing sistema modular con logs...")
    print("=" * 50)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        # Test 1: Búsqueda simple
        print("\n🔍 Test 1: Búsqueda simple")
        print("Query: 'Busca a Gavin Templeton'")
        result = run_agent("Busca a Gavin Templeton", auto_approve=True)
        print(f"\n✅ Resultado: {result}")
        
        # Test 2: Flujo completo
        print("\n📧 Test 2: Flujo completo")
        print("Query: 'Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo'")
        result = run_agent("Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo", auto_approve=True)
        print(f"\n✅ Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_query()




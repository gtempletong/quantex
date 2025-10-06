#!/usr/bin/env python3
"""
Test directo del sistema modular con logs visibles en terminal
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

def test_with_logs():
    """Test directo con logs visibles"""
    
    print("🚀 INICIANDO TEST DIRECTO DEL SISTEMA MODULAR")
    print("=" * 60)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        while True:
            print("\n🤖 OPCIONES DE TEST:")
            print("1. Buscar a Gavin Templeton")
            print("2. Redactar email para Gavin")
            print("3. Flujo completo (buscar + redactar + enviar)")
            print("4. Query personalizado")
            print("5. Salir")
            
            choice = input("\nElige una opción (1-5): ").strip()
            
            if choice == "1":
                print("\n🔍 EJECUTANDO: Buscar a Gavin Templeton")
                print("-" * 40)
                result = run_agent("Busca a Gavin Templeton", auto_approve=True)
                print(f"\n✅ RESULTADO: {result}")
                
            elif choice == "2":
                print("\n📝 EJECUTANDO: Redactar email para Gavin")
                print("-" * 40)
                result = run_agent("Busca a Gavin y redacta un email para él sobre seguimiento de proyecto", auto_approve=True)
                print(f"\n✅ RESULTADO: {result}")
                
            elif choice == "3":
                print("\n📧 EJECUTANDO: Flujo completo con envío")
                print("-" * 40)
                confirm = input("⚠️  ¿Enviar email REAL a Gavin? (y/n): ").strip().lower()
                if confirm == 'y':
                    result = run_agent("Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo", auto_approve=True)
                    print(f"\n✅ RESULTADO: {result}")
                else:
                    print("❌ Envío cancelado")
                    
            elif choice == "4":
                query = input("\n📝 Ingresa tu query: ").strip()
                if query:
                    print(f"\n🤖 EJECUTANDO: {query}")
                    print("-" * 40)
                    result = run_agent(query, auto_approve=True)
                    print(f"\n✅ RESULTADO: {result}")
                else:
                    print("❌ Query vacío")
                    
            elif choice == "5":
                print("\n👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción no válida")
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_logs()




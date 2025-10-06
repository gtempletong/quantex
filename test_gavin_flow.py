#!/usr/bin/env python3
"""
Script para probar el sistema modular con Gavin como sujeto de prueba
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_gavin_complete_flow():
    """Test completo del flujo con Gavin"""
    
    print("🧪 Testing sistema modular con Gavin...")
    print("=" * 50)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        # Test 1: Búsqueda
        print("\n🔍 Test 1: Búsqueda")
        print("Query: 'Busca a Gavin Templeton'")
        result1 = run_agent("Busca a Gavin Templeton", auto_approve=True)
        print(f"Resultado: {result1}")
        
        # Test 2: Redacción
        print("\n📝 Test 2: Redacción de email")
        print("Query: 'Redacta un email profesional para Gavin Templeton sobre seguimiento de proyecto'")
        result2 = run_agent("Redacta un email profesional para Gavin Templeton sobre seguimiento de proyecto", auto_approve=True)
        print(f"Resultado: {result2}")
        
        # Test 3: Flujo completo
        print("\n📧 Test 3: Flujo completo (búsqueda + redacción)")
        print("Query: 'Busca a Gavin y redacta un email para él sobre seguimiento de proyecto'")
        result3 = run_agent("Busca a Gavin y redacta un email para él sobre seguimiento de proyecto", auto_approve=True)
        print(f"Resultado: {result3}")
        
        # Test 4: Envío real (opcional)
        print("\n🚀 Test 4: Envío real")
        confirm = input("¿Enviar email real a Gavin? (y/n): ")
        if confirm.lower() == 'y':
            print("Query: 'Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo'")
            result4 = run_agent("Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo", auto_approve=True)
            print(f"Resultado: {result4}")
        else:
            print("Envío cancelado")
        
        print("\n✅ Tests completados!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def interactive_mode():
    """Modo interactivo para probar queries personalizados"""
    
    print("🤖 Modo interactivo - Sistema Modular")
    print("=" * 50)
    print("Escribe queries en lenguaje natural para probar el sistema")
    print("Ejemplos:")
    print("  - 'Busca a Gavin Templeton'")
    print("  - 'Redacta un email para Gavin'")
    print("  - 'Encuentra personas que no han recibido emails'")
    print("  - 'Busca a Gavin, redacta un email y envíalo'")
    print("\nEscribe 'quit' para salir")
    print("-" * 50)
    
    try:
        from quantex.core.agents.modular_agent.runner import run_agent
        
        while True:
            query = input("\n🤖 Tu query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'salir']:
                print("👋 ¡Hasta luego!")
                break
                
            if not query:
                continue
                
            print(f"\n🔄 Procesando: '{query}'")
            try:
                result = run_agent(query, auto_approve=True)
                print(f"\n✅ Resultado:")
                print(f"{result}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Error inicializando: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Test del Sistema Modular")
    print("1. Test completo con Gavin")
    print("2. Modo interactivo")
    
    choice = input("\nElige una opción (1 o 2): ").strip()
    
    if choice == "1":
        test_gavin_complete_flow()
    elif choice == "2":
        interactive_mode()
    else:
        print("Opción no válida")




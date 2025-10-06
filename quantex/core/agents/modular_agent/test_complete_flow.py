"""
Test del agente modular con flujo completo.
Busca contacto → Redacta email → Envía email
"""

import sys
import os

# Agregar el directorio raíz del proyecto al path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from quantex.core.agents.modular_agent.runner import run_agent


def test_complete_email_flow():
    """Prueba el flujo completo: buscar → redactar → enviar."""
    print("Probando Agente Modular - Flujo Completo de Email")
    print("=" * 60)
    
    # Ejemplo con flujo completo
    query = "Busca el contacto de Juan Pérez en Supabase y envíale un email profesional pidiendo una reunión para discutir oportunidades de negocio"
    
    print(f"Consulta: {query}")
    print()
    
    # Ejecutar con auto_approve=True para evitar confirmación manual
    result = run_agent(query, auto_approve=True)
    
    print("\n" + "=" * 60)
    print("RESULTADO FINAL:")
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'completed':
        print("Ejecución exitosa")
        for i, res in enumerate(result.get('results', []), 1):
            print(f"  {i}. {res['tool']}: {res['response']}")
    elif result.get('status') == 'cancelled':
        print("Ejecución cancelada por el usuario")
    else:
        print(f"Error: {result.get('message', 'Error desconocido')}")


def test_simple_email():
    """Prueba simple solo con envío directo."""
    print("Probando Agente Modular - Email Simple")
    print("=" * 50)
    
    query = "Envía un email a gavintempleton@gavintempleton.net con asunto 'Test Completo' y di 'Este es un test del flujo completo del agente modular'"
    
    print(f"Consulta: {query}")
    print()
    
    result = run_agent(query, auto_approve=True)
    
    print("\n" + "=" * 50)
    print("RESULTADO FINAL:")
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'completed':
        print("Ejecución exitosa")
        for i, res in enumerate(result.get('results', []), 1):
            print(f"  {i}. {res['tool']}: {res['response']}")


if __name__ == "__main__":
    print("Selecciona test:")
    print("1. Flujo completo (buscar → redactar → enviar)")
    print("2. Email simple (solo enviar)")
    
    choice = input("Opción (1 o 2): ").strip()
    
    if choice == "1":
        test_complete_email_flow()
    elif choice == "2":
        test_simple_email()
    else:
        print("Opción inválida")

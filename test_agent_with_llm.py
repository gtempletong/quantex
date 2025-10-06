#!/usr/bin/env python3
"""
Test del agente modular CON LLM para verificar que entiende queries y usa herramientas correctamente
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio del proyecto al path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_agent_with_llm():
    """Prueba el agente modular con LLM para queries inteligentes"""
    
    print("🤖 Probando agente modular CON LLM...")
    print("=" * 50)
    
    try:
        # Importar funciones del agente modular
        from quantex.core.agents.modular_agent.planner import plan_action
        from quantex.core.agents.modular_agent.runner import execute_tool
        
        def run_agent_query(query: str):
            """Función simplificada que usa LLM para planificar y ejecutar"""
            print(f"🤖 LLM planificando: '{query}'")
            
            # 1. LLM crea el plan
            plan = plan_action(query)
            print(f"📋 Plan creado: {plan}")
            
            # 2. Ejecutar herramientas según el plan
            if plan.get("tool_calls"):
                results = []
                for tool_call in plan["tool_calls"]:
                    print(f"🔧 Ejecutando: {tool_call}")
                    result = execute_tool(tool_call)
                    results.append(result)
                    print(f"✅ Resultado: {result}")
                return results
            else:
                return {"error": "No se generaron tool calls"}
        
        # Test 1: Query simple
        print("\n📋 Test 1: Query simple")
        print("Query: 'Busca a Juan en la base de datos'")
        response1 = run_agent_query("Busca a Juan en la base de datos")
        print(f"Respuesta final: {response1}")
        
        # Test 2: Query específico con filtro
        print("\n📧 Test 2: Query con filtro")
        print("Query: 'Encuentra personas que no han recibido emails'")
        response2 = run_agent_query("Encuentra personas que no han recibido emails")
        print(f"Respuesta final: {response2}")
        
        # Test 3: Query por email
        print("\n🔍 Test 3: Query por email")
        print("Query: '¿Quién tiene el email jprodriguez@empresasryr.cl?'")
        response3 = run_agent_query("¿Quién tiene el email jprodriguez@empresasryr.cl?")
        print(f"Respuesta final: {response3}")
        
        print("\n✅ Tests con LLM completados!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_with_llm()

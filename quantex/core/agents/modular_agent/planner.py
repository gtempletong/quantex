"""
Planner del agente modular.
Usa Sonnet 4 para crear planes de acción basados en herramientas MCP.
"""

import json
import os
import sys
from typing import Dict, Any

# Agregar el directorio raíz del proyecto al path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from quantex.core.llm_manager import generate_structured_output
try:
    from .schemas import planner_output_schema
except ImportError:
    # Fallback for absolute import
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from schemas import planner_output_schema


def plan_action(user_query: str) -> Dict[str, Any]:
    """
    Crea un plan de acción usando Sonnet 4.
    
    Args:
        user_query: La consulta del usuario en lenguaje natural
        
    Returns:
        Dict con plan, tool_calls y approvals_needed
    """
    # Lee el prompt del agente
    current_dir = os.path.dirname(__file__)
    with open(os.path.join(current_dir, "prompts/agent.md"), "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    # Lee el catálogo de herramientas
    with open(os.path.join(current_dir, "registry/tools.json"), "r", encoding="utf-8") as f:
        tools_spec = json.load(f)

    # Construye el prompt del usuario con las herramientas disponibles
    user_prompt = f"""Herramientas disponibles:
{json.dumps(tools_spec, indent=2, ensure_ascii=False)}

Usuario: {user_query}

Responde con un JSON válido que incluya:
- plan: array de strings describiendo los pasos
- tool_calls: array de objetos con tool y params
- approvals_needed: boolean"""

    try:
        result = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_name="claude-sonnet-4-20250514",
            output_schema=planner_output_schema,
            force_json_output=True
        )
        return result or {}
    except Exception as e:
        print(f"Error en plan_action: {e}")
        return {"error": str(e)}

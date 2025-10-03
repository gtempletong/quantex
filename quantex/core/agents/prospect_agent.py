#!/usr/bin/env python3

"""
QuantexAgent Orquestador
Sigue patrón Quantex: prompt + llm_manager + tools execution
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional

# Añadir path para importar módulos Quantex
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from quantex.core.llm_manager import generate_structured_output
from .prospect_tools import prospect_tools

class QuantexAgent:
    """
    Agent siguiendo patrón Quantex exacto:
    - Lee prompt file
    - Usa llm_manager con Sonnet 4
    - Ejecuta tools según respuesta estructurada
    """
    
    def __init__(self):
        self.prompt_file = "quantex/core/agents/agent_quantex.md"
        self.task_complexity = "reasoning"  # Para usar Sonnet 4
        self.output_schema = self._get_output_schema()
        
        print("🤖 QuantexAgent initialized")
        print(f"   Prompt: {self.prompt_file}")
        print(f"   Model: {self.task_complexity}")
        
    def execute(self, user_query: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Ejecuta consulta del usuario siguiendo patrón Quantex
        """
        try:
            print(f"\n🎯 Executing Query: '{user_query}'")
            print(f"🧪 Dry Run Mode: {'ON' if dry_run else 'OFF'}")
            print("─" * 60)
            
            # PASO 1: Generar respuesta estructurada usando llm_manager
            print("🧠 Step 1: Generating structured output with Sonnet 4...")
            
            system_prompt = self._load_system_prompt()
            user_prompt = f"""
Query: {user_query}

Available tools: {json.dumps(prospect_tools.get_available_tools(), indent=2)}

Dry run mode: {dry_run}

Please analyze the query and provide a detailed plan with tool calls.
Return response in the exact JSON structure defined in the output schema.
"""
            
            structured_response = generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name="claude-sonnet-4-20250514",  # Sonnet 4 para reasoning
                output_schema=self.output_schema
            )
            
            if not structured_response:
                return {
                    "ok": False,
                    "error": "Failed to generate structured response from Sonnet 4",
                    "suggestions": ["Check prompt format", "Verify API key", "Try simpler query"]
                }
            
            print("✅ Sonnet 4 response received")
            
            # PASO 2: Mostrar plan para aprobación
            print("\n📋 Step 2: Execution Plan")
            self._display_plan(structured_response)
            
            # PASO 3: Ejecutar tools (si se requiere aprobación y dry_run está OFF)
            if structured_response.get("requires_confirmation", True) and not dry_run:
                print("\n⚠️  REQUIRES CONFIRMATION - Switching to dry_run mode")
                dry_run = True
            
            if dry_run or not structured_response.get("requires_confirmation", True):
                print(f"\n🔧 Step 3: Executing {len(structured_response.get('tool_calls', []))} tools...")
                execution_results = self._execute_tools(structured_response, dry_run=dry_run)
            else:
                execution_results = []
            
            # PASO 4: Formatear respuesta final
            final_response = {
                "ok": True,
                "query": user_query,
                "plan": structured_response,
                "execution": execution_results,
                "summary": self._generate_summary(structured_response, execution_results),
                "next_actions": self._get_next_actions(structured_response, dry_run),
                "dry_run": dry_run
            }
            
            print("\n✅ Execution completed successfully!")
            return final_response
            
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            return {
                "ok": False,
                "error": str(e),
                "query": user_query,
                "dry_run": dry_run
            }
    
    def _load_system_prompt(self) -> str:
        """Carga prompt del archivo de sistema"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), '..', '..', self.prompt_file)
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Agent prompt file not found: {self.prompt_file}"
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define schema de salida esperado de Sonnet 4"""
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "Brief description of what the user wants"
                },
                "tools_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tools required for this task"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "integer"},
                            "tool": {"type": "string"},
                            "action": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                },
                "requires_confirmation": {
                    "type": "boolean",
                    "description": "Whether user confirmation is needed before execution"
                },
                "estimated_results": {
                    "type": "string", 
                    "description": "Estimated number of contacts/actions"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Whether to run in dry run mode"
                }
            },
            "required": ["intent", "tools_needed", "steps", "requires_confirmation"]
        }
    
    def _display_plan(self, plan: Dict[str, Any]) -> None:
        """Muestra plan de ejecución"""
        print(f"Intent: {plan.get('intent', 'N/A')}")
        print(f"Tools needed: {', '.join(plan.get('tools_needed', []))}")
        print(f"Steps planned: {len(plan.get('steps', []))}")
        print(f"Requires confirmation: {plan.get('requires_confirmation', True)}")
        print(f"Estimated results: {plan.get('estimated_results', 'N/A')}")
        
        print("\nDetailed steps:")
        for step in plan.get('steps', []):
            print(f"  {step.get('step', '?')}. {step.get('tool', 'unknown')} - {step.get('action', 'unknown')}")
            if 'params' in step:
                print(f"     Params: {json.dumps(step['params'], indent=2)}")
    
    def _execute_tools(self, plan: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
        """Ejecuta herramientas según plan"""
        results = []
        
        for step in plan.get('steps', []):
            tool_name = step.get('tool')
            params = step.get('params', {})
            params['dry_run'] = dry_run  # Añadir dry_run a todos los tools
            
            print(f"\n🔧 Executing: {tool_name}")
            tool_result = prospect_tools.execute_tool(tool_name, **params)
            results.append(tool_result)
            
            if tool_result.get("ok"):
                print(f"✅ {tool_name} completed successfully")
                if 'result' in tool_result and 'rows_returned' in tool_result['result']:
                    print(f"   📊 Rows returned: {tool_result['result']['rows_returned']}")
            else:
                print(f"❌ {tool_name} failed: {tool_result.get('error')}")
        
        return results
    
    def _generate_summary(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Genera resumen de ejecución"""
        tools_executed = len(results)
        successful_tools = sum(1 for r in results if r.get('ok', False))
        
        summary = f"""
Execution Summary:
- Tools executed: {tools_executed}
- Successful: {successful_tools}  
- Failed: {tools_executed - successful_tools}
- Intent: {plan.get('intent', 'N/A')}
"""
        
        # Añadir datos específicos si los hay
        for result in results:
            if result.get('ok') and 'result' in result:
                tool_name = result['tool']
                tool_result = result['result']
                
                if 'rows_returned' in tool_result:
                    summary += f"- {tool_name}: {tool_result['rows_returned']} prospects found\n"
                elif 'sent' in tool_result:
                    summary += f"- {tool_name}: Email {'sent' if tool_result['sent'] else 'simulated'}\n"
        
        return summary.strip()
    
    def _get_next_actions(self, plan: Dict[str, Any], dry_run: bool) -> List[str]:
        """Sugiere próximas acciones"""
        actions = []
        
        if dry_run:
            actions.append("Modify dry_run=False to execute real actions")
            actions.append("review_execution_plan")
        
        if plan.get('requires_confirmation'):
            actions.append("confirm_execution") 
            
        actions.extend([
            "run_new_query",
            "check_results", 
            "export_data"
        ])
        
        return actions

# CLI simple para testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="QuantexAgent CLI")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--dry-run", default=True, type=bool, help="Run in dry run mode")
    
    args = parser.parse_args()
    
    agent = QuantexAgent()
    result = agent.execute(args.query, dry_run=args.dry_run)
    
    print(f"\n📊 FINAL RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

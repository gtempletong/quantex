"""
Schemas para el agente modular.
Define la estructura de datos que debe devolver el planner.
"""

planner_output_schema = {
    "type": "object",
    "properties": {
        "plan": {"type": "array", "items": {"type": "string"}},
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "params": {"type": "object"}
                },
                "required": ["tool", "params"]
            }
        },
        "approvals_needed": {"type": "boolean"}
    },
    "required": ["plan", "tool_calls", "approvals_needed"]
}

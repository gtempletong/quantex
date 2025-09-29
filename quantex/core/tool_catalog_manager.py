# quantex/core/tool_catalog_manager.py

from quantex.core.flow_registry import FLOW_REGISTRY

def build_tool_catalog():
    """
    Construye el catálogo de herramientas en el formato JSON Schema
    requerido por las APIs de "Tool Use" de los LLMs.

    Lee el FLOW_REGISTRY y lo transforma.
    """
    tool_catalog = []
    
    print("🧠 [Tool Catalog Manager] Construyendo catálogo de herramientas desde FLOW_REGISTRY...")

    for flow_name, flow_details in FLOW_REGISTRY.items():
        # Asegurarnos de que el flujo tiene una definición de parámetros
        if "parameters" not in flow_details:
            print(f"   -> ⚠️  Advertencia: El flujo '{flow_name}' no tiene 'parameters' definidos. Será omitido.")
            continue

        tool = {
            "name": flow_name,
            "description": flow_details.get("description", "Sin descripción."),
            "input_schema": flow_details.get("parameters", {"type": "object", "properties": {}})
        }
        tool_catalog.append(tool)
        print(f"   -> 🛠️  Herramienta '{flow_name}' añadida al catálogo.")
        
    print("   -> ✅ Catálogo de herramientas construido exitosamente.")
    return tool_catalog
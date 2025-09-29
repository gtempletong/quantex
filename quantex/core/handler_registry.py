# quantex/core/handler_registry.py

HANDLER_REGISTRY = {}

def register_handler(flow_name):
    def decorator(func):

        # --- INICIO DEL ESPÍA ---
        print(f"✅ [Handler Registry] Registrando '{func.__name__}' para el flujo '{flow_name}'.")
        # --- FIN DEL ESPÍA ---

        
        HANDLER_REGISTRY[flow_name] = func
        return func
    return decorator
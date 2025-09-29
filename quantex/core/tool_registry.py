# quantex/core/tool_registry.py (Versión Corregida)

class ToolRegistry:
    """
    Una clase singleton para registrar y acceder a todas las funciones de
    herramientas disponibles en la aplicación.
    """
    def __init__(self):
        self._tools = {}
        print("Registro de Herramientas (ToolRegistry) inicializado.")

    def register(self, name: str):
        """
        Un decorador para registrar una función como una herramienta disponible.
        """
        def decorator(func):
            print(f"  -> Registrando herramienta: '{name}'")
            self._tools[name] = func
            return func
        return decorator

    def get(self, name: str):
        """
        Obtiene una función de herramienta desde el registro por su nombre.
        """
        return self._tools.get(name)

    # --- NUEVA FUNCIÓN DE REGISTRO ---
    # Esta función ahora contiene las importaciones que antes estaban sueltas al final del archivo.
    # Rompe el círculo de importaciones porque solo se ejecuta cuando se la llama explícitamente.
    def register_all_tools(self):
        """
        Importa todos los módulos de herramientas para asegurarse de que sus decoradores
        @register se ejecuten y se añadan al registro.
        """
        print("  -> ⚙️  El Anfitrión ha ordenado registrar las herramientas de la aplicación...")
        import quantex.core.tools.technical_tools
        import quantex.core.tools.visualization_tools
        # Añade aquí cualquier otro módulo de herramientas que crees en el futuro.

# Creamos una única instancia global para que toda la aplicación la use.
registry = ToolRegistry()
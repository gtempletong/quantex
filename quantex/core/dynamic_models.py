# En quantex/core/dynamic_models.py
from pydantic import BaseModel, create_model
from typing import List, Dict, Any, Type

# Mapeo de nuestros tipos simples en el JSON a los tipos reales de Python
TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "list_of_strings": List[str]
}

def build_pydantic_model_from_schema(schema_name: str, schema_definition: Dict[str, Any]) -> Type[BaseModel]:
    """
    Construye dinámicamente un modelo Pydantic a partir de una definición de esquema JSON.
    Esta función es recursiva para manejar objetos anidados.
    """
    fields = {}
    for field_name, field_type in schema_definition.items():
        if isinstance(field_type, dict):
            # Caso anidado: creamos un sub-modelo recursivamente
            nested_model_name = f"{schema_name.capitalize()}{field_name.capitalize()}"
            nested_model = build_pydantic_model_from_schema(nested_model_name, field_type)
            # El segundo elemento de la tupla (...) significa que el campo es obligatorio
            fields[field_name] = (nested_model, ...)
        elif isinstance(field_type, str) and field_type in TYPE_MAP:
            # Caso base: mapeamos el string del tipo al tipo de Python real
            fields[field_name] = (TYPE_MAP[field_type], ...)
        else:
            # Si el tipo no es reconocido, por defecto lo tratamos como 'Any' para flexibilidad
            fields[field_name] = (Any, ...)
    
    # Usamos create_model de Pydantic para fabricar la clase del modelo al vuelo
    dynamic_model = create_model(schema_name, **fields)
    return dynamic_model
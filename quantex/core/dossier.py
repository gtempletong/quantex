# quantex/core/dossier.py (Versión Definitiva)

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Esta función auxiliar recorre de forma recursiva un objeto (diccionario o lista)
# y convierte cualquier tipo de dato de NumPy a su equivalente en Python nativo.
def _convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


@dataclass
class Dossier:
    """
    Un contenedor estructurado para toda la evidencia y contenido de un informe.
    """
    summaries: Dict[str, Any] = field(default_factory=dict)
    qualitative_context: Dict[str, Any] = field(default_factory=dict)
    visualizations: List[Dict[str, str]] = field(default_factory=list)
    required_reports: Dict[str, Any] = field(default_factory=dict)
    ai_content: Dict[str, Any] = field(default_factory=dict)
    expert_view_anterior: Dict[str, Any] = field(default_factory=dict)

    def to_dict_for_oracle(self) -> dict:
        """
        (Arquitectura Final - Genérica y Universal)
        Construye el diccionario para CUALQUIER Oráculo, usando una estructura estándar.
        """
        prompt_data = {
            "summaries": self.summaries,
            "qualitative_context": self.qualitative_context,
            "required_reports": self.required_reports,
            "expert_view_anterior": self.expert_view_anterior
        }
        return prompt_data

    def to_dict(self) -> dict:
        raw_dict = {
            "summaries": self.summaries,
            "qualitative_context": self.qualitative_context,
            "visualizations": self.visualizations,
            "required_reports": self.required_reports,
            "ai_content": self.ai_content,
            "expert_view_anterior": self.expert_view_anterior
        }
        return _convert_numpy_types(raw_dict)

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            return cls()
        return cls(
            summaries=data.get('summaries', {}),
            qualitative_context=data.get('qualitative_context', {}),
            visualizations=data.get('visualizations', []),
            required_reports=data.get('required_reports', {}),
            ai_content=data.get('ai_content', {}),
            expert_view_anterior=data.get('expert_view_anterior', {})
        )

    # --- Métodos de ayuda para construir el dossier ---

    def add_summary(self, key: str, data: dict):
        """Añade un bloque de resumen numérico."""
        self.summaries[key] = data

    def add_qualitative_context(self, key: str, text: Any):
        """Añade un bloque de contexto cualitativo."""
        self.qualitative_context[key] = text

    def add_visualization(self, viz_object: dict):
        """Añade un elemento de visualización (tabla o gráfico)."""
        self.visualizations.append(viz_object)
    
    def add_multiple_summaries(self, workspace: dict):
        """
        Busca todas las claves que terminen con '_summary' en el workspace
        y las añade al diccionario de resúmenes del dossier.
        """
        for key, value in workspace.items():
            if key.endswith("_summary"):
                self.summaries[key] = value
"""
Interpretador de Consultas - Sistema Grafo
Versión 1.0 - Interpretación inteligente de preguntas del usuario
"""

import os
import sys
import json
import traceback
from typing import Dict, Any, Optional

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.ai_services import ai_services
from quantex.core import llm_manager

class ConsultaInterpretador:
    """
    Interpreta consultas del usuario y las convierte en búsquedas optimizadas
    """
    
    def __init__(self):
        self.ai_services = ai_services
        self.llm_manager = llm_manager
        
        # Cargar prompt del interpretador
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Carga el prompt del interpretador"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'interpretador.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Error cargando prompt del interpretador: {e}")
            return "Analiza la consulta del usuario y determina qué información necesita del grafo de conocimiento."
    
    def interpretar_consulta(self, consulta: str) -> Dict[str, Any]:
        """
        Interpreta una consulta del usuario y determina la estrategia de búsqueda
        
        Args:
            consulta: Pregunta o consulta del usuario
            
        Returns:
            Diccionario con la interpretación estructurada
        """
        try:
            print(f"🧠 [Interpretador] Analizando consulta: '{consulta[:50]}...'")
            
            # Usar LLM para interpretar la consulta
            response = self.llm_manager.generate_structured_output(
                system_prompt=self.prompt_template,
                user_prompt=f"Consulta del usuario: '{consulta}'",
                model_name="claude-3-haiku-20240307",
                output_schema={
                    "type": "object",
                    "properties": {
                        "categoria": {"type": "string"},
                        "conceptos_clave": {"type": "array", "items": {"type": "string"}},
                        "consulta_reformulada": {"type": "string"},
                        "filtro_temporal": {"type": ["string", "null"]},
                        "necesita_sintesis": {"type": "boolean"},
                        "confianza": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    },
                    "required": ["categoria", "conceptos_clave", "consulta_reformulada", "necesita_sintesis", "confianza"]
                }
            )
            
            # Validar y limpiar respuesta
            interpretacion = self._validar_interpretacion(response)
            
            print(f"✅ [Interpretador] Categoría: {interpretacion['categoria']}, Confianza: {interpretacion['confianza']:.2f}")
            
            return interpretacion
            
        except Exception as e:
            print(f"❌ [Interpretador] Error interpretando consulta: {e}")
            traceback.print_exc()
            
            # Fallback: interpretación básica
            return self._interpretacion_fallback(consulta)
    
    def _validar_interpretacion(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y limpia la interpretación del LLM"""
        try:
            # Asegurar que todos los campos requeridos estén presentes
            interpretacion = {
                "categoria": response.get("categoria", "ANÁLISIS_TEMÁTICO"),
                "conceptos_clave": response.get("conceptos_clave", []),
                "consulta_reformulada": response.get("consulta_reformulada", ""),
                "filtro_temporal": response.get("filtro_temporal"),
                "necesita_sintesis": response.get("necesita_sintesis", True),
                "confianza": float(response.get("confianza", 0.7))
            }
            
            # Limpiar consulta reformulada
            if not interpretacion["consulta_reformulada"]:
                interpretacion["consulta_reformulada"] = interpretacion["conceptos_clave"][0] if interpretacion["conceptos_clave"] else ""
            
            # Validar confianza
            interpretacion["confianza"] = max(0.0, min(1.0, interpretacion["confianza"]))
            
            return interpretacion
            
        except Exception as e:
            print(f"⚠️ Error validando interpretación: {e}")
            return self._interpretacion_fallback("")
    
    def _interpretacion_fallback(self, consulta: str) -> Dict[str, Any]:
        """Interpretación de fallback cuando falla el LLM"""
        print("🔄 [Interpretador] Usando interpretación de fallback")
        
        consulta_lower = consulta.lower()
        
        # Detección básica de categorías
        if any(word in consulta_lower for word in ["cómo", "como", "relaciona", "conecta", "impacto"]):
            categoria = "CONEXIONES"
        elif any(word in consulta_lower for word in ["reciente", "último", "hoy", "ayer"]):
            categoria = "TEMPORAL"
        elif any(word in consulta_lower for word in ["por qué", "porque", "causa", "motivo"]):
            categoria = "CAUSAL"
        elif any(word in consulta_lower for word in ["qué pasaría", "que pasaria", "tendencia", "predicción"]):
            categoria = "PREDICTIVO"
        else:
            categoria = "ANÁLISIS_TEMÁTICO"
        
        # Extraer conceptos clave básicos
        conceptos = []
        palabras_importantes = ["cobre", "clp", "dólar", "dolar", "fed", "inflación", "inflacion", "tasa", "mercado", "china", "usa"]
        for palabra in palabras_importantes:
            if palabra in consulta_lower:
                conceptos.append(palabra)
        
        return {
            "categoria": categoria,
            "conceptos_clave": conceptos,
            "consulta_reformulada": consulta,
            "filtro_temporal": None,
            "necesita_sintesis": True,
            "confianza": 0.5
        }
    
    def detectar_intencion_grafo(self, consulta: str) -> bool:
        """
        Detecta si la consulta está dirigida al grafo de conocimiento
        
        Args:
            consulta: Consulta del usuario
            
        Returns:
            True si la consulta es para el grafo
        """
        consulta_lower = consulta.lower()
        
        # Keywords que indican consulta al grafo
        grafo_keywords = [
            'qué sé sobre', 'qué conozco de', 'qué información tengo',
            'buscar en mi conocimiento', 'explorar mi conocimiento',
            'qué documentos tengo', 'qué datos tengo',
            'cómo se relaciona', 'qué conexiones hay',
            'grafo de conocimiento', 'mi conocimiento',
            'qué análisis tengo', 'qué reportes tengo',
            'información sobre', 'datos sobre',
            'qué noticias', 'qué análisis técnico', 'qué análisis',
            'cómo está', 'estado de', 'situación de',
            'qué tengo sobre', 'qué conozco sobre',
            'información de', 'análisis de', 'reportes de',
            # NUEVAS: Consultas específicas (SIN comandos de herramientas)
            'buscame', 'muestrame', 'dame',
            'noticias de', 'noticias del', 'noticias sobre',
            'ultimos', 'últimos', 'dias', 'días',
            'smm', 'mktnews', 'autonomous',
            'de la semana', 'de esta semana', 'de hoy',
            'todos', 'todas', 'todas las'
        ]
        
        return any(keyword in consulta_lower for keyword in grafo_keywords)

# Instancia global del interpretador
_interpretador = None

def get_interpretador() -> ConsultaInterpretador:
    """Obtiene la instancia global del interpretador"""
    global _interpretador
    if _interpretador is None:
        _interpretador = ConsultaInterpretador()
    return _interpretador

if __name__ == "__main__":
    # Prueba del interpretador
    print("🧪 Probando Interpretador de Consultas...")
    
    interpretador = ConsultaInterpretador()
    
    # Pruebas
    consultas_prueba = [
        "¿Qué sé sobre el cobre?",
        "¿Cómo se relaciona la inflación con las tasas de interés?",
        "¿Qué noticias recientes hay sobre China?",
        "¿Por qué subió el precio del cobre?"
    ]
    
    for consulta in consultas_prueba:
        print(f"\n🔍 Consulta: {consulta}")
        resultado = interpretador.interpretar_consulta(consulta)
        print(f"📊 Resultado: {resultado['categoria']} - {resultado['consulta_reformulada']}")

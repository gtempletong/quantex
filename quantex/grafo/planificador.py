"""
Planificador de Búsquedas - Sistema Grafo
Versión 1.0 - Planificación inteligente de estrategias de búsqueda
"""

import os
import sys
import json
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.ai_services import ai_services
from quantex.core import llm_manager

class BusquedaPlanificador:
    """
    Planifica estrategias de búsqueda optimizadas en el grafo de conocimiento
    """
    
    def __init__(self):
        self.ai_services = ai_services
        self.llm_manager = llm_manager
        
        # Cargar prompt del planificador
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Carga el prompt del planificador"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'planificador.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Error cargando prompt del planificador: {e}")
            return "Planifica la estrategia de búsqueda óptima en el grafo de conocimiento."
    
    def planificar_busqueda(self, interpretacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planifica la estrategia de búsqueda basada en la interpretación
        
        Args:
            interpretacion: Resultado del interpretador
            
        Returns:
            Plan de búsqueda estructurado
        """
        try:
            print(f"📋 [Planificador] Planificando búsqueda para categoría: {interpretacion['categoria']}")
            
            # Usar LLM para planificar
            user_prompt = f"""Interpretación de la consulta: {json.dumps(interpretacion, ensure_ascii=False)}

IMPORTANTE: Si la interpretación incluye un 'filtro_temporal', úsalo para generar filtros temporales específicos.
Ejemplo: Si filtro_temporal es "últimas 24 horas", genera filtros con temporal="últimas 24 horas"."""
            
            response = self.llm_manager.generate_structured_output(
                system_prompt=self.prompt_template,
                user_prompt=user_prompt,
                model_name="claude-3-haiku-20240307",
                output_schema={
                    "type": "object",
                    "properties": {
                        "estrategia": {"type": "string"},
                        "búsquedas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "filtros": {"type": "object"},
                                    "top_k": {"type": "integer"},
                                    "prioridad": {"type": "integer"}
                                },
                                "required": ["query", "filtros", "top_k", "prioridad"]
                            }
                        },
                        "síntesis_final": {"type": "boolean"},
                        "tiempo_límite": {"type": "string"}
                    },
                    "required": ["estrategia", "búsquedas", "síntesis_final"]
                }
            )
            
            # Validar y optimizar el plan
            plan = self._validar_plan(response)
            
            print(f"✅ [Planificador] Estrategia: {plan['estrategia']}, {len(plan['búsquedas'])} búsquedas")
            
            return plan
            
        except Exception as e:
            print(f"❌ [Planificador] Error planificando búsqueda: {e}")
            traceback.print_exc()
            
            # Fallback: plan básico
            return self._plan_fallback(interpretacion)
    
    def _validar_plan(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y optimiza el plan de búsqueda"""
        try:
            plan = {
                "estrategia": response.get("estrategia", "SIMPLE"),
                "búsquedas": response.get("búsquedas", []),
                "síntesis_final": response.get("síntesis_final", True),
                "tiempo_límite": response.get("tiempo_límite", "30 segundos")
            }
            
            # Validar y limpiar búsquedas
            busquedas_validas = []
            for busqueda in plan["búsquedas"]:
                busqueda_valida = {
                    "query": busqueda.get("query", ""),
                    "filtros": busqueda.get("filtros", {}),
                    "top_k": max(1, min(100, busqueda.get("top_k", 50))),
                    "prioridad": max(1, busqueda.get("prioridad", 1))
                }
                
                # Procesar filtros temporales
                busqueda_valida["filtros"] = self._procesar_filtros_temporales(busqueda_valida["filtros"])
                
                busquedas_validas.append(busqueda_valida)
            
            # Ordenar por prioridad
            busquedas_validas.sort(key=lambda x: x["prioridad"])
            plan["búsquedas"] = busquedas_validas
            
            return plan
            
        except Exception as e:
            print(f"⚠️ Error validando plan: {e}")
            return self._plan_fallback({})
    
    def _procesar_filtros_temporales(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa y convierte filtros temporales a formato estándar"""
        try:
            if "temporal" in filtros:
                temporal = filtros["temporal"]
                
                # Convertir diferentes formatos temporales
                if isinstance(temporal, str):
                    import re
                    
                    # Extraer números del texto temporal
                    if "días" in temporal or "dias" in temporal:
                        # Buscar números en el texto (ej: "últimos 7 días" -> 7)
                        match = re.search(r'(\d+)', temporal)
                        if match:
                            dias = int(match.group(1))
                            filtros["since"] = self._calcular_fecha_desde(dias)
                    elif "meses" in temporal:
                        match = re.search(r'(\d+)', temporal)
                        if match:
                            meses = int(match.group(1))
                            filtros["since"] = self._calcular_fecha_desde(meses * 30)
                    elif "horas" in temporal:
                        match = re.search(r'(\d+)', temporal)
                        if match:
                            horas = int(match.group(1))
                            filtros["since"] = self._calcular_fecha_desde(horas / 24)
                
                # Eliminar temporal original
                del filtros["temporal"]
            
            return filtros
            
        except Exception as e:
            print(f"⚠️ Error procesando filtros temporales: {e}")
            return filtros
    
    def _calcular_fecha_desde(self, dias: float) -> str:
        """Calcula la fecha desde hace X días"""
        try:
            fecha_desde = datetime.now(timezone.utc) - timedelta(days=dias)
            return fecha_desde.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
    
    def _plan_fallback(self, interpretacion: Dict[str, Any]) -> Dict[str, Any]:
        """Plan de fallback cuando falla el LLM"""
        print("🔄 [Planificador] Usando plan de fallback")
        
        consulta = interpretacion.get("consulta_reformulada", "")
        categoria = interpretacion.get("categoria", "ANÁLISIS_TEMÁTICO")
        
        # Plan básico según categoría
        if categoria == "TEMPORAL":
            return {
                "estrategia": "SIMPLE",
                "búsquedas": [{
                    "query": consulta,
                    "filtros": {"since": self._calcular_fecha_desde(30)},  # Últimos 30 días
                    "top_k": 30,
                    "prioridad": 1
                }],
                "síntesis_final": True,
                "tiempo_límite": "30 segundos"
            }
        elif categoria == "CONEXIONES":
            return {
                "estrategia": "MÚLTIPLE",
                "búsquedas": [
                    {
                        "query": consulta,
                        "filtros": {},
                        "top_k": 15,
                        "prioridad": 1
                    },
                    {
                        "query": consulta,
                        "filtros": {"node_type": "Documento"},
                        "top_k": 10,
                        "prioridad": 2
                    }
                ],
                "síntesis_final": True,
                "tiempo_límite": "45 segundos"
            }
        else:
            return {
                "estrategia": "SIMPLE",
                "búsquedas": [{
                    "query": consulta,
                    "filtros": {},
                    "top_k": 50,  # Aumentar de 15 a 50 para capturar más información
                    "prioridad": 1
                }],
                "síntesis_final": True,
                "tiempo_límite": "30 segundos"
            }
    
    def optimizar_plan_por_resultados(self, plan: Dict[str, Any], resultados_parciales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimiza el plan basándose en resultados parciales
        
        Args:
            plan: Plan original
            resultados_parciales: Resultados obtenidos hasta ahora
            
        Returns:
            Plan optimizado
        """
        try:
            if not resultados_parciales:
                return plan
            
            # Si tenemos pocos resultados, expandir búsquedas
            total_resultados = sum(len(resultados) for resultados in resultados_parciales)
            
            if total_resultados < 5:
                print("📈 [Planificador] Pocos resultados, expandiendo búsquedas...")
                
                # Aumentar top_k en búsquedas principales
                for busqueda in plan["búsquedas"][:2]:
                    busqueda["top_k"] = min(30, busqueda["top_k"] * 2)
            
            # Si tenemos muchos resultados, refinar búsquedas
            elif total_resultados > 50:
                print("🎯 [Planificador] Muchos resultados, refinando búsquedas...")
                
                # Reducir top_k y agregar filtros
                for busqueda in plan["búsquedas"]:
                    busqueda["top_k"] = max(5, busqueda["top_k"] // 2)
                    if "source" not in busqueda["filtros"]:
                        busqueda["filtros"]["node_type"] = "Documento"
            
            return plan
            
        except Exception as e:
            print(f"⚠️ Error optimizando plan: {e}")
            return plan

# Instancia global del planificador
_planificador = None

def get_planificador() -> BusquedaPlanificador:
    """Obtiene la instancia global del planificador"""
    global _planificador
    if _planificador is None:
        _planificador = BusquedaPlanificador()
    return _planificador

if __name__ == "__main__":
    # Prueba del planificador
    print("🧪 Probando Planificador de Búsquedas...")
    
    planificador = BusquedaPlanificador()
    
    # Prueba con interpretación de ejemplo
    interpretacion_ejemplo = {
        "categoria": "TEMPORAL",
        "conceptos_clave": ["cobre", "precio"],
        "consulta_reformulada": "evolución del precio del cobre",
        "filtro_temporal": "últimos 7 días",
        "necesita_sintesis": True,
        "confianza": 0.8
    }
    
    plan = planificador.planificar_busqueda(interpretacion_ejemplo)
    print(f"📋 Plan generado: {plan['estrategia']} con {len(plan['búsquedas'])} búsquedas")

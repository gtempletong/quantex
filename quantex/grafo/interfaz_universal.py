"""
Interfaz Universal del Sistema Grafo
Versión 1.0 - Punto de entrada unificado para todas las consultas al grafo
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

from .interpretador import get_interpretador
from .planificador import get_planificador
from .ejecutor import get_ejecutor

class GrafoInterface:
    """
    Interfaz universal para el sistema de consultas al grafo de conocimiento
    """
    
    def __init__(self):
        self.interpretador = get_interpretador()
        self.planificador = get_planificador()
        self.ejecutor = get_ejecutor()
        
        print("🧠 [GrafoInterface] Sistema de consultas inteligentes inicializado")
    
    def consultar_grafo(self, consulta: str, contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Método principal para consultar el grafo de conocimiento
        
        Args:
            consulta: Pregunta o consulta del usuario
            contexto: Contexto adicional (opcional)
            
        Returns:
            Resultado completo de la consulta
        """
        try:
            print(f"🔍 [GrafoInterface] Procesando consulta: '{consulta[:50]}...'")
            
            # PASO 1: Interpretar la consulta
            interpretacion = self.interpretador.interpretar_consulta(consulta)
            
            # PASO 2: Planificar la búsqueda
            plan = self.planificador.planificar_busqueda(interpretacion)
            
            # PASO 3: Ejecutar el plan
            resultado_ejecucion = self.ejecutor.ejecutar_plan(plan, interpretacion)
            
            # PASO 4: Formatear respuesta final
            respuesta_formateada = self.ejecutor.formatear_respuesta_final(resultado_ejecucion, interpretacion)
            
            # PASO 5: Construir resultado completo
            resultado_final = {
                "consulta_original": consulta,
                "interpretacion": interpretacion,
                "plan_ejecutado": plan,
                "resultados_encontrados": resultado_ejecucion.get("resultados", []),
                "sintesis": resultado_ejecucion.get("sintesis"),
                "respuesta_formateada": respuesta_formateada,
                "estadisticas": {
                    "total_resultados": resultado_ejecucion.get("total_resultados", 0),
                    "confianza_interpretacion": interpretacion.get("confianza", 0),
                    "confianza_sintesis": resultado_ejecucion.get("sintesis", {}).get("confianza", 0) if resultado_ejecucion.get("sintesis") else 0
                },
                "contexto": contexto
            }
            
            print(f"✅ [GrafoInterface] Consulta completada: {resultado_final['estadisticas']['total_resultados']} resultados")
            
            return resultado_final
            
        except Exception as e:
            print(f"❌ [GrafoInterface] Error procesando consulta: {e}")
            traceback.print_exc()
            
            return {
                "consulta_original": consulta,
                "error": str(e),
                "respuesta_formateada": f"Error al procesar la consulta: {str(e)}",
                "estadisticas": {
                    "total_resultados": 0,
                    "confianza_interpretacion": 0,
                    "confianza_sintesis": 0
                }
            }
    
    def consultar_grafo_simple(self, consulta: str) -> str:
        """
        Versión simplificada que solo retorna la respuesta formateada
        
        Args:
            consulta: Pregunta del usuario
            
        Returns:
            Respuesta formateada como string
        """
        try:
            resultado = self.consultar_grafo(consulta)
            return resultado.get("respuesta_formateada", "No se pudo procesar la consulta.")
        except Exception as e:
            return f"Error al consultar el grafo: {str(e)}"
    
    def detectar_consulta_grafo(self, consulta: str) -> bool:
        """
        Detecta si una consulta está dirigida al grafo de conocimiento
        
        Args:
            consulta: Consulta del usuario
            
        Returns:
            True si la consulta es para el grafo
        """
        return self.interpretador.detectar_intencion_grafo(consulta)
    
    def obtener_estadisticas_sistema(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de consultas
        
        Returns:
            Estadísticas del sistema
        """
        try:
            return {
                "sistema": "GrafoInterface v1.0",
                "componentes": {
                    "interpretador": "ConsultaInterpretador",
                    "planificador": "BusquedaPlanificador", 
                    "ejecutor": "BusquedaEjecutor"
                },
                "funcionalidades": [
                    "Interpretación inteligente de consultas",
                    "Planificación de estrategias de búsqueda",
                    "Ejecución optimizada de búsquedas semánticas",
                    "Síntesis automática de resultados",
                    "Formateo inteligente de respuestas"
                ],
                "estado": "Activo"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def consultar_grafo_con_filtros(self, consulta: str, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consulta el grafo con filtros específicos
        
        Args:
            consulta: Pregunta del usuario
            filtros: Filtros específicos para la búsqueda
            
        Returns:
            Resultado de la consulta con filtros aplicados
        """
        try:
            print(f"🔍 [GrafoInterface] Consulta con filtros: '{consulta[:30]}...'")
            
            # Interpretar consulta
            interpretacion = self.interpretador.interpretar_consulta(consulta)
            
            # Crear plan personalizado con filtros
            plan_personalizado = {
                "estrategia": "SIMPLE",
                "búsquedas": [{
                    "query": interpretacion.get("consulta_reformulada", consulta),
                    "filtros": filtros,
                    "top_k": filtros.get("top_k", 15),
                    "prioridad": 1
                }],
                "síntesis_final": True,
                "tiempo_límite": "30 segundos"
            }
            
            # Ejecutar con plan personalizado
            resultado_ejecucion = self.ejecutor.ejecutar_plan(plan_personalizado, interpretacion)
            respuesta_formateada = self.ejecutor.formatear_respuesta_final(resultado_ejecucion, interpretacion)
            
            return {
                "consulta_original": consulta,
                "filtros_aplicados": filtros,
                "resultados_encontrados": resultado_ejecucion.get("resultados", []),
                "sintesis": resultado_ejecucion.get("sintesis"),
                "respuesta_formateada": respuesta_formateada,
                "estadisticas": {
                    "total_resultados": resultado_ejecucion.get("total_resultados", 0)
                }
            }
            
        except Exception as e:
            print(f"❌ [GrafoInterface] Error en consulta con filtros: {e}")
            return {
                "consulta_original": consulta,
                "error": str(e),
                "respuesta_formateada": f"Error al procesar la consulta con filtros: {str(e)}"
            }

# Instancia global del sistema
_grafo_interface = None

def get_grafo_interface() -> GrafoInterface:
    """
    Obtiene la instancia global del sistema de consultas al grafo
    
    Returns:
        Instancia de GrafoInterface
    """
    global _grafo_interface
    if _grafo_interface is None:
        _grafo_interface = GrafoInterface()
    return _grafo_interface

# Funciones de conveniencia para compatibilidad
def consultar_grafo_inteligente(consulta: str) -> str:
    """
    Función de conveniencia para consultas simples al grafo
    
    Args:
        consulta: Pregunta del usuario
        
    Returns:
        Respuesta formateada
    """
    interface = get_grafo_interface()
    return interface.consultar_grafo_simple(consulta)

def es_consulta_grafo(consulta: str) -> bool:
    """
    Función de conveniencia para detectar consultas al grafo
    
    Args:
        consulta: Consulta del usuario
        
    Returns:
        True si es consulta al grafo
    """
    interface = get_grafo_interface()
    return interface.detectar_consulta_grafo(consulta)

if __name__ == "__main__":
    # Prueba del sistema completo
    print("🧪 Probando Sistema Grafo Completo...")
    
    interface = GrafoInterface()
    
    # Pruebas
    consultas_prueba = [
        "¿Qué sé sobre el cobre?",
        "¿Cómo se relaciona la inflación con las tasas de interés?",
        "¿Qué noticias recientes hay sobre China?",
        "¿Por qué subió el precio del cobre?"
    ]
    
    for consulta in consultas_prueba:
        print(f"\n🔍 Probando: {consulta}")
        
        # Detectar si es consulta al grafo
        es_grafo = interface.detectar_consulta_grafo(consulta)
        print(f"   ¿Es consulta al grafo? {es_grafo}")
        
        if es_grafo:
            # Procesar consulta
            resultado = interface.consultar_grafo_simple(consulta)
            print(f"   Respuesta: {resultado[:100]}...")
    
    # Estadísticas del sistema
    stats = interface.obtener_estadisticas_sistema()
    print(f"\n📊 Sistema: {stats['sistema']}")
    print(f"📊 Estado: {stats['estado']}")

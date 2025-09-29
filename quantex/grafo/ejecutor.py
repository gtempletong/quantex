"""
Ejecutor de Búsquedas - Sistema Grafo
Versión 1.0 - Ejecución inteligente de búsquedas y síntesis de resultados
"""

import os
import sys
import json
import traceback
from typing import Dict, Any, List, Optional

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.ai_services import ai_services
from quantex.core import llm_manager
from quantex.core.semantic_search_engine import get_semantic_engine

class BusquedaEjecutor:
    """
    Ejecuta búsquedas en el grafo de conocimiento y sintetiza resultados
    """
    
    def __init__(self):
        self.ai_services = ai_services
        self.llm_manager = llm_manager
        
        # Asegurar que los servicios de AI estén inicializados
        if not hasattr(self.ai_services, 'embedding_model') or self.ai_services.embedding_model is None:
            print("🔧 [Ejecutor] Inicializando servicios de AI...")
            self.ai_services.initialize()
        
        self.semantic_engine = get_semantic_engine()
        
        # Cargar prompt del sintetizador
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Carga el prompt del sintetizador"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'sintetizador.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Error cargando prompt del sintetizador: {e}")
            return "Sintetiza inteligentemente los resultados de búsqueda del grafo de conocimiento."
    
    def ejecutar_plan(self, plan: Dict[str, Any], interpretacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el plan de búsqueda y sintetiza resultados
        
        Args:
            plan: Plan de búsqueda generado por el planificador
            interpretacion: Interpretación original de la consulta
            
        Returns:
            Resultados sintetizados
        """
        try:
            print(f"🚀 [Ejecutor] Ejecutando plan: {plan['estrategia']}")
            
            # Ejecutar búsquedas según el plan
            resultados_todos = []
            
            for busqueda in plan["búsquedas"]:
                print(f"  🔍 Ejecutando búsqueda: '{busqueda['query'][:30]}...'")
                
                resultados_busqueda = self._ejecutar_busqueda_individual(busqueda, interpretacion)
                resultados_todos.extend(resultados_busqueda)
                
                print(f"    ✅ Encontrados {len(resultados_busqueda)} resultados")
            
            # Deduplicar resultados
            resultados_unicos = self._deduplicar_resultados(resultados_todos)
            
            print(f"📊 [Ejecutor] Total resultados únicos: {len(resultados_unicos)}")
            
            # Verificar si es query directo (sin síntesis)
            es_query_directo = interpretacion.get("es_query_directo", False)
            necesita_sintesis = plan.get("síntesis_final", True) and not es_query_directo
            
            # Sintetizar solo si no es query directo
            if necesita_sintesis and resultados_unicos:
                sintesis = self._sintetizar_resultados(resultados_unicos, interpretacion)
                return {
                    "resultados": resultados_unicos,
                    "sintesis": sintesis,
                    "plan_ejecutado": plan,
                    "total_resultados": len(resultados_unicos),
                    "es_query_directo": False
                }
            else:
                return {
                    "resultados": resultados_unicos,
                    "sintesis": None,
                    "plan_ejecutado": plan,
                    "total_resultados": len(resultados_unicos),
                    "es_query_directo": es_query_directo
                }
            
        except Exception as e:
            print(f"❌ [Ejecutor] Error ejecutando plan: {e}")
            traceback.print_exc()
            
            return {
                "resultados": [],
                "sintesis": {"error": str(e)},
                "plan_ejecutado": plan,
                "total_resultados": 0
            }
    
    def _ejecutar_busqueda_individual(self, busqueda: Dict[str, Any], interpretacion: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta una búsqueda individual"""
        try:
            query = busqueda["query"]
            filtros = busqueda["filtros"]
            top_k = busqueda["top_k"]
            
            # Convertir filtros temporales si existen
            meses = None
            if "since" in filtros:
                # Convertir fecha ISO a meses aproximados
                from datetime import datetime, timezone
                try:
                    since_date = datetime.fromisoformat(filtros["since"])
                    now = datetime.now(timezone.utc)
                    dias_diff = (now - since_date).days
                    
                    # Para períodos muy cortos, usar días en lugar de meses
                    if dias_diff <= 1:
                        meses = 0.03  # ~1 día
                    elif dias_diff <= 7:
                        meses = 0.23  # ~7 días
                    elif dias_diff <= 30:
                        meses = 1.0   # ~1 mes
                    else:
                        meses = dias_diff / 30  # Convertir a meses
                        
                except Exception:
                    meses = None  # Usar filtro por defecto del motor semántico
                
                # Remover since de filtros (el motor semántico usa meses)
                filtros_clean = {k: v for k, v in filtros.items() if k != "since"}
            else:
                filtros_clean = filtros
                meses = None  # Usar filtro por defecto del motor semántico
            
            # Aumentar límite de resultados para queries directos
            if interpretacion.get("es_query_directo", False):
                top_k = max(top_k, 50)  # Mínimo 50 para queries directos
            
            # Ejecutar búsqueda con el motor semántico
            resultados = self.semantic_engine.search_knowledge(
                query=query,
                top_k=top_k,
                months=meses,
                filters=filtros_clean,
                include_connections=True
            )
            
            return resultados
            
        except Exception as e:
            print(f"⚠️ Error en búsqueda individual: {e}")
            return []
    
    def _deduplicar_resultados(self, resultados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplica resultados por ID"""
        try:
            ids_vistos = set()
            resultados_unicos = []
            
            for resultado in resultados:
                resultado_id = resultado.get("id")
                if resultado_id and resultado_id not in ids_vistos:
                    ids_vistos.add(resultado_id)
                    resultados_unicos.append(resultado)
            
            return resultados_unicos
            
        except Exception as e:
            print(f"⚠️ Error deduplicando resultados: {e}")
            return resultados
    
    def _sintetizar_resultados(self, resultados: List[Dict[str, Any]], interpretacion: Dict[str, Any]) -> Dict[str, Any]:
        """Sintetiza los resultados usando IA"""
        try:
            print("🧠 [Ejecutor] Sintetizando resultados...")
            
            # Preparar contexto para la síntesis
            contexto_resultados = self._preparar_contexto_sintesis(resultados)
            
            # Usar LLM para sintetizar
            response = self.llm_manager.generate_structured_output(
                system_prompt=self.prompt_template,
                user_prompt=f"""
Consulta original: {interpretacion.get('consulta_reformulada', '')}
Categoría: {interpretacion.get('categoria', '')}
Conceptos clave: {interpretacion.get('conceptos_clave', [])}

Resultados encontrados:
{contexto_resultados}
""",
                model_name="claude-3-haiku-20240307",
                output_schema={
                    "type": "object",
                    "properties": {
                        "tipo_sintesis": {"type": "string"},
                        "resumen_ejecutivo": {"type": "string"},
                        "hallazgos_principales": {"type": "array", "items": {"type": "string"}},
                        "conexiones": {"type": "array", "items": {"type": "string"}},
                        "insights": {"type": "array", "items": {"type": "string"}},
                        "fuentes_principales": {"type": "array", "items": {"type": "string"}},
                        "próximos_pasos": {"type": ["array", "null"], "items": {"type": "string"}},
                        "confianza": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    },
                    "required": ["tipo_sintesis", "resumen_ejecutivo", "hallazgos_principales", "confianza"]
                }
            )
            
            # Validar y limpiar síntesis
            sintesis = self._validar_sintesis(response)
            
            print(f"✅ [Ejecutor] Síntesis completada: {sintesis['tipo_sintesis']}")
            
            return sintesis
            
        except Exception as e:
            print(f"❌ [Ejecutor] Error sintetizando: {e}")
            traceback.print_exc()
            
            return {
                "tipo_sintesis": "INFORMATIVA",
                "resumen_ejecutivo": "Error al procesar los resultados encontrados.",
                "hallazgos_principales": [f"Se encontraron {len(resultados)} resultados relevantes"],
                "conexiones": [],
                "insights": [],
                "fuentes_principales": [],
                "próximos_pasos": None,
                "confianza": 0.3
            }
    
    def _preparar_contexto_sintesis(self, resultados: List[Dict[str, Any]]) -> str:
        """Prepara el contexto de resultados para la síntesis"""
        try:
            contexto = f"Total de resultados: {len(resultados)}\n\n"
            
            for i, resultado in enumerate(resultados[:10], 1):  # Limitar a 10 para no sobrecargar
                contexto += f"Resultado {i}:\n"
                contexto += f"  Título: {resultado.get('title', 'Sin título')}\n"
                contexto += f"  Tipo: {resultado.get('node_type', 'Desconocido')}\n"
                contexto += f"  Fuente: {resultado.get('source', 'Desconocida')}\n"
                contexto += f"  Relevancia: {resultado.get('score', 0):.3f}\n"
                contexto += f"  Conexiones: {resultado.get('connections', 0)}\n"
                contexto += f"  Contenido: {resultado.get('content', '')[:300]}...\n"
                contexto += f"  Fecha: {resultado.get('created_at', 'Desconocida')}\n\n"
            
            if len(resultados) > 10:
                contexto += f"... y {len(resultados) - 10} resultados más.\n"
            
            return contexto
            
        except Exception as e:
            print(f"⚠️ Error preparando contexto: {e}")
            return f"Se encontraron {len(resultados)} resultados relevantes."
    
    def _validar_sintesis(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y limpia la síntesis del LLM"""
        try:
            sintesis = {
                "tipo_sintesis": response.get("tipo_sintesis", "INFORMATIVA"),
                "resumen_ejecutivo": response.get("resumen_ejecutivo", ""),
                "hallazgos_principales": response.get("hallazgos_principales", []),
                "conexiones": response.get("conexiones", []),
                "insights": response.get("insights", []),
                "fuentes_principales": response.get("fuentes_principales", []),
                "próximos_pasos": response.get("próximos_pasos"),
                "confianza": float(response.get("confianza", 0.7))
            }
            
            # Validar confianza
            sintesis["confianza"] = max(0.0, min(1.0, sintesis["confianza"]))
            
            # Asegurar que hay al menos un hallazgo
            if not sintesis["hallazgos_principales"]:
                sintesis["hallazgos_principales"] = ["Se encontró información relevante en el grafo de conocimiento."]
            
            return sintesis
            
        except Exception as e:
            print(f"⚠️ Error validando síntesis: {e}")
            return {
                "tipo_sintesis": "INFORMATIVA",
                "resumen_ejecutivo": "Información encontrada en el grafo de conocimiento.",
                "hallazgos_principales": ["Resultados procesados exitosamente"],
                "conexiones": [],
                "insights": [],
                "fuentes_principales": [],
                "próximos_pasos": None,
                "confianza": 0.5
            }
    
    def formatear_respuesta_final(self, resultado_ejecucion: Dict[str, Any], interpretacion: Dict[str, Any]) -> str:
        """Formatea la respuesta final para el usuario"""
        try:
            sintesis = resultado_ejecucion.get("sintesis", {})
            resultados = resultado_ejecucion.get("resultados", [])
            es_query_directo = resultado_ejecucion.get("es_query_directo", False)
            
            # Para queries directos, mostrar lista sin síntesis
            if es_query_directo:
                return self._formatear_query_directo(resultados, interpretacion)
            elif not sintesis:
                return self._formatear_sin_sintesis(resultados, interpretacion)
            
            # Formatear con síntesis
            respuesta = f"🧠 **{sintesis['tipo_sintesis']}**\n\n"
            respuesta += f"📋 **Resumen:** {sintesis['resumen_ejecutivo']}\n\n"
            
            if sintesis.get("hallazgos_principales"):
                respuesta += "🔍 **Hallazgos principales:**\n"
                for hallazgo in sintesis["hallazgos_principales"]:
                    respuesta += f"• {hallazgo}\n"
                respuesta += "\n"
            
            if sintesis.get("conexiones"):
                respuesta += "🔗 **Conexiones identificadas:**\n"
                for conexion in sintesis["conexiones"]:
                    respuesta += f"• {conexion}\n"
                respuesta += "\n"
            
            if sintesis.get("insights"):
                respuesta += "💡 **Insights relevantes:**\n"
                for insight in sintesis["insights"]:
                    respuesta += f"• {insight}\n"
                respuesta += "\n"
            
            if sintesis.get("fuentes_principales"):
                respuesta += "📚 **Fuentes principales:**\n"
                for fuente in sintesis["fuentes_principales"]:
                    respuesta += f"• {fuente}\n"
                respuesta += "\n"
            
            if sintesis.get("próximos_pasos"):
                respuesta += "🎯 **Próximos pasos sugeridos:**\n"
                for paso in sintesis["próximos_pasos"]:
                    respuesta += f"• {paso}\n"
                respuesta += "\n"
            
            respuesta += f"📊 **Estadísticas:** {len(resultados)} resultados analizados, confianza: {sintesis.get('confianza', 0):.1%}"
            
            return respuesta
            
        except Exception as e:
            print(f"⚠️ Error formateando respuesta: {e}")
            return f"Se encontraron {len(resultados)} resultados relevantes. Error al formatear la síntesis."
    
    def _formatear_query_directo(self, resultados: List[Dict[str, Any]], interpretacion: Dict[str, Any]) -> str:
        """Formatea respuesta para queries directos (lista de datos)"""
        try:
            consulta = interpretacion.get("consulta_reformulada", "")
            
            respuesta = f"📋 **Lista de resultados para: '{consulta}'**\n\n"
            respuesta += f"**Total encontrados: {len(resultados)}**\n\n"
            
            for i, resultado in enumerate(resultados, 1):
                respuesta += f"**{i}. {resultado.get('title', 'Sin título')}**\n"
                respuesta += f"   📅 Fecha: {resultado.get('created_at', 'Desconocida')}\n"
                respuesta += f"   📊 Fuente: {resultado.get('source', 'Desconocida')}\n"
                respuesta += f"   🏷️ Tipo: {resultado.get('node_type', 'Desconocido')}\n"
                respuesta += f"   📊 Relevancia: {resultado.get('score', 0):.2f}\n"
                respuesta += f"   📝 Contenido: {resultado.get('content', '')[:300]}{'...' if len(resultado.get('content', '')) > 300 else ''}\n\n"
            
            return respuesta
            
        except Exception as e:
            print(f"⚠️ Error formateando query directo: {e}")
            return f"Se encontraron {len(resultados)} resultados relevantes."
    
    def _formatear_sin_sintesis(self, resultados: List[Dict[str, Any]], interpretacion: Dict[str, Any]) -> str:
        """Formatea respuesta cuando no hay síntesis"""
        try:
            consulta = interpretacion.get("consulta_reformulada", "")
            
            respuesta = f"🔍 **Resultados encontrados para: '{consulta}'**\n\n"
            
            for i, resultado in enumerate(resultados[:5], 1):
                respuesta += f"**{i}. {resultado.get('title', 'Sin título')}**\n"
                respuesta += f"   📊 Relevancia: {resultado.get('score', 0):.2f}\n"
                respuesta += f"   🔗 Conexiones: {resultado.get('connections', 0)}\n"
                respuesta += f"   📝 {resultado.get('content', '')[:200]}{'...' if len(resultado.get('content', '')) > 200 else ''}\n\n"
            
            if len(resultados) > 5:
                respuesta += f"*... y {len(resultados) - 5} resultados más.*\n\n"
            
            return respuesta
            
        except Exception as e:
            print(f"⚠️ Error formateando sin síntesis: {e}")
            return f"Se encontraron {len(resultados)} resultados relevantes."

# Instancia global del ejecutor
_ejecutor = None

def get_ejecutor() -> BusquedaEjecutor:
    """Obtiene la instancia global del ejecutor"""
    global _ejecutor
    if _ejecutor is None:
        _ejecutor = BusquedaEjecutor()
    return _ejecutor

if __name__ == "__main__":
    # Prueba del ejecutor
    print("🧪 Probando Ejecutor de Búsquedas...")
    
    ejecutor = BusquedaEjecutor()
    
    # Prueba con plan de ejemplo
    plan_ejemplo = {
        "estrategia": "SIMPLE",
        "búsquedas": [{
            "query": "cobre precio evolución",
            "filtros": {},
            "top_k": 10,
            "prioridad": 1
        }],
        "síntesis_final": True,
        "tiempo_límite": "30 segundos"
    }
    
    interpretacion_ejemplo = {
        "categoria": "ANÁLISIS_TEMÁTICO",
        "consulta_reformulada": "evolución del precio del cobre"
    }
    
    print("Ejecutando plan de ejemplo...")
    resultado = ejecutor.ejecutar_plan(plan_ejemplo, interpretacion_ejemplo)
    print(f"Resultado: {resultado['total_resultados']} resultados encontrados")

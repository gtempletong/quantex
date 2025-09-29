# quantex/core/autoconocimiento/insights_predictivos.py

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import numpy as np
from collections import defaultdict, Counter

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core import llm_manager

class PredictiveInsightsEngine:
    """
    Motor de insights predictivos que analiza patrones en el grafo de conocimiento
    para generar predicciones y recomendaciones automáticas.
    """
    
    def __init__(self):
        self.db = db
        self.ai_services = ai_services
        self.llm_manager = llm_manager
    
    def analyze_temporal_patterns(self, months: int = 6) -> Dict[str, Any]:
        """
        Analiza patrones temporales en el grafo para identificar tendencias
        """
        try:
            print(f"📈 [Insights Predictivos] Analizando patrones temporales (últimos {months} meses)")
            
            # Calcular fecha límite
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
            
            # Obtener todos los nodos recientes con paginación
            nodes = []
            page_size = 1000
            offset = 0
            
            while True:
                response = self.db.supabase.table('nodes').select('*').gte('created_at', cutoff_date.isoformat()).range(offset, offset + page_size - 1).execute()
                
                if not response.data:
                    break
                    
                nodes.extend(response.data)
                print(f"  -> Obtenidos {len(response.data)} nodos recientes (offset: {offset})")
                
                if len(response.data) < page_size:
                    break
                    
                offset += page_size
            
            if not nodes:
                return {"error": "No hay datos suficientes para análisis temporal"}
            
            # Análisis de frecuencia por tipo de nodo
            node_types = [node.get('type', 'Desconocido') for node in nodes]
            type_frequency = Counter(node_types)
            
            # Análisis de frecuencia por tema (extraído de labels)
            topics = []
            for node in nodes:
                label = node.get('label', '')
                if label:
                    # Extraer palabras clave principales
                    words = label.lower().split()
                    topics.extend([w for w in words if len(w) > 3])
            
            topic_frequency = Counter(topics)
            
            # Análisis de crecimiento temporal
            creation_dates = []
            for node in nodes:
                created_at = node.get('created_at')
                if created_at:
                    try:
                        if 'Z' in created_at:
                            date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            date = datetime.fromisoformat(created_at)
                        creation_dates.append(date)
                    except:
                        continue
            
            # Calcular tendencia de crecimiento
            if len(creation_dates) > 1:
                creation_dates.sort()
                growth_rate = self._calculate_growth_rate(creation_dates)
            else:
                growth_rate = 0
            
            return {
                "total_nodes": len(nodes),
                "time_period_months": months,
                "node_types": dict(type_frequency.most_common(10)),
                "top_topics": dict(topic_frequency.most_common(15)),
                "growth_rate": growth_rate,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Insights Predictivos] Error en análisis temporal: {e}")
            return {"error": str(e)}
    
    def analyze_connection_patterns(self) -> Dict[str, Any]:
        """
        Analiza patrones de conexiones entre nodos para identificar clusters y hubs
        """
        try:
            print("🔗 [Insights Predictivos] Analizando patrones de conexiones")
            
            # Obtener todas las conexiones con paginación
            edges = []
            page_size = 1000
            offset = 0
            
            while True:
                response = self.db.supabase.table('edges').select('*').range(offset, offset + page_size - 1).execute()
                
                if not response.data:
                    break
                    
                edges.extend(response.data)
                print(f"  -> Obtenidas {len(response.data)} conexiones (offset: {offset})")
                
                if len(response.data) < page_size:
                    break
                    
                offset += page_size
            
            if not edges:
                return {"error": "No hay conexiones para analizar"}
            
            # Construir grafo de conexiones
            connection_graph = defaultdict(list)
            node_degrees = defaultdict(int)
            
            for edge in edges:
                source = edge.get('source_id')
                target = edge.get('target_id')
                if source and target:
                    connection_graph[source].append(target)
                    connection_graph[target].append(source)
                    node_degrees[source] += 1
                    node_degrees[target] += 1
            
            # Identificar hubs (nodos con muchas conexiones)
            hubs = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Calcular métricas de red
            total_nodes = len(connection_graph)
            total_edges = len(edges)
            avg_degree = sum(node_degrees.values()) / total_nodes if total_nodes > 0 else 0
            
            # Identificar clusters usando análisis de componentes conectados
            clusters = self._find_connected_components(connection_graph)
            
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "average_degree": round(avg_degree, 2),
                "top_hubs": [{"node_id": node_id, "connections": degree} for node_id, degree in hubs],
                "clusters_count": len(clusters),
                "largest_cluster_size": max(len(cluster) for cluster in clusters) if clusters else 0,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Insights Predictivos] Error en análisis de conexiones: {e}")
            return {"error": str(e)}
    
    def generate_predictive_insights(self, temporal_data: Dict, connection_data: Dict) -> str:
        """
        Genera insights predictivos usando IA basado en los patrones analizados
        """
        try:
            print("🧠 [Insights Predictivos] Generando insights con IA")
            
            context = f"""
Análisis Temporal:
- Total de nodos: {temporal_data.get('total_nodes', 0)}
- Período analizado: {temporal_data.get('time_period_months', 0)} meses
- Tipos de nodos más frecuentes: {temporal_data.get('node_types', {})}
- Temas más frecuentes: {temporal_data.get('top_topics', {})}
- Tasa de crecimiento: {temporal_data.get('growth_rate', 0)}

Análisis de Conexiones:
- Total de nodos conectados: {connection_data.get('total_nodes', 0)}
- Total de conexiones: {connection_data.get('total_edges', 0)}
- Grado promedio: {connection_data.get('average_degree', 0)}
- Hubs principales: {connection_data.get('top_hubs', [])}
- Número de clusters: {connection_data.get('clusters_count', 0)}
- Cluster más grande: {connection_data.get('largest_cluster_size', 0)} nodos
"""
            
            prompt = f"""
Eres un analista experto en grafos de conocimiento. Analiza los siguientes datos de un grafo de conocimiento financiero y genera insights predictivos y recomendaciones estratégicas.

{context}

Instrucciones:
1. Identifica patrones y tendencias significativas
2. Genera predicciones sobre la evolución del conocimiento
3. Proporciona recomendaciones específicas para optimizar el grafo
4. Destaca oportunidades de crecimiento y conexiones faltantes
5. Mantén un tono profesional pero accesible
6. Limita la respuesta a máximo 400 palabras

Responde en español y enfócate en insights accionables.
"""
            
            response = self.llm_manager.generate_completion(
                task_complexity='reasoning',
                system_prompt=prompt,
                user_prompt="Genera insights predictivos basados en estos datos del grafo de conocimiento."
            )
            
            return response.get('raw_text', 'No se pudieron generar insights')
            
        except Exception as e:
            print(f"❌ [Insights Predictivos] Error generando insights: {e}")
            return f"Error generando insights: {str(e)}"
    
    def _calculate_growth_rate(self, dates: List[datetime]) -> float:
        """Calcula la tasa de crecimiento basada en fechas de creación"""
        if len(dates) < 2:
            return 0
        
        # Agrupar por semana para calcular crecimiento
        weekly_counts = defaultdict(int)
        for date in dates:
            week_key = date.strftime('%Y-W%U')
            weekly_counts[week_key] += 1
        
        if len(weekly_counts) < 2:
            return 0
        
        weeks = sorted(weekly_counts.keys())
        counts = [weekly_counts[week] for week in weeks]
        
        # Calcular tasa de crecimiento simple
        if counts[0] > 0:
            growth_rate = (counts[-1] - counts[0]) / counts[0] * 100
        else:
            growth_rate = 0
        
        return round(growth_rate, 2)
    
    def _find_connected_components(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Encuentra componentes conectados en el grafo"""
        visited = set()
        components = []
        
        def dfs(node, component):
            visited.add(node)
            component.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, component)
        
        for node in graph:
            if node not in visited:
                component = []
                dfs(node, component)
                if component:
                    components.append(component)
        
        return components

def generate_predictive_insights_report(months: int = 6) -> Dict[str, Any]:
    """
    Función principal para generar un reporte completo de insights predictivos
    """
    try:
        print("🚀 [Insights Predictivos] Iniciando análisis completo")
        
        engine = PredictiveInsightsEngine()
        
        # Realizar análisis temporal
        temporal_data = engine.analyze_temporal_patterns(months)
        
        # Realizar análisis de conexiones
        connection_data = engine.analyze_connection_patterns()
        
        # Generar insights con IA
        insights = engine.generate_predictive_insights(temporal_data, connection_data)
        
        return {
            "success": True,
            "temporal_analysis": temporal_data,
            "connection_analysis": connection_data,
            "predictive_insights": insights,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [Insights Predictivos] Error en análisis completo: {e}")
        return {
            "success": False,
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Ejecutar análisis completo
    report = generate_predictive_insights_report()
    print("\n" + "="*50)
    print("REPORTE DE INSIGHTS PREDICTIVOS")
    print("="*50)
    print(json.dumps(report, indent=2, ensure_ascii=False))

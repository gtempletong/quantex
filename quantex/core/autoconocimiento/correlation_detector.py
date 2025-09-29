# quantex/core/autoconocimiento/correlation_detector.py

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Set
import numpy as np
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import networkx as nx

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core import llm_manager

class CorrelationDetector:
    """
    Detector de correlaciones avanzado que identifica patrones y relaciones
    ocultas entre nodos del grafo de conocimiento.
    """
    
    def __init__(self):
        self.db = db
        self.ai_services = ai_services
        self.llm_manager = llm_manager
    
    def detect_semantic_correlations(self, min_nodes: int = 50) -> Dict[str, Any]:
        """
        Detecta correlaciones semánticas entre nodos usando análisis de texto
        """
        try:
            print(f"🔍 [Correlaciones] Detectando correlaciones semánticas (mínimo {min_nodes} nodos)")
            
            # Obtener todos los nodos con paginación
            nodes = []
            page_size = 1000
            offset = 0
            
            while True:
                response = self.db.supabase.table('nodes').select('*').range(offset, offset + page_size - 1).execute()
                
                if not response.data:
                    break
                    
                nodes.extend(response.data)
                print(f"  -> Obtenidos {len(response.data)} nodos (offset: {offset})")
                
                if len(response.data) < page_size:
                    break
                    
                offset += page_size
            
            if not nodes or len(nodes) < min_nodes:
                return {"error": f"No hay suficientes nodos para análisis (mínimo {min_nodes})"}
            
            # Preparar datos para análisis
            node_texts = []
            node_ids = []
            node_labels = []
            
            for node in nodes:
                content = node.get('content', '')
                label = node.get('label', '')
                
                if content and len(content.strip()) > 10:  # Solo nodos con contenido sustancial
                    # Combinar label y content para análisis
                    combined_text = f"{label} {content}".strip()
                    node_texts.append(combined_text)
                    node_ids.append(node.get('id'))
                    node_labels.append(label)
            
            if len(node_texts) < min_nodes:
                return {"error": f"No hay suficientes nodos con contenido para análisis (mínimo {min_nodes})"}
            
            print(f"  -> Analizando {len(node_texts)} nodos con contenido")
            
            # Análisis TF-IDF para encontrar similitudes semánticas
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2
            )
            
            tfidf_matrix = vectorizer.fit_transform(node_texts)
            
            # Calcular similitudes coseno
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Encontrar pares altamente correlacionados
            correlations = self._find_high_correlations(similarity_matrix, node_ids, node_labels, threshold=0.3)
            
            # Detectar clusters semánticos
            clusters = self._detect_semantic_clusters(similarity_matrix, node_ids, node_labels)
            
            # Análisis de palabras clave más importantes
            feature_names = vectorizer.get_feature_names_out()
            important_features = self._extract_important_features(tfidf_matrix, feature_names)
            
            return {
                "total_nodes_analyzed": len(node_texts),
                "high_correlations": correlations,
                "semantic_clusters": clusters,
                "important_features": important_features,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Correlaciones] Error en análisis semántico: {e}")
            return {"error": str(e)}
    
    def detect_structural_correlations(self) -> Dict[str, Any]:
        """
        Detecta correlaciones estructurales basadas en conexiones del grafo
        """
        try:
            print("🔗 [Correlaciones] Detectando correlaciones estructurales")
            
            # Obtener nodos y conexiones
            nodes_response = self.db.supabase.table('nodes').select('*').execute()
            edges_response = self.db.supabase.table('edges').select('*').execute()
            
            if not nodes_response.data or not edges_response.data:
                return {"error": "No hay suficientes datos estructurales para análisis"}
            
            nodes = nodes_response.data
            edges = edges_response.data
            
            # Construir grafo de red
            G = nx.Graph()
            
            # Agregar nodos
            for node in nodes:
                G.add_node(node.get('id'), **node)
            
            # Agregar conexiones
            for edge in edges:
                source = edge.get('source_id')
                target = edge.get('target_id')
                if source and target:
                    G.add_edge(source, target)
            
            # Calcular métricas de centralidad
            centrality_measures = self._calculate_centrality_measures(G)
            
            # Detectar comunidades usando algoritmos de clustering
            communities = self._detect_communities(G)
            
            # Encontrar patrones de conexión
            connection_patterns = self._analyze_connection_patterns(G)
            
            # Identificar nodos puente
            bridge_nodes = self._identify_bridge_nodes(G)
            
            return {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "centrality_measures": centrality_measures,
                "communities": communities,
                "connection_patterns": connection_patterns,
                "bridge_nodes": bridge_nodes,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Correlaciones] Error en análisis estructural: {e}")
            return {"error": str(e)}
    
    def detect_temporal_correlations(self, months: int = 6) -> Dict[str, Any]:
        """
        Detecta correlaciones temporales entre nodos creados en períodos similares
        """
        try:
            print(f"⏰ [Correlaciones] Detectando correlaciones temporales (últimos {months} meses)")
            
            # Calcular fecha límite
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
            
            # Obtener nodos recientes
            nodes_response = self.db.supabase.table('nodes').select('*').gte('created_at', cutoff_date.isoformat()).execute()
            
            if not nodes_response.data:
                return {"error": "No hay datos temporales suficientes para análisis"}
            
            nodes = nodes_response.data
            
            # Agrupar nodos por períodos temporales
            temporal_groups = defaultdict(list)
            
            for node in nodes:
                created_at = node.get('created_at')
                if created_at:
                    try:
                        if 'Z' in created_at:
                            date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            date = datetime.fromisoformat(created_at)
                        
                        # Agrupar por semana
                        week_key = date.strftime('%Y-W%U')
                        temporal_groups[week_key].append(node)
                    except:
                        continue
            
            # Analizar correlaciones temporales
            temporal_correlations = self._analyze_temporal_patterns(temporal_groups)
            
            # Detectar secuencias de creación
            creation_sequences = self._detect_creation_sequences(nodes)
            
            # Análisis de co-ocurrencia temporal
            co_occurrence_patterns = self._analyze_co_occurrence_patterns(temporal_groups)
            
            return {
                "time_period_months": months,
                "temporal_groups": len(temporal_groups),
                "temporal_correlations": temporal_correlations,
                "creation_sequences": creation_sequences,
                "co_occurrence_patterns": co_occurrence_patterns,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Correlaciones] Error en análisis temporal: {e}")
            return {"error": str(e)}
    
    def generate_correlation_insights(self, semantic_data: Dict, structural_data: Dict, temporal_data: Dict) -> str:
        """
        Genera insights sobre correlaciones usando IA
        """
        try:
            print("🧠 [Correlaciones] Generando insights con IA")
            
            context = f"""
Análisis de Correlaciones del Grafo de Conocimiento:

Análisis Semántico:
- Nodos analizados: {semantic_data.get('total_nodes_analyzed', 0)}
- Correlaciones altas encontradas: {len(semantic_data.get('high_correlations', []))}
- Clusters semánticos: {len(semantic_data.get('semantic_clusters', []))}
- Características importantes: {len(semantic_data.get('important_features', []))}

Análisis Estructural:
- Total nodos: {structural_data.get('total_nodes', 0)}
- Total conexiones: {structural_data.get('total_edges', 0)}
- Comunidades detectadas: {len(structural_data.get('communities', []))}
- Nodos puente: {len(structural_data.get('bridge_nodes', []))}

Análisis Temporal:
- Período analizado: {temporal_data.get('time_period_months', 0)} meses
- Grupos temporales: {temporal_data.get('temporal_groups', 0)}
- Patrones de co-ocurrencia: {len(temporal_data.get('co_occurrence_patterns', []))}
"""
            
            prompt = f"""
Eres un analista experto en grafos de conocimiento y detección de patrones. Analiza los siguientes datos de correlaciones de un grafo de conocimiento financiero y genera insights profundos.

{context}

Instrucciones:
1. Identifica las correlaciones más significativas y su importancia
2. Analiza patrones ocultos y relaciones no evidentes
3. Proporciona recomendaciones para fortalecer conexiones débiles
4. Destaca oportunidades de crecimiento del grafo
5. Identifica nodos o temas que podrían beneficiarse de más conexiones
6. Mantén un tono profesional pero accesible
7. Limita la respuesta a máximo 400 palabras

Responde en español y enfócate en insights accionables sobre correlaciones.
"""
            
            response = self.llm_manager.generate_completion(
                task_complexity='reasoning',
                system_prompt=prompt,
                user_prompt="Genera insights sobre las correlaciones encontradas en el grafo de conocimiento."
            )
            
            return response.get('raw_text', 'No se pudieron generar insights de correlaciones')
            
        except Exception as e:
            print(f"❌ [Correlaciones] Error generando insights: {e}")
            return f"Error generando insights de correlaciones: {str(e)}"
    
    def _find_high_correlations(self, similarity_matrix: np.ndarray, node_ids: List[str], node_labels: List[str], threshold: float = 0.3) -> List[Dict]:
        """Encuentra pares de nodos con alta correlación semántica"""
        correlations = []
        
        for i in range(len(similarity_matrix)):
            for j in range(i + 1, len(similarity_matrix)):
                similarity = similarity_matrix[i][j]
                if similarity > threshold:
                    correlations.append({
                        "node1_id": node_ids[i],
                        "node1_label": node_labels[i],
                        "node2_id": node_ids[j],
                        "node2_label": node_labels[j],
                        "similarity_score": round(similarity, 3)
                    })
        
        # Ordenar por similitud descendente
        correlations.sort(key=lambda x: x['similarity_score'], reverse=True)
        return correlations[:20]  # Top 20 correlaciones
    
    def _detect_semantic_clusters(self, similarity_matrix: np.ndarray, node_ids: List[str], node_labels: List[str]) -> List[Dict]:
        """Detecta clusters semánticos usando DBSCAN"""
        try:
            # Usar DBSCAN para clustering
            clustering = DBSCAN(eps=0.3, min_samples=3, metric='precomputed')
            
            # Convertir similitud a distancia
            distance_matrix = 1 - similarity_matrix
            
            cluster_labels = clustering.fit_predict(distance_matrix)
            
            # Agrupar nodos por cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                if label != -1:  # Ignorar outliers
                    clusters[label].append({
                        "node_id": node_ids[i],
                        "node_label": node_labels[i]
                    })
            
            # Convertir a lista y agregar métricas
            cluster_list = []
            for cluster_id, nodes in clusters.items():
                cluster_list.append({
                    "cluster_id": cluster_id,
                    "size": len(nodes),
                    "nodes": nodes
                })
            
            return cluster_list
            
        except Exception as e:
            print(f"⚠️ Error en clustering semántico: {e}")
            return []
    
    def _extract_important_features(self, tfidf_matrix: np.ndarray, feature_names: List[str]) -> List[Dict]:
        """Extrae las características más importantes del análisis TF-IDF"""
        # Calcular importancia promedio de cada característica
        feature_importance = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # Crear lista de características con su importancia
        features = []
        for i, importance in enumerate(feature_importance):
            if importance > 0.01:  # Solo características con importancia significativa
                features.append({
                    "feature": feature_names[i],
                    "importance": round(importance, 4)
                })
        
        # Ordenar por importancia descendente
        features.sort(key=lambda x: x['importance'], reverse=True)
        return features[:30]  # Top 30 características
    
    def _calculate_centrality_measures(self, G: nx.Graph) -> Dict[str, Any]:
        """Calcula medidas de centralidad del grafo"""
        try:
            # Calcular diferentes medidas de centralidad
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            closeness_centrality = nx.closeness_centrality(G)
            
            # Encontrar nodos más centrales
            top_degree = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            top_betweenness = sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            top_closeness = sorted(closeness_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "top_degree_centrality": top_degree,
                "top_betweenness_centrality": top_betweenness,
                "top_closeness_centrality": top_closeness
            }
            
        except Exception as e:
            print(f"⚠️ Error calculando centralidad: {e}")
            return {}
    
    def _detect_communities(self, G: nx.Graph) -> List[Dict]:
        """Detecta comunidades en el grafo"""
        try:
            # Usar algoritmo de detección de comunidades de NetworkX
            communities = list(nx.community.greedy_modularity_communities(G))
            
            community_list = []
            for i, community in enumerate(communities):
                community_list.append({
                    "community_id": i,
                    "size": len(community),
                    "nodes": list(community)
                })
            
            return community_list
            
        except Exception as e:
            print(f"⚠️ Error detectando comunidades: {e}")
            return []
    
    def _analyze_connection_patterns(self, G: nx.Graph) -> Dict[str, Any]:
        """Analiza patrones de conexión en el grafo"""
        try:
            # Calcular densidad del grafo
            density = nx.density(G)
            
            # Calcular clustering promedio
            clustering_coefficient = nx.average_clustering(G)
            
            # Encontrar componentes conectados
            components = list(nx.connected_components(G))
            largest_component_size = max(len(comp) for comp in components) if components else 0
            
            return {
                "density": round(density, 4),
                "average_clustering": round(clustering_coefficient, 4),
                "connected_components": len(components),
                "largest_component_size": largest_component_size
            }
            
        except Exception as e:
            print(f"⚠️ Error analizando patrones: {e}")
            return {}
    
    def _identify_bridge_nodes(self, G: nx.Graph) -> List[str]:
        """Identifica nodos puente en el grafo"""
        try:
            # Calcular betweenness centrality para identificar nodos puente
            betweenness = nx.betweenness_centrality(G)
            
            # Encontrar nodos con alta betweenness centrality
            bridge_nodes = [node for node, centrality in betweenness.items() if centrality > 0.1]
            
            return bridge_nodes[:10]  # Top 10 nodos puente
            
        except Exception as e:
            print(f"⚠️ Error identificando nodos puente: {e}")
            return []
    
    def _analyze_temporal_patterns(self, temporal_groups: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analiza patrones temporales en la creación de nodos"""
        patterns = {}
        
        # Analizar distribución temporal
        group_sizes = [len(nodes) for nodes in temporal_groups.values()]
        if group_sizes:
            patterns["average_group_size"] = round(np.mean(group_sizes), 2)
            patterns["max_group_size"] = max(group_sizes)
            patterns["min_group_size"] = min(group_sizes)
        
        return patterns
    
    def _detect_creation_sequences(self, nodes: List[Dict]) -> List[Dict]:
        """Detecta secuencias de creación de nodos relacionados"""
        # Implementación simplificada - en una versión más avanzada se podría
        # usar análisis de secuencias temporales más sofisticado
        sequences = []
        
        # Agrupar por tipo de nodo y analizar secuencias temporales
        type_groups = defaultdict(list)
        for node in nodes:
            node_type = node.get('type', 'Desconocido')
            created_at = node.get('created_at')
            if created_at:
                type_groups[node_type].append(node)
        
        # Encontrar tipos con secuencias de creación
        for node_type, type_nodes in type_groups.items():
            if len(type_nodes) > 3:  # Solo tipos con suficientes nodos
                sequences.append({
                    "type": node_type,
                    "count": len(type_nodes),
                    "pattern": "sequential_creation"
                })
        
        return sequences
    
    def _analyze_co_occurrence_patterns(self, temporal_groups: Dict[str, List[Dict]]) -> List[Dict]:
        """Analiza patrones de co-ocurrencia temporal"""
        co_occurrence_patterns = []
        
        # Analizar qué tipos de nodos aparecen juntos en el tiempo
        for week, nodes in temporal_groups.items():
            if len(nodes) > 1:
                types_in_week = [node.get('type', 'Desconocido') for node in nodes]
                type_counts = Counter(types_in_week)
                
                # Encontrar tipos que aparecen frecuentemente juntos
                for node_type, count in type_counts.items():
                    if count > 1:
                        co_occurrence_patterns.append({
                            "week": week,
                            "type": node_type,
                            "frequency": count
                        })
        
        return co_occurrence_patterns

def generate_correlation_analysis_report(months: int = 6) -> Dict[str, Any]:
    """
    Función principal para generar un reporte completo de análisis de correlaciones
    """
    try:
        print("🚀 [Correlaciones] Iniciando análisis completo")
        
        detector = CorrelationDetector()
        
        # Realizar análisis semántico
        semantic_data = detector.detect_semantic_correlations()
        
        # Realizar análisis estructural
        structural_data = detector.detect_structural_correlations()
        
        # Realizar análisis temporal
        temporal_data = detector.detect_temporal_correlations(months)
        
        # Generar insights con IA
        insights = detector.generate_correlation_insights(semantic_data, structural_data, temporal_data)
        
        return {
            "success": True,
            "semantic_analysis": semantic_data,
            "structural_analysis": structural_data,
            "temporal_analysis": temporal_data,
            "correlation_insights": insights,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [Correlaciones] Error en análisis completo: {e}")
        return {
            "success": False,
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Ejecutar análisis completo
    report = generate_correlation_analysis_report()
    print("\n" + "="*50)
    print("REPORTE DE ANÁLISIS DE CORRELACIONES")
    print("="*50)
    print(json.dumps(report, indent=2, ensure_ascii=False))

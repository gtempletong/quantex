# quantex/core/autoconocimiento/temporal_analyzer.py

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict, Counter
import numpy as np

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services
from quantex.core import llm_manager

class TemporalAnalyzer:
    """
    Analizador temporal avanzado para el grafo de conocimiento
    que genera visualizaciones de evolución y tendencias temporales.
    """
    
    def __init__(self):
        self.db = db
        self.ai_services = ai_services
        self.llm_manager = llm_manager
    
    def analyze_knowledge_evolution(self, months: int = 12) -> Dict[str, Any]:
        """
        Analiza la evolución del conocimiento a lo largo del tiempo
        """
        try:
            print(f"📅 [Análisis Temporal] Analizando evolución del conocimiento (últimos {months} meses)")
            
            # Calcular fecha límite
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
            
            # Obtener TODOS los nodos con paginación para evitar límite de 1000
            all_nodes = []
            page_size = 1000
            offset = 0
            
            while True:
                response = self.db.supabase.table('nodes').select('*').range(offset, offset + page_size - 1).execute()
                
                if not response.data:
                    break
                    
                all_nodes.extend(response.data)
                print(f"  -> Obtenidos {len(response.data)} nodos (offset: {offset})")
                
                if len(response.data) < page_size:
                    break
                    
                offset += page_size
            
            if not all_nodes:
                return {"error": "No hay nodos en la base de datos"}
            
            print(f"  -> Total nodos en BD: {len(all_nodes)}")
            
            # Filtrar por fecha solo si es necesario
            if months < 24:  # Solo filtrar si es menos de 2 años
                # Filtrar los nodos obtenidos por fecha en memoria
                filtered_nodes = []
                for node in all_nodes:
                    created_at = node.get('created_at')
                    if created_at:
                        try:
                            if 'Z' in created_at:
                                date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                date = datetime.fromisoformat(created_at)
                            
                            if date >= cutoff_date:
                                filtered_nodes.append(node)
                        except:
                            # Si hay error en fecha, incluir el nodo
                            filtered_nodes.append(node)
                    else:
                        # Si no hay fecha, incluir el nodo
                        filtered_nodes.append(node)
                
                nodes = filtered_nodes
                print(f"  -> Nodos en rango temporal ({months} meses): {len(nodes)}")
            else:
                nodes = all_nodes
                print(f"  -> Analizando todos los nodos (sin filtro temporal)")
            
            if not nodes:
                return {"error": "No hay datos suficientes para análisis temporal"}
            
            # Procesar fechas y agrupar por períodos
            daily_counts = defaultdict(int)
            weekly_counts = defaultdict(int)
            monthly_counts = defaultdict(int)
            
            node_types_by_time = defaultdict(lambda: defaultdict(int))
            topics_by_time = defaultdict(lambda: defaultdict(int))
            
            nodes_with_dates = 0
            nodes_without_dates = 0
            
            for node in nodes:
                created_at = node.get('created_at')
                if not created_at:
                    nodes_without_dates += 1
                    # Si no hay fecha, usar fecha actual como fallback
                    date = datetime.now(timezone.utc)
                else:
                    nodes_with_dates += 1
                    try:
                        if 'Z' in created_at:
                            date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            date = datetime.fromisoformat(created_at)
                    except Exception as e:
                        print(f"⚠️ Error procesando fecha {created_at}: {e}")
                        # Usar fecha actual como fallback
                        date = datetime.now(timezone.utc)
                
                # Agrupar por día, semana y mes
                day_key = date.strftime('%Y-%m-%d')
                week_key = date.strftime('%Y-W%U')
                month_key = date.strftime('%Y-%m')
                
                daily_counts[day_key] += 1
                weekly_counts[week_key] += 1
                monthly_counts[month_key] += 1
                
                # Agrupar por tipo de nodo
                node_type = node.get('type', 'Desconocido')
                node_types_by_time[month_key][node_type] += 1
                
                # Extraer temas de las etiquetas
                label = node.get('label', '')
                if label:
                    words = label.lower().split()
                    for word in words:
                        if len(word) > 3 and word.isalpha():
                            topics_by_time[month_key][word] += 1
            
            print(f"  -> Nodos con fechas: {nodes_with_dates}")
            print(f"  -> Nodos sin fechas: {nodes_without_dates}")
            
            # Calcular métricas de crecimiento
            growth_metrics = self._calculate_growth_metrics(daily_counts, weekly_counts, monthly_counts)
            
            # Identificar tendencias por tipo de nodo
            type_trends = self._analyze_type_trends(node_types_by_time)
            
            # Identificar temas emergentes
            emerging_topics = self._identify_emerging_topics(topics_by_time)
            
            return {
                "total_nodes": len(nodes),
                "time_period_months": months,
                "daily_counts": dict(daily_counts),
                "weekly_counts": dict(weekly_counts),
                "monthly_counts": dict(monthly_counts),
                "growth_metrics": growth_metrics,
                "type_trends": type_trends,
                "emerging_topics": emerging_topics,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ [Análisis Temporal] Error: {e}")
            return {"error": str(e)}
    
    def generate_temporal_visualization(self, evolution_data: Dict[str, Any]) -> str:
        """
        Genera visualizaciones temporales del grafo de conocimiento
        """
        try:
            print("📊 [Análisis Temporal] Generando visualizaciones")
            
            # Configurar matplotlib para español
            plt.rcParams['font.family'] = 'DejaVu Sans'
            
            # Crear figura con subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Evolución Temporal del Grafo de Conocimiento', fontsize=16, fontweight='bold')
            
            # 1. Evolución mensual
            monthly_data = evolution_data.get('monthly_counts', {})
            if monthly_data:
                months = sorted(monthly_data.keys())
                counts = [monthly_data[month] for month in months]
                
                ax1.plot(months, counts, marker='o', linewidth=2, markersize=6, color='#007acc')
                ax1.set_title('Crecimiento Mensual de Nodos', fontweight='bold')
                ax1.set_xlabel('Mes')
                ax1.set_ylabel('Número de Nodos')
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis='x', rotation=45)
            
            # 2. Distribución por tipo de nodo
            type_trends = evolution_data.get('type_trends', {})
            if type_trends:
                types = list(type_trends.keys())
                total_counts = [sum(type_trends[t].values()) for t in types]
                
                colors = plt.cm.Set3(np.linspace(0, 1, len(types)))
                ax2.pie(total_counts, labels=types, autopct='%1.1f%%', colors=colors)
                ax2.set_title('Distribución por Tipo de Nodo', fontweight='bold')
            
            # 3. Tendencia semanal
            weekly_data = evolution_data.get('weekly_counts', {})
            if weekly_data:
                weeks = sorted(weekly_data.keys())
                counts = [weekly_data[week] for week in weeks]
                
                ax3.plot(range(len(weeks)), counts, marker='s', linewidth=2, markersize=4, color='#28a745')
                ax3.set_title('Tendencia Semanal', fontweight='bold')
                ax3.set_xlabel('Semana')
                ax3.set_ylabel('Número de Nodos')
                ax3.grid(True, alpha=0.3)
                ax3.set_xticks(range(0, len(weeks), max(1, len(weeks)//10)))
                ax3.set_xticklabels([weeks[i] for i in range(0, len(weeks), max(1, len(weeks)//10))], rotation=45)
            
            # 4. Temas emergentes
            emerging_topics = evolution_data.get('emerging_topics', {})
            if emerging_topics:
                topics = list(emerging_topics.keys())[:10]  # Top 10
                growth_rates = [emerging_topics[topic] for topic in topics]
                
                bars = ax4.barh(topics, growth_rates, color='#fd7e14')
                ax4.set_title('Temas con Mayor Crecimiento', fontweight='bold')
                ax4.set_xlabel('Tasa de Crecimiento (%)')
                ax4.grid(True, alpha=0.3, axis='x')
            
            plt.tight_layout()
            
            # Guardar la imagen
            filename = f"temporal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            # Subir a Supabase Storage
            try:
                with open(filename, 'rb') as f:
                    image_data = f.read()
                
                public_url = self.db.upload_file_to_storage(
                    "report-charts", 
                    f"temporal_analysis/{filename}", 
                    image_data
                )
                
                if public_url:
                    return public_url
                else:
                    return filename  # Fallback al archivo local
                    
            except Exception as e:
                print(f"⚠️ Error subiendo visualización: {e}")
                return filename
            
        except Exception as e:
            print(f"❌ [Análisis Temporal] Error generando visualización: {e}")
            return None
    
    def generate_temporal_insights(self, evolution_data: Dict[str, Any]) -> str:
        """
        Genera insights temporales usando IA
        """
        try:
            print("🧠 [Análisis Temporal] Generando insights con IA")
            
            context = f"""
Análisis de Evolución Temporal del Grafo de Conocimiento:

Datos Generales:
- Total de nodos analizados: {evolution_data.get('total_nodes', 0)}
- Período de análisis: {evolution_data.get('time_period_months', 0)} meses

Métricas de Crecimiento:
- Crecimiento mensual promedio: {evolution_data.get('growth_metrics', {}).get('monthly_growth_rate', 0):.2f}%
- Crecimiento semanal promedio: {evolution_data.get('growth_metrics', {}).get('weekly_growth_rate', 0):.2f}%
- Variabilidad del crecimiento: {evolution_data.get('growth_metrics', {}).get('growth_volatility', 0):.2f}

Tendencias por Tipo de Nodo:
{json.dumps(evolution_data.get('type_trends', {}), indent=2, ensure_ascii=False)}

Temas Emergentes:
{json.dumps(evolution_data.get('emerging_topics', {}), indent=2, ensure_ascii=False)}
"""
            
            prompt = f"""
Eres un analista experto en evolución de conocimiento. Analiza los siguientes datos temporales de un grafo de conocimiento financiero y genera insights sobre la evolución del conocimiento.

{context}

Instrucciones:
1. Identifica patrones de crecimiento y tendencias temporales
2. Analiza qué tipos de conocimiento están creciendo más rápido
3. Identifica temas emergentes y su importancia
4. Proporciona recomendaciones para optimizar el crecimiento del conocimiento
5. Destaca oportunidades de desarrollo futuro
6. Mantén un tono profesional pero accesible
7. Limita la respuesta a máximo 350 palabras

Responde en español y enfócate en insights accionables sobre la evolución temporal.
"""
            
            response = self.llm_manager.generate_completion(
                task_complexity='reasoning',
                system_prompt=prompt,
                user_prompt="Genera insights sobre la evolución temporal del grafo de conocimiento."
            )
            
            return response.get('raw_text', 'No se pudieron generar insights temporales')
            
        except Exception as e:
            print(f"❌ [Análisis Temporal] Error generando insights: {e}")
            return f"Error generando insights temporales: {str(e)}"
    
    def _calculate_growth_metrics(self, daily_counts: Dict, weekly_counts: Dict, monthly_counts: Dict) -> Dict[str, float]:
        """Calcula métricas de crecimiento"""
        metrics = {}
        
        # Crecimiento mensual
        if len(monthly_counts) > 1:
            months = sorted(monthly_counts.keys())
            first_month = monthly_counts[months[0]]
            last_month = monthly_counts[months[-1]]
            if first_month > 0:
                monthly_growth = ((last_month - first_month) / first_month) * 100
                metrics['monthly_growth_rate'] = round(monthly_growth, 2)
        
        # Crecimiento semanal promedio
        if len(weekly_counts) > 1:
            weeks = sorted(weekly_counts.keys())
            weekly_changes = []
            for i in range(1, len(weeks)):
                prev_count = weekly_counts[weeks[i-1]]
                curr_count = weekly_counts[weeks[i]]
                if prev_count > 0:
                    change = ((curr_count - prev_count) / prev_count) * 100
                    weekly_changes.append(change)
            
            if weekly_changes:
                metrics['weekly_growth_rate'] = round(np.mean(weekly_changes), 2)
                metrics['growth_volatility'] = round(np.std(weekly_changes), 2)
        
        return metrics
    
    def _analyze_type_trends(self, type_trends: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
        """Analiza tendencias por tipo de nodo"""
        # Simplificar para mostrar solo los tipos más importantes
        simplified_trends = {}
        
        for month, types in type_trends.items():
            # Tomar solo los 5 tipos más frecuentes
            sorted_types = sorted(types.items(), key=lambda x: x[1], reverse=True)[:5]
            simplified_trends[month] = dict(sorted_types)
        
        return simplified_trends
    
    def _identify_emerging_topics(self, topics_by_time: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        """Identifica temas emergentes basado en crecimiento"""
        if len(topics_by_time) < 2:
            return {}
        
        # Calcular crecimiento para cada tema
        topic_growth = {}
        
        for topic in set().union(*topics_by_time.values()):
            counts = []
            for month in sorted(topics_by_time.keys()):
                counts.append(topics_by_time[month].get(topic, 0))
            
            if len(counts) > 1 and counts[0] > 0:
                growth_rate = ((counts[-1] - counts[0]) / counts[0]) * 100
                if growth_rate > 10:  # Solo temas con crecimiento significativo
                    topic_growth[topic] = round(growth_rate, 2)
        
        # Retornar los 10 temas con mayor crecimiento
        return dict(sorted(topic_growth.items(), key=lambda x: x[1], reverse=True)[:10])

def generate_temporal_analysis_report(months: int = 12) -> Dict[str, Any]:
    """
    Función principal para generar un reporte completo de análisis temporal
    """
    try:
        print("🚀 [Análisis Temporal] Iniciando análisis completo")
        
        analyzer = TemporalAnalyzer()
        
        # Realizar análisis de evolución
        evolution_data = analyzer.analyze_knowledge_evolution(months)
        
        if evolution_data.get('error'):
            return evolution_data
        
        # Generar visualización
        visualization_url = analyzer.generate_temporal_visualization(evolution_data)
        
        # Generar insights con IA
        insights = analyzer.generate_temporal_insights(evolution_data)
        
        return {
            "success": True,
            "evolution_data": evolution_data,
            "visualization_url": visualization_url,
            "temporal_insights": insights,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [Análisis Temporal] Error en análisis completo: {e}")
        return {
            "success": False,
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Ejecutar análisis completo
    report = generate_temporal_analysis_report()
    print("\n" + "="*50)
    print("REPORTE DE ANÁLISIS TEMPORAL")
    print("="*50)
    print(json.dumps(report, indent=2, ensure_ascii=False))

# quantex/pipelines/pinecone_visualizer.py (Versión Final y Autocontenida)

import os
import sys
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db

def get_subgraph_data_in_python(topic: str, limit: int = 30) -> tuple[list, list]:
    """
    Obtiene los nodos y conexiones de un subgrafo directamente con consultas
    en Python, sin depender de una función RPC en la base de datos.
    """
    print(f"  -> 🐍 Ejecutando lógica de subgrafo en Python para '{topic}'...")
    
    # 1. Encontrar el nodo inicial del tópico
    topic_node_res = db.supabase.table('nodes').select('id, type, label').eq('label', topic).limit(1).maybe_single().execute()
    if not topic_node_res.data:
        return [], []
    
    start_node = topic_node_res.data
    topic_node_id = start_node['id']
    
    # 2. Encontrar todas las conexiones directas con el nodo del tópico
    edges_res = db.supabase.table('edges').select('*') \
        .or_(f"source_id.eq.{topic_node_id},target_id.eq.{topic_node_id}") \
        .limit(limit) \
        .execute()
    
    if not edges_res.data:
        return [start_node], []
        
    edges = edges_res.data
    
    # 3. Recolectar todos los IDs de los nodos conectados
    neighbor_ids = set([topic_node_id])
    for edge in edges:
        neighbor_ids.add(edge['source_id'])
        neighbor_ids.add(edge['target_id'])
        
    # 4. Obtener la información de todos los nodos del subgrafo
    nodes_res = db.supabase.table('nodes').select('id, type, label').in_('id', list(neighbor_ids)).execute()
    
    return nodes_res.data, edges

def visualize_topic_subgraph(topic: str, limit: int = 30):
    """
    Genera una visualización del "vecindario" del grafo para un tópico específico.
    """
    print(f"--- 📊 Iniciando Visualizador de Subgrafo para: '{topic}' ---")
    try:
        nodes, edges = get_subgraph_data_in_python(topic, limit)

        if not nodes:
            print(f"  -> 🟡 No se encontraron nodos o conexiones para '{topic}'.")
            return

        G = nx.Graph()
        for node in nodes: G.add_node(node['id'], type=node.get('type'), label=node.get('label'))
        for edge in edges: G.add_edge(edge['source_id'], edge['target_id'])

        print(f"  -> ✅ Grafo construido con {len(nodes)} nodos y {len(edges)} conexiones.")
        plt.style.use('dark_background')
        plt.figure(figsize=(28, 28))
        pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
        color_map = {'Tópico Principal': '#e74c3c', 'Aprendizaje Clave': '#f1c40f', 'Documento': '#3498db', 'Entidad': '#2ecc71', 'Briefing': '#9b59b6'}
        node_colors = [color_map.get(G.nodes[n].get('type'), '#7f8c8d') for n in G.nodes()]
        node_sizes = [5000 if G.nodes[n].get('type') == 'Tópico Principal' else 1500 for n in G.nodes()]
        labels = {n: G.nodes[n].get('label', '')[:30] for n in G.nodes()}

        nx.draw_networkx(G, pos, labels=labels, node_color=node_colors, node_size=node_sizes, font_size=9, font_color='white', edge_color='#555555', width=1.5, alpha=0.9)
        plt.title(f"Grafo de Conocimiento para '{topic}'", size=24)
        output_filename = f"grafo_conocimiento_{topic.lower()}.png"
        plt.savefig(output_filename, format="PNG", dpi=150, bbox_inches='tight')
        plt.close()
        print(f"--- ✅ Visualización de subgrafo guardada como '{output_filename}' ---")
    except Exception as e:
        print(f"❌ Error durante la visualización del subgrafo: {e}")
        import traceback
        traceback.print_exc()

def get_all_data_paginated(table_name: str) -> list:
    all_data, page, page_size = [], 0, 1000
    print(f"    -> Descargando datos de la tabla '{table_name}'...")
    while True:
        response = db.supabase.table(table_name).select('*').range(page * page_size, (page + 1) * page_size - 1).execute()
        if not response.data: break
        all_data.extend(response.data)
        page += 1
    print(f"       ✅ Se descargaron {len(all_data)} filas.")
    return all_data

def visualize_full_knowledge_graph():
    """
    Genera una visualización del grafo de conocimiento COMPLETO.
    """
    print(f"--- 🗺️ Iniciando Visualizador del Grafo Completo ---")
    try:
        nodes_data = get_all_data_paginated('nodes')
        edges_data = get_all_data_paginated('edges')
        if not nodes_data:
            print("  -> 🟡 No se encontraron nodos."); return

        G = nx.Graph()
        for node in nodes_data: G.add_node(node['id'], type=node.get('type', 'desconocido'), label=node.get('label', ''))
        if edges_data:
            for edge in edges_data:
                if edge['source_id'] in G and edge['target_id'] in G:
                    G.add_edge(edge['source_id'], edge['target_id'])

        print(f"  -> ✅ Grafo construido con {G.number_of_nodes()} nodos y {G.number_of_edges()} conexiones.")
        plt.style.use('dark_background')
        plt.figure(figsize=(40, 40))
        pos = nx.spring_layout(G, k=0.1, iterations=50, seed=42)
        color_map = {'Tópico Principal': '#e74c3c', 'Aprendizaje Clave': '#f1c40f', 'Documento': '#3498db', 'Entidad': '#2ecc71', 'Briefing': '#9b59b6'}
        node_colors = [color_map.get(G.nodes[n]['type'], '#7f8c8d') for n in G.nodes()]
        node_sizes = [1000 if G.nodes[n]['type'] == 'Tópico Principal' else 200 for n in G.nodes()]
        labels = {n: G.nodes[n]['label'][:25] for n in G.nodes() if G.degree(n) > 1}

        nx.draw_networkx(G, pos, labels=labels, node_color=node_colors, node_size=node_sizes, font_size=8, font_color='white', edge_color='#555555', alpha=0.8, width=0.5)
        plt.title("Grafo de Conocimiento Completo de Quantex", size=30)
        output_filename = "grafo_conocimiento_completo.png"
        plt.savefig(output_filename, format="PNG", dpi=200, bbox_inches='tight')
        plt.close()
        print(f"--- ✅ Visualización completa guardada como '{output_filename}' ---")
    except Exception as e:
        print(f"❌ Ocurrió un error durante la visualización completa: {e}")
        import traceback
        traceback.print_exc()

# --- Bloque de Ejecución (PUEDES ELEGIR QUÉ VISTA GENERAR) ---
if __name__ == '__main__':
    if not db.supabase:
        print("❌ Error: No se pudo conectar a Supabase.")
    else:
        # --- CONFIGURACIÓN ---
        MODO = "subgrafo"  # Cambia a "completo" para ver el grafo entero
        TOPICO_PARA_SUBGRAFO = "Cobre"
        # ---------------------
        
        if MODO == "subgrafo":
            visualize_topic_subgraph(topic=TOPICO_PARA_SUBGRAFO)
        elif MODO == "completo":
            visualize_full_knowledge_graph()
        else:
            print(f"❌ Modo '{MODO}' no reconocido. Elige 'subgrafo' o 'completo'.")
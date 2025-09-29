#!/usr/bin/env python3
"""
Script para reprocesar nodos del 21 de septiembre 2025
Agrega timestamps a la metadata de Pinecone para nodos existentes
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services

# Cargar variables de entorno
load_dotenv()

def reprocess_nodes_sep21():
    """Reprocesa todos los nodos del 21 de sep 2025"""
    print('🔄 REPROCESANDO NODOS DEL 21 DE SEPTIEMBRE 2025')
    print('=' * 60)
    
    try:
        # Inicializar servicios
        ai_services.initialize()
        print('✅ Servicios de AI inicializados')
        
        # Buscar nodos del 21 de sep 2025
        print('📊 Buscando nodos del 21 de sep 2025...')
        response = db.supabase.table('nodes').select('*').gte('created_at', '2025-09-21T00:00:00Z').lt('created_at', '2025-09-22T00:00:00Z').execute()
        
        nodes = response.data
        print(f'✅ Encontrados {len(nodes)} nodos del 21 de sep')
        
        if not nodes:
            print('❌ No se encontraron nodos para reprocesar')
            return
        
        # Procesar cada nodo
        processed = 0
        errors = 0
        
        for i, node in enumerate(nodes, 1):
            try:
                node_id = node['id']
                node_type = node.get('type', 'Desconocido')
                properties = node.get('properties') or {}
                
                print(f'\n{i}. Procesando nodo {node_id[:12]}... (Tipo: {node_type})')
                
                # Solo procesar nodos de tipo "Documento"
                if node_type != 'Documento':
                    print(f'   ⏭️ Saltando nodo de tipo {node_type}')
                    continue
                
                # Obtener contenido del nodo
                content = node.get('content', '')
                if not content:
                    print(f'   ⚠️ Nodo sin contenido, saltando')
                    continue
                
                # Crear metadata actualizada para Pinecone
                created_at = node.get('created_at', '')
                timestamp = properties.get('timestamp', created_at)
                
                # Convertir timestamp a formato correcto si es necesario
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            # Si es string ISO, convertir a timestamp Unix
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            timestamp_unix = int(dt.timestamp())
                        else:
                            timestamp_unix = timestamp
                    except:
                        # Si falla, usar created_at
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        timestamp_unix = int(dt.timestamp())
                else:
                    # Si no hay timestamp, usar created_at
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timestamp_unix = int(dt.timestamp())
                
                # Metadata actualizada para Pinecone
                updated_metadata = {
                    "source": properties.get('source', ''),
                    "source_type": properties.get('source_type', ''),
                    "topic": properties.get('topic', ''),
                    "original_url": properties.get('original_url', ''),
                    "categories": properties.get('categories', []),
                    "key_entities": properties.get('key_entities', []),
                    "text_snippet": content[:500],
                    "timestamp": timestamp_unix,  # Timestamp Unix para filtros
                    "created_at": created_at,     # Timestamp ISO para referencia
                    "node_type": node_type
                }
                
                # Generar embedding si no existe
                vector = ai_services.embedding_model.encode(content).tolist()
                
                # Upsert en Pinecone con metadata actualizada
                ai_services.pinecone_index.upsert(vectors=[{
                    "id": node_id,
                    "values": vector,
                    "metadata": updated_metadata
                }])
                
                print(f'   ✅ Nodo reprocesado exitosamente')
                print(f'   📅 Timestamp: {timestamp_unix}')
                print(f'   📊 Fuente: {properties.get("source", "N/A")}')
                print(f'   🏷️ Tópico: {properties.get("topic", "N/A")}')
                
                processed += 1
                
            except Exception as e:
                print(f'   ❌ Error procesando nodo: {e}')
                errors += 1
                continue
        
        print(f'\n📊 RESUMEN:')
        print(f'   ✅ Nodos procesados: {processed}')
        print(f'   ❌ Errores: {errors}')
        print(f'   📈 Total nodos: {len(nodes)}')
        
        if processed > 0:
            print(f'\n🎉 ¡Reprocesamiento completado!')
            print(f'   Los nodos ahora tienen timestamps en Pinecone')
            print(f'   Los filtros temporales deberían funcionar')
        
    except Exception as e:
        print(f'❌ Error crítico: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reprocess_nodes_sep21()


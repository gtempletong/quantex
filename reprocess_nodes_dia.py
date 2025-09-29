#!/usr/bin/env python3
"""
Script para reprocesar nodos de un día específico
Basado en el script exitoso reprocess_nodes_sep21.py
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from quantex.core import database_manager as db
from quantex.core.ai_services import ai_services

# Cargar variables de entorno
load_dotenv()

def get_date_from_user():
    """Obtiene la fecha del usuario"""
    print("📅 CONFIGURACIÓN DE FECHA")
    print("=" * 50)
    
    while True:
        try:
            fecha_str = input("Ingresa la fecha a procesar (formato: YYYY-MM-DD): ").strip()
            
            if not fecha_str:
                print("❌ Debes ingresar una fecha.")
                continue
                
            # Validar formato
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            
            # Confirmar fecha
            print(f"\n📅 Fecha seleccionada: {fecha.strftime('%A, %d de %B de %Y')}")
            confirmar = input("¿Es correcta esta fecha? (s/N): ").strip().lower()
            
            if confirmar in ['s', 'si', 'sí', 'y', 'yes']:
                return fecha
            else:
                print("🔄 Intenta de nuevo...")
                
        except ValueError:
            print("❌ Formato inválido. Usa YYYY-MM-DD (ej: 2025-09-20)")
        except KeyboardInterrupt:
            print("\n👋 Operación cancelada.")
            exit(0)

def reprocess_nodes_by_date(fecha):
    """Reprocesa todos los nodos de una fecha específica"""
    print(f'\n🔄 REPROCESANDO NODOS DEL {fecha.strftime("%d de %B de %Y")}')
    print('=' * 60)
    
    try:
        # Inicializar servicios
        ai_services.initialize()
        print('✅ Servicios de AI inicializados')
        
        # Calcular rango de fechas para el día completo
        inicio_dia = fecha.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        fin_dia = inicio_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        inicio_iso = inicio_dia.isoformat()
        fin_iso = fin_dia.isoformat()
        
        print(f'📅 Rango: {inicio_iso} a {fin_iso}')
        
        # Buscar nodos del día especificado
        print(f'📊 Buscando nodos del {fecha.strftime("%Y-%m-%d")}...')
        response = db.supabase.table('nodes').select('*').gte('created_at', inicio_iso).lte('created_at', fin_iso).execute()
        
        nodes = response.data
        print(f'✅ Encontrados {len(nodes)} nodos del {fecha.strftime("%Y-%m-%d")}')
        
        if not nodes:
            print('❌ No se encontraron nodos para reprocesar')
            return
        
        # Procesar cada nodo
        processed = 0
        errors = 0
        skipped = 0
        
        for i, node in enumerate(nodes, 1):
            try:
                node_id = node['id']
                node_type = node.get('type', 'Desconocido')
                properties = node.get('properties') or {}
                
                print(f'\n{i}. Procesando nodo {node_id[:12]}... (Tipo: {node_type})')
                
                # Solo procesar nodos de tipo "Documento"
                if node_type != 'Documento':
                    print(f'   ⏭️ Saltando nodo de tipo {node_type}')
                    skipped += 1
                    continue
                
                # Obtener contenido del nodo
                content = node.get('content', '')
                if not content:
                    print(f'   ⚠️ Nodo sin contenido, saltando')
                    skipped += 1
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
        print(f'   ⏭️ Nodos saltados: {skipped}')
        print(f'   ❌ Errores: {errors}')
        print(f'   📈 Total nodos: {len(nodes)}')
        
        if processed > 0:
            print(f'\n🎉 ¡Reprocesamiento completado!')
            print(f'   Los nodos del {fecha.strftime("%Y-%m-%d")} ahora tienen timestamps en Pinecone')
            print(f'   Los filtros temporales deberían funcionar para esta fecha')
        
    except Exception as e:
        print(f'❌ Error crítico: {e}')
        import traceback
        traceback.print_exc()

def main():
    """Función principal"""
    print("🚀 REPROCESADOR DE NODOS POR DÍA")
    print("=" * 50)
    print("Este script reprocesa nodos de un día específico para asegurar metadatos completos en Pinecone")
    print()
    
    try:
        # Obtener fecha del usuario
        fecha = get_date_from_user()
        
        # Reprocesar nodos
        reprocess_nodes_by_date(fecha)
        
        print("\n🎉 Proceso completado.")
        
    except KeyboardInterrupt:
        print("\n👋 Operación cancelada por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

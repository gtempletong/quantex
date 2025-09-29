import os
import sys
import argparse
import pprint
from datetime import datetime, timedelta, timezone

# --- Configuración de Rutas para poder importar desde Quantex ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Reutilizamos el gestor de servicios de IA que ya tiene la conexión a Pinecone ---
from quantex.core.ai_services import ai_services

def main():
    parser = argparse.ArgumentParser(description="Explorador de vectores recientes en Pinecone.")
    parser.add_argument("--horas", type=int, default=1, help="El número de horas hacia atrás para buscar.")
    args = parser.parse_args()

    print(f"--- 🌲 Buscando vectores creados en las últimas {args.horas} hora(s) en Pinecone ---")

    # 1. Inicializamos los servicios para asegurarnos de tener conexión
    ai_services.initialize()
    if not ai_services.is_initialized or not ai_services.pinecone_index:
        print("❌ No se pudo inicializar la conexión a Pinecone.")
        return

    # 2. Creamos el filtro de tiempo
    # Pinecone usa timestamps "epoch" (segundos desde 1970)
    n_hours_ago = datetime.now(timezone.utc) - timedelta(hours=args.horas)
    timestamp_n_hours_ago = int(n_hours_ago.timestamp())

    # El filtro le dice a Pinecone: "dame todo donde 'created_at' sea mayor o igual que X"
    time_filter = {"created_at": {"$gte": timestamp_n_hours_ago}}
    print(f"Filtro de metadatos aplicado: {time_filter}")

    try:
        # 3. Hacemos una "consulta vacía" para obtener todos los resultados que coincidan con el filtro
        # Pinecone requiere un vector para buscar, así que usamos un vector de ceros como "comodín".
        # Pedimos un top_k alto para asegurarnos de traer todos los resultados recientes.
        dummy_vector = [0.0] * 384 # La dimensión del modelo 'all-MiniLM-L6-v2' es 384
        
        query_response = ai_services.pinecone_index.query(
            vector=dummy_vector,
            filter=time_filter,
            top_k=100, # Trae hasta 100 resultados
            include_metadata=True # ¡Muy importante!
        )

        # 4. Imprimimos los resultados
        if query_response.get('matches'):
            print(f"\n✅ Se encontraron {len(query_response['matches'])} vectores:")
            for match in query_response['matches']:
                # El 'score' no es relevante en esta búsqueda, solo los metadatos
                metadata = match.get('metadata', {})
                # Convertimos el timestamp de vuelta a una fecha legible
                metadata['created_at_readable'] = datetime.fromtimestamp(metadata.get('created_at', 0)).isoformat()
                pprint.pprint(metadata)
                print("-" * 20)
        else:
            print("\n🟡 No se encontraron vectores que coincidan con el filtro de tiempo.")

    except Exception as e:
        print(f"\n❌ Ocurrió un error al consultar Pinecone: {e}")

if __name__ == '__main__':
    main()
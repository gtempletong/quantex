# quantex/core/ai_services.py (versión refactorizada)
import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

class AIServiceManager:
    """
    Una clase para gestionar y centralizar el acceso a los modelos de IA
    y a la conexión con Pinecone.
    """
    def __init__(self):
        print("  -> [AI] Creando instancia del Gestor de Servicios de IA...")
        self.embedding_model = None
        self.pinecone_index = None
        self.is_initialized = False

    def initialize(self):
        """Carga los modelos y establece la conexión con Pinecone."""
        if self.is_initialized:
            print("    -> 🟡 Servicios de IA ya estaban inicializados.")
            return

        # Permitir desactivar embeddings globalmente para acelerar el sistema
        disable_embeddings = os.environ.get("QUANTEX_DISABLE_EMBEDDINGS", "").lower() in ["1", "true", "yes"]
        if disable_embeddings:
            print("    -> Embeddings desactivados por QUANTEX_DISABLE_EMBEDDINGS. Usando modelo nulo.")
            class NullEmbeddingModel:
                def encode(self, inputs):
                    # Devuelve vectores cero (dimensión 384 como MiniLM-L6-v2)
                    import numpy as np
                    def zeros_vec():
                        return np.zeros(384, dtype=float).tolist()
                    if isinstance(inputs, list):
                        return [zeros_vec() for _ in inputs]
                    return zeros_vec()
            self.embedding_model = NullEmbeddingModel()
            self.pinecone_index = None
            self.is_initialized = True
            return

        print("    -> 🧠 Cargando modelo de embeddings (all-MiniLM-L6-v2)...")
        try:
            # Usamos un modelo eficiente y popular para embeddings semánticos
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            print("    -> 🌲 Conectando con Pinecone...")
            pinecone_api_key = os.environ.get("PINECONE_API_KEY")
            
            if not pinecone_api_key:
                raise ValueError("La variable de entorno PINECONE_API_KEY no está configurada.")
            
            pc = Pinecone(api_key=pinecone_api_key)
            index_name = 'quantex-knowledge-base' # Puedes cambiar esto si tu índice se llama diferente
            self.pinecone_index = pc.Index(index_name)
            
            self.is_initialized = True
            print("    -> ✅ Modelo de embeddings y Pinecone listos.")
        except Exception as e:
            print(f"    -> ❌ Error crítico durante la inicialización de servicios de IA: {e}")
            self.is_initialized = False

# --- Instancia Única y Global ---
# Creamos una sola instancia que toda la aplicación importará y usará.
# Esta es nuestra única "fuente de la verdad".
ai_services = AIServiceManager()
# quantex/pipelines/document_pipeline.py (Versión final con clasificación desde Supabase)

import os
import sys
import uuid
import shutil
from dotenv import load_dotenv

# --- INICIALIZACIÓN Y RUTAS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from quantex.pipelines import processing_utils as proc
from quantex.core import database_manager as db
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

# ... (Las funciones _chunk_text y run_pipeline no cambian) ...
def _chunk_text(text: str) -> list[str]:
    # ...
def run_pipeline(source_url: str, doc_type: str, embedding_model, pinecone_index, document_content: str = None):
    # ...

# --- DISPARADOR DE INGESTA MANUAL CON CONFIGURACIÓN DINÁMICA ---
if __name__ == '__main__':
    print("--- ⚙️  Ejecutando pipeline en modo de INGESTA DINÁMICA DE CARPETA ---")

    SOURCE_FOLDER = os.path.join(PROJECT_ROOT, 'documentos_manuales')
    PROCESSED_FOLDER = os.path.join(PROJECT_ROOT, 'documentos_procesados')
    os.makedirs(SOURCE_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)

    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        pinecone_index = pc.Index("quantex-knowledge-base")

        # --- INICIO DE LA MODIFICACIÓN: LEER CONFIGURACIÓN DESDE SUPABASE ---
        print("--- 📚 Obteniendo configuración de tipos de documento desde Supabase... ---")
        targets_response = db.supabase.table('scraping_targets').select('target_name, doc_type').execute()
        doc_type_map = {item['target_name']: item['doc_type'] for item in targets_response.data}
        print(f"--- ✅ {len(doc_type_map)} configuraciones cargadas. ---")
        # --- FIN DE LA MODIFICACIÓN ---

    except Exception as e:
        print(f"❌ Error al inicializar o cargar configuración: {e}")
        sys.exit(1)

    files_to_process = [f for f in os.listdir(SOURCE_FOLDER) if f.lower().endswith('.pdf')]
    
    if not files_to_process:
        print("--- No se encontraron nuevos PDFs para procesar. ---")
    else:
        print(f"--- Se encontraron {len(files_to_process)} archivo(s) para procesar. ---")

    for file_name in files_to_process:
        print(f"\n--- 📄 Procesando: {file_name} ---")
        
        # --- LÓGICA DE CLASIFICACIÓN DINÁMICA ---
        file_name_without_ext = os.path.splitext(file_name)[0]
        TIPO_DE_DOCUMENTO = doc_type_map.get(file_name_without_ext, "documento_desconocido")
        
        if TIPO_DE_DOCUMENTO == "documento_desconocido":
            print(f"  -> ⚠️  Advertencia: No se encontró una configuración para '{file_name_without_ext}' en la tabla 'scraping_targets'. Se usará 'documento_desconocido'.")
        else:
            print(f"  -> ℹ️  Clasificado como: '{TIPO_DE_DOCUMENTO}'")
        # ----------------------------------------
        
        file_path = os.path.join(SOURCE_FOLDER, file_name)
        texto_del_documento = proc.extract_text_from_pdf(file_path)
        
        if texto_del_documento:
            run_pipeline(
                source_url=f"local_file:{file_name}",
                doc_type=TIPO_DE_DOCUMENTO,
                embedding_model=embedding_model,
                pinecone_index=pinecone_index,
                document_content=texto_del_documento
            )
            shutil.move(file_path, os.path.join(PROCESSED_FOLDER, file_name))
            print(f"--- ✅ Archivo '{file_name}' procesado y movido. ---")
        else:
            print(f"--- ❌ No se pudo extraer texto de '{file_name}'. Se omite. ---")
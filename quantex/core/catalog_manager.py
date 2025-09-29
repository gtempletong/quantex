# En quantex/core/catalog_manager.py

import os
import sys

# --- Importación de Herramientas de Quantex ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.flow_registry import FLOW_REGISTRY

def build_dynamic_catalog():
    """
    Construye un catálogo híbrido y conciso de las capacidades del sistema.
    """
    print("🧠 [Catalog Manager] Construyendo catálogo de conciencia (híbrido)...")
    catalog = {"reports": [], "tools": []}
    
    try:
        # Parte 1: Obtener los informes de forma resumida desde la base de datos
        response = db.supabase.table('report_definitions').select('report_keyword, display_title, is_active').eq('is_active', True).execute()
        if response.data:
            catalog["reports"] = [
                {"keyword": r["report_keyword"], "title": r["display_title"]}
                for r in response.data
            ]

        # Parte 2: Obtener las herramientas y sus descripciones desde el código
        if FLOW_REGISTRY:
            catalog["tools"] = [
                {
                    "flow_type": flow_name,
                    "keywords": config.get("keywords", []),
                    "description": config.get("description", "")
                }
                for flow_name, config in FLOW_REGISTRY.items()
            ]

        print("  -> ✅ Catálogo de conciencia híbrido construido exitosamente.")
        return catalog
        
    except Exception as e:
        print(f"  -> ⚠️ Error construyendo el catálogo dinámico: {e}")
        return catalog
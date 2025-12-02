#!/usr/bin/env python3
"""
Script para regenerar el PDF de un artifact existente.

Puede recibir el artifact_id de dos formas:
1. Por argumento de línea de comandos: python regenerate_pdf.py <artifact_id>
2. Por stdin como JSON: {"artifact_id": "..."}
"""

import sys
import os
import json

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from quantex.core import database_manager as db

def main():
    artifact_id = None
    
    # Intentar leer de stdin primero (para uso desde API)
    try:
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            data = json.loads(stdin_data)
            artifact_id = data.get('artifact_id')
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Si no hay stdin, intentar argumento de línea de comandos
    if not artifact_id and len(sys.argv) >= 2:
        artifact_id = sys.argv[1].strip()
    
    if not artifact_id:
        print("❌ Error: Debes proporcionar el ID del artifact")
        print("\nUso:")
        print(f"  python {sys.argv[0]} <artifact_id>")
        print("  O enviar JSON por stdin: {{\"artifact_id\": \"...\"}}")
        sys.exit(1)
    
    print(f"🔄 Regenerando PDF para artifact: {artifact_id}\n")
    
    result = db.regenerate_pdf_for_artifact(artifact_id)
    
    if result:
        # Imprimir resultado como JSON para que el endpoint pueda parsearlo
        output = {
            "ok": True,
            "artifact_id": artifact_id,
            "pdf_url": result.get('pdf_url'),
            "message": "PDF regenerado exitosamente"
        }
        print(json.dumps(output))
        sys.exit(0)
    else:
        output = {
            "ok": False,
            "artifact_id": artifact_id,
            "error": "No se pudo regenerar el PDF"
        }
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()


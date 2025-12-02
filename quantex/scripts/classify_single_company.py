#!/usr/bin/env python3
"""
Script para clasificar una sola empresa desde el dashboard CRM
Recibe company_id por stdin y ejecuta la clasificación completa
"""

import os
import sys
import json
from pathlib import Path

# Agregar el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importar el sistema de clasificación
from verticals.quantex_agora.complete_classification_system import CompleteClassificationSystem


def classify_company(company_id: str) -> dict:
    """
    Clasificar una empresa específica por su ID
    
    Args:
        company_id: UUID de la empresa en apollo_companies
        
    Returns:
        dict con resultado de la clasificación
    """
    try:
        # Inicializar sistema
        system = CompleteClassificationSystem()
        
        # Obtener empresa por ID
        result = system.supabase.table('apollo_companies').select('*').eq('id', company_id).execute()
        
        if not result.data:
            return {
                "ok": False,
                "error": f"No se encontró empresa con ID: {company_id}"
            }
        
        company = result.data[0]
        
        # PASO 1: Análisis con Perplexity
        perplexity_result = system.analyze_company_with_perplexity(company)
        
        if 'error' in perplexity_result:
            return {
                "ok": False,
                "error": "Error en análisis de Perplexity",
                "details": perplexity_result.get('error')
            }
        
        # PASO 2: Análisis con IA (Claude)
        ai_result = system.analyze_company_with_ai(perplexity_result)
        
        if 'error' in ai_result:
            return {
                "ok": False,
                "error": "Error en análisis de IA",
                "details": ai_result.get('error')
            }
        
        # Guardar análisis de empresa
        system.supabase.table('apollo_companies').update({
            'perplexity_analysis': perplexity_result,
            'ai_score': ai_result['ai_score'],
            'ai_classification': ai_result['ai_classification'],
            'ai_analysis_report': ai_result.get('ai_analysis_report')
        }).eq('id', company['id']).execute()
        
        # PASO 3: Clasificar personas de esta empresa
        persons_result = system.classify_persons_for_company(
            company,
            ai_result['ai_score'],
            ai_result['ai_classification']
        )
        
        return {
            "ok": True,
            "company_name": company['name'],
            "company_score": ai_result['ai_score'],
            "company_classification": ai_result['ai_classification'],
            "persons_found": persons_result['persons_found'],
            "persons_updated": persons_result['persons_updated']
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Leer datos desde stdin
    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)
        company_id = data.get('company_id')
        
        if not company_id:
            print(json.dumps({"ok": False, "error": "company_id es requerido"}))
            sys.exit(1)
        
        # Ejecutar clasificación
        result = classify_company(company_id)
        
        # Retornar resultado como JSON
        print(json.dumps(result))
        
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": f"JSON inválido: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)














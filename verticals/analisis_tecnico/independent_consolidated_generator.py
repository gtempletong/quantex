# quantex/verticals/analisis_tecnico/independent_consolidated_generator.py

import os
import sys
from datetime import datetime, timezone
from flask import jsonify

# --- Importaciones de Servicios Centrales ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from .consolidated_report_generator import (
    get_today_committee_artifacts,
    extract_committee_data,
    generate_consolidated_html
)

def run_independent_consolidated_generator(parameters: dict) -> dict:
    """
    Generador independiente de reportes consolidados.
    Lee artifacts de Supabase y genera el consolidado sin re-ejecutar análisis técnico.
    """
    print("🚀 [Generador Independiente] Iniciando generación de consolidado...")
    
    try:
        report_keyword = parameters.get("report_keyword", "comite_tecnico_mercado")
        
        # 1. Obtener artifacts de hoy
        print(f"  -> 📊 [Independiente] Buscando artifacts para '{report_keyword}'...")
        artifacts = get_today_committee_artifacts(report_keyword)
        
        if not artifacts:
            return {
                "success": False,
                "error": f"No se encontraron artifacts de hoy para '{report_keyword}'",
                "response_blocks": [
                    {"type": "markdown", "content": f"⚠️ No hay datos base disponibles para generar consolidado de '{report_keyword}'", "display_target": "chat"}
                ]
            }
        
        print(f"  -> ✅ [Independiente] Encontrados {len(artifacts)} artifacts")
        
        # 2. Extraer datos del comité
        committee_data = extract_committee_data(artifacts)
        
        if not committee_data:
            return {
                "success": False,
                "error": "No se pudieron extraer datos del comité",
                "response_blocks": [
                    {"type": "markdown", "content": "⚠️ Error extrayendo datos del comité", "display_target": "chat"}
                ]
            }
        
        print(f"  -> ✅ [Independiente] Datos extraídos para {len(committee_data)} tickers")
        
        # 3. Generar HTML consolidado
        html_report = generate_consolidated_html(committee_data, report_keyword)
        
        # 4. Guardar artifact consolidado
        consolidated_artifact = db.insert_generated_artifact(
            report_keyword=report_keyword,
            artifact_content=html_report,
            artifact_type=f"report_{report_keyword}_consolidated",
            results_packet={
                "consolidated_data": committee_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_tickers": len(committee_data),
                "source_artifacts": [a.get('id') for a in artifacts]
            },
            ticker="CONSOLIDATED"
        )
        
        print(f"  -> ✅ [Independiente] Reporte consolidado generado exitosamente")
        
        # 5. Preparar respuesta
        tickers_list = [data['ticker'] for data in committee_data]
        
        response_blocks = [
            {
                "type": "markdown", 
                "content": f"### ✅ Reporte Consolidado Generado\n\n**Tickers procesados:** {', '.join(tickers_list)}\n**Total:** {len(committee_data)} tickers\n**Artifact ID:** {consolidated_artifact.get('id') if consolidated_artifact else 'N/A'}", 
                "display_target": "chat"
            },
            {
                "type": "html", 
                "content": html_report, 
                "display_target": "panel"
            }
        ]
        
        return {
            "success": True,
            "response_blocks": response_blocks,
            "artifact_id": consolidated_artifact.get('id') if consolidated_artifact else None,
            "total_tickers": len(committee_data),
            "tickers": tickers_list
        }
        
    except Exception as e:
        print(f"❌ [Generador Independiente] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "response_blocks": [
                {"type": "markdown", "content": f"❌ Error generando consolidado: {e}", "display_target": "chat"}
            ]
        }

def get_available_consolidated_reports() -> dict:
    """
    Obtiene lista de reportes consolidados disponibles.
    """
    try:
        # Buscar artifacts consolidados de hoy
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        response = db.supabase.table('generated_artifacts').select('*').like('artifact_type', '%consolidated').gte('created_at', today_start.isoformat()).lte('created_at', today_end.isoformat()).order('created_at', desc=True).execute()
        
        if not response.data:
            return {"available_reports": []}
        
        reports = []
        for artifact in response.data:
            reports.append({
                "report_keyword": artifact.get('report_keyword'),
                "artifact_id": artifact.get('id'),
                "created_at": artifact.get('created_at'),
                "ticker": artifact.get('ticker', 'CONSOLIDATED')
            })
        
        return {"available_reports": reports}
        
    except Exception as e:
        print(f"❌ [Independiente] Error obteniendo reportes disponibles: {e}")
        return {"available_reports": [], "error": str(e)}

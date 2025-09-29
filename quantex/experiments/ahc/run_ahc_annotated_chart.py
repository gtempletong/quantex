import os
import sys
import re
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from quantex.experiments.ahc.run_ahc_mvp import generate_log_chart, fetch_ohlcv, CUTOFF_DATE_STR
from quantex.experiments.ahc.run_ahc_narrative import find_major_inflections


def parse_narrative_dates(narrative_file: str) -> list:
    """Extrae las fechas de los eventos del archivo de narrativa markdown."""
    inflection_points = []
    
    try:
        with open(narrative_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar patrones como "1. **2005-12-30**" o "32. **2024-04-11**"
        pattern = r'(\d+)\.\s*\*\*(\d{4}-\d{2}-\d{2})\*\*'
        matches = re.findall(pattern, content)
        
        for event_num, date_str in matches:
            inflection_points.append({
                'event_number': int(event_num),
                'date': date_str
            })
            
        print(f"Encontrados {len(inflection_points)} eventos en la narrativa")
        return inflection_points
        
    except Exception as e:
        print(f"Error leyendo narrativa: {e}")
        return []


def generate_annotated_chart(identifier: str = 'SPIPSA.INDX', years: int = 20, start_date_str: str | None = None, cutoff_date_str: str | None = None) -> str | None:
    """Genera un gráfico anotado con los puntos de inflexión de la narrativa."""
    load_dotenv()
    
    # Buscar archivo de narrativa
    narrative_file = os.path.join('quantex', 'experiments', 'ahc', f'ahc_{identifier}_narrative.md')
    
    if not os.path.exists(narrative_file):
        print(f"No se encontró narrativa en: {narrative_file}")
        print("Ejecuta primero run_ahc_narrative.py para generar la narrativa")
        return None
    
    # Extraer fechas de la narrativa
    inflection_points = parse_narrative_dates(narrative_file)
    
    if not inflection_points:
        print("No se pudieron extraer fechas de la narrativa")
        return None
    
    # Generar gráfico anotado
    output_filename = f"ahc_annotated_{identifier.replace('/', '_').replace('^','')}.png"
    chart_path = generate_log_chart(
        identifier=identifier,
        years=years,
        cutoff_date_str=cutoff_date_str,  # Hasta cutoff
        output_filename=output_filename,
        inflection_points=inflection_points,
        start_date_str=start_date_str
    )
    
    if chart_path:
        print(f"Gráfico anotado guardado en: {chart_path}")
        print(f"Eventos anotados: {len(inflection_points)}")
    
    return chart_path


if __name__ == '__main__':
    identifier = sys.argv[1] if len(sys.argv) > 1 else 'SPIPSA.INDX'
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    start = sys.argv[3] if len(sys.argv) > 3 else None
    cutoff = sys.argv[4] if len(sys.argv) > 4 else None
    
    generate_annotated_chart(identifier=identifier, years=years, start_date_str=start, cutoff_date_str=cutoff)

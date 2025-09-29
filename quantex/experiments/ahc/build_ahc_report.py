import os
import sys
from pathlib import Path


def _md_to_html(md_text: str) -> str:
    try:
        import markdown  # optional dependency
        return markdown.markdown(md_text, extensions=['extra', 'sane_lists'])
    except Exception:
        # Fallback simple: preservar saltos de línea y asteriscos en negrita básica
        html = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Negrita entre ** **
        import re
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        # Saltos de línea
        html = html.replace('\n', '<br>\n')
        return f"<div style='white-space: pre-wrap; font-family: system-ui, Segoe UI, Arial; font-size: 14px;'>{html}</div>"


def _split_narrative_sections(md_text: str) -> tuple[str, str]:
    """Separa la narrativa en secciones de puntos de inflexión y análisis mensual."""
    sections = md_text.split('## ')
    
    inflection_section = ""
    monthly_section = ""
    
    for section in sections:
        if section.startswith('PUNTOS DE INFLEXIÓN'):
            inflection_section = section.replace('PUNTOS DE INFLEXIÓN', '').strip()
        elif section.startswith('ANÁLISIS MENSUAL'):
            monthly_section = section.replace('ANÁLISIS MENSUAL', '').strip()
    
    return inflection_section, monthly_section


def build_report(identifier: str = 'SPIPSA.INDX') -> str:
    base_dir = Path('quantex/experiments/ahc')
    
    # Buscar gráfico anotado primero, luego el básico como fallback
    annotated_img_path = base_dir / f"ahc_annotated_{identifier.replace('/', '_').replace('^','')}.png"
    basic_img_path = base_dir / f"ahc_log_{identifier.replace('/', '_').replace('^','')}.png"
    
    if annotated_img_path.exists():
        img_path = annotated_img_path
        chart_type = "anotado con eventos"
    elif basic_img_path.exists():
        img_path = basic_img_path
        chart_type = "logarítmico"
    else:
        raise FileNotFoundError(f"No se encuentra ningún gráfico para {identifier}")
    
    md_path = base_dir / f"ahc_{identifier}_narrative.md"
    if not md_path.exists():
        raise FileNotFoundError(f"No se encuentra el markdown: {md_path}")

    md_text = md_path.read_text(encoding='utf-8')
    
    # Separar las secciones de la narrativa híbrida
    inflection_text, monthly_text = _split_narrative_sections(md_text)
    
    # Si no hay secciones separadas, usar el texto completo como fallback
    if not inflection_text and not monthly_text:
        narrative_html = _md_to_html(md_text)
        inflection_html = ""
        monthly_html = ""
    else:
        inflection_html = _md_to_html(inflection_text) if inflection_text else ""
        monthly_html = _md_to_html(monthly_text) if monthly_text else ""
        narrative_html = ""  # No usar el texto completo si tenemos secciones separadas

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AHC - {identifier}</title>
  <style>
    body {{ margin: 24px; font-family: system-ui, Segoe UI, Arial; color: #111; }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    .hero {{ margin-bottom: 20px; }}
    .figure img {{ width: 100%; height: auto; border: 1px solid #ddd; }}
    .caption {{ font-size: 12px; color: #666; margin-top: 6px; }}
    .section {{ margin: 28px 0; }}
    .event-legend {{ 
      background-color: #f8f9fa; 
      padding: 15px; 
      border-radius: 5px; 
      margin: 15px 0;
      border-left: 4px solid #e74c3c;
    }}
  </style>
</head>
<body>
  <header class="hero">
    <h1>Agente Historiador Compuesto (AHC) — {identifier}</h1>
    <div class="caption">Gráfico {chart_type} y narrativa histórica hasta 2025-01-01.</div>
  </header>

  <section class="section figure">
    <img src="{img_path.name}" alt="AHC Chart {identifier}" />
    <div class="caption">Fuente: Supabase (Quantex). Imagen generada automáticamente.</div>
    {"<div class='event-legend'><strong>Leyenda:</strong> Las líneas rojas verticales indican fechas de eventos históricos. Los números amarillos corresponden a los eventos listados en la narrativa abajo.</div>" if "anotado" in chart_type else ""}
  </section>

  <section class="section narrative">
    <h2>Narrativa Histórica Híbrida</h2>
    {narrative_html}
    {f"<h3>Puntos de Inflexión Críticos</h3>{inflection_html}" if inflection_html else ""}
    {f"<h3>Análisis Mensual</h3>{monthly_html}" if monthly_html else ""}
  </section>

  <footer class="section">
    <div class="caption">Informe generado por AHC (experiments). Uso informativo, no es recomendación.</div>
  </footer>
</body>
</html>
"""
    out_path = base_dir / f"ahc_{identifier}_report.html"
    out_path.write_text(html, encoding='utf-8')
    print(f"Informe guardado en: {out_path}")
    return str(out_path)


if __name__ == '__main__':
    ident = sys.argv[1] if len(sys.argv) > 1 else 'SPIPSA.INDX'
    build_report(identifier=ident)

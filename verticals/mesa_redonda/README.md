# LinkedIn Post Generator

Generador automático de posts de LinkedIn en PDF basado en reportes de análisis de mercado de Quantex.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Modo interactivo (recomendado)
python -m quantex.verticals.mesa_redonda.linkedin_posts.linkedin_post_generator --interactive

# Generar post de CLP (último reporte)
python -m quantex.verticals.mesa_redonda.linkedin_posts.linkedin_post_generator --report_type=CLP

# Generar post de COBRE (último reporte)
python -m quantex.verticals.mesa_redonda.linkedin_posts.linkedin_post_generator --report_type=COBRE

# Generar post desde un reporte específico por ID
python -m quantex.verticals.mesa_redonda.linkedin_posts.linkedin_post_generator --report_id=123 --report_type=CLP

# Especificar nombre de archivo de salida
python -m quantex.verticals.mesa_redonda.linkedin_posts.linkedin_post_generator --report_type=COBRE --output=post_cobre
```

## Estructura

```
verticals/mesa_redonda/
├── linkedin_posts/
│   ├── linkedin_post_generator.py    # Script principal
│   ├── CLP_linkedin_post_template.html   # Template para CLP
│   ├── COBRE_linkedin_post_template.html # Template para COBRE (futuro)
│   └── outputs/                      # PDFs generados
└── requirements.txt                  # Dependencias
```

## Funcionalidades

- ✅ Extracción automática de datos desde Supabase
- ✅ Análisis de sentiment usando LLM
- ✅ Generación de hooks atractivos
- ✅ Template HTML profesional
- ✅ Conversión a PDF con weasyprint
- ✅ Soporte para reportes de cobre y CLP

## Output

Los PDFs se generan en la carpeta `linkedin_posts/outputs/` con el formato:
`linkedin_post_{report_id}_{timestamp}.pdf`

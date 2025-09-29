# Quantex Leads Pipeline

## Descripción
Pipeline completo para procesamiento de leads desde Phantombuster hasta Airtable con clasificación por IA.

## Flujo del Pipeline
```
Phantombuster API → Supabase → IA Classification → Airtable
```

### Pasos del Pipeline:
1. **Extracción**: Obtiene datos del agent "Quantex Leads" en Phantombuster
2. **Ingesta**: Sube los datos a Supabase (tabla `linkedin_leads`) con detección de duplicados
3. **Clasificación IA**: Usa Haiku para clasificar candidatos como INCLUIR/DESCARTAR
4. **Sincronización**: Envía candidatos clasificados como "INCLUIR" a Airtable

## Archivos Principales

### `quantex_leads_pipeline.py`
**Archivo principal consolidado** que ejecuta todo el pipeline completo.

**Uso:**
```bash
python quantex_leads_pipeline.py
```

### `airtable_manager.py`
Gestor de Airtable para operaciones de contactos e interacciones.

### `communication_tools.py`
Herramientas de comunicación (email, webhooks, etc.).

## Configuración Requerida

### Variables de Entorno (.env):
```
PHANTOMBUSTER_API_KEY=tu_api_key_aqui
AIRTABLE_API_KEY=tu_api_key_aqui
AIRTABLE_BASE_ID=tu_base_id_aqui
```

### Base de Datos Supabase:
- Tabla: `linkedin_leads`
- Campos principales: `full_name`, `title`, `company_name`, `linkedin_profile_url`, `ai_classification`, `ai_score`, `ai_justification`, `airtable_synced`

### Airtable:
- Tabla: `Contacts`
- Campos: `Name`, `Email`, `Company`, `Title`, `LinkedInProfile`, `Type`, `Status`

## Resultados Actuales
- **Total de leads procesados**: 164
- **Candidatos clasificados**: 164 (100%)
- **Candidatos incluidos**: 71 (43.3%)
- **Candidatos sincronizados**: 71 (100% de los incluidos)

## Próximos Pasos
- Conectar con phantom de envío de DMs
- Automatizar el pipeline completo
- Implementar seguimiento de interacciones

## Logs
Los logs se guardan en `quantex_leads_pipeline.log` con información detallada de cada paso del proceso.


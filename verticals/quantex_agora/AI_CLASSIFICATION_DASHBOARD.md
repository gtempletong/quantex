# AI Classification Dashboard Integration

## 📋 Descripción

Integración del sistema de clasificación AI (`complete_classification_system.py`) con el dashboard CRM de Prospects.

## 🚀 Funcionalidad

Permite ejecutar la clasificación AI de empresas **directamente desde el dashboard**, sin necesidad de ejecutar scripts manualmente.

### ¿Qué hace?

1. **Analiza la empresa** con Perplexity Sonar Pro (búsqueda web en tiempo real)
2. **Clasifica con Claude Sonnet 4** (análisis inteligente + score 0-100)
3. **Actualiza apollo_companies** con:
   - `ai_score` (0-100)
   - `ai_classification` (INCLUIR/REVISAR/EXCLUIR)
   - `ai_analysis_report` (reporte completo)
   - `perplexity_analysis` (datos crudos de Perplexity)
4. **Clasifica automáticamente a todas las personas** asociadas a esa empresa

---

## 🎯 Cómo usar

### Desde el Dashboard CRM

1. **Ve a la página de Prospects** (`http://localhost:3000/prospects`)
2. **Busca una empresa sin análisis** (muestra "⚠️ Sin análisis disponible")
3. **Haz clic en "🤖 Clasificar con AI"**
4. **Confirma** que quieres ejecutar la clasificación
5. **Espera** a que termine (puede tomar 30-60 segundos)
6. **Resultado** se muestra en un alert con:
   - Score de la empresa
   - Clasificación (INCLUIR/REVISAR/EXCLUIR)
   - Número de personas actualizadas

### Re-clasificar

Si una empresa ya tiene análisis pero quieres actualizarlo:

1. **Expande el análisis** (clic en "📄 Ver análisis completo")
2. **Haz clic en "🔄 Re-clasificar"**
3. Se ejecutará nuevamente el análisis completo

---

## 🏗️ Arquitectura

### Backend

**Script Python:** `quantex/scripts/classify_single_company.py`
- Recibe `company_id` por stdin (JSON)
- Ejecuta `CompleteClassificationSystem._process_single_company()`
- Retorna resultado como JSON por stdout

**API Endpoint:** `quantex-crm/app/api/classify-company/route.ts`
- Endpoint POST en Next.js
- Ejecuta el script Python usando `child_process.spawn`
- Pasa datos via stdin, lee resultado de stdout
- Manejo de errores y logs

### Frontend

**Componente:** `quantex-crm/app/prospects/page.tsx`
- Handler `handleClassifyCompany(company_id, company_name)`
- Estado `classifyingCompanyId` para loading state
- Botones:
  - **"🤖 Clasificar con AI"** - Para empresas sin análisis
  - **"🔄 Re-clasificar"** - Para empresas con análisis existente

---

## 📊 Flujo de Datos

```
User clicks button
    ↓
Frontend: handleClassifyCompany()
    ↓
API: POST /api/classify-company
    ↓
Python: classify_single_company.py
    ↓
CompleteClassificationSystem:
    1. analyze_company_with_perplexity()
    2. analyze_company_with_ai()
    3. classify_persons_for_company()
    ↓
Supabase: Update apollo_companies + apollo_persons
    ↓
Return result to frontend
    ↓
Show alert + refresh table
```

---

## ⚙️ Requisitos

### Dependencias

- Python 3.x con `venv` activado
- Perplexity API key (`PERPLEXITY_API_KEY` en `.env`)
- Anthropic API key (`ANTHROPIC_API_KEY` en `.env`)
- Supabase credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`)

### Variables de Entorno

```env
PERPLEXITY_API_KEY=pplx-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=xxxxx
```

---

## 🔍 Debugging

### Ver logs del script Python

Los logs se imprimen a `stderr`, puedes verlos en la consola del servidor Next.js:

```bash
cd quantex-crm
npm run dev
```

Luego ejecuta la clasificación y verás:
```
🤖 Clasificando empresa: uuid-xxxx-xxxx
   ❓ Pregunta: ¿A qué se dedica la empresa X?
   🔍 Consultando Perplexity...
   ✅ Respuesta recibida
   ...
```

### Errores comunes

**Error:** `module 'quantex' not found`
- **Solución:** El script agrega `C:\quantex` al `sys.path` automáticamente

**Error:** `PERPLEXITY_API_KEY not found`
- **Solución:** Verifica que `.env` esté en `C:\quantex` con las credenciales correctas

**Error:** `Script Python falló con código 1`
- **Solución:** Revisa los logs en stderr para ver el error específico

---

## 📝 Ejemplo de Uso

```typescript
// Frontend (llamada desde el dashboard)
handleClassifyCompany("uuid-company-id", "Empresa X")

// API Response
{
  "ok": true,
  "company_name": "Empresa X",
  "company_score": 85,
  "company_classification": "INCLUIR",
  "persons_found": 3,
  "persons_updated": 3
}
```

---

## 🎨 UI/UX

### Estados del botón

- **Normal:** "🤖 Clasificar con AI" (purple-600)
- **Loading:** "⏳ Clasificando..." (disabled, opacity-50)
- **Re-clasificar:** "🔄 Re-clasificar" (purple-600)

### Feedback al usuario

- **Confirmación antes de ejecutar:** Muestra nombre de empresa y número estimado de personas
- **Loading state:** Botón deshabilitado con spinner emoji
- **Resultado exitoso:** Alert con score, clasificación y personas actualizadas
- **Error:** Alert con mensaje de error específico
- **Auto-refresh:** La tabla se refresca automáticamente al terminar

---

## 🚀 Próximas mejoras

- [ ] Batch classification (clasificar múltiples empresas a la vez)
- [ ] Progress bar para operaciones largas
- [ ] Mostrar logs en tiempo real
- [ ] Caché de análisis de Perplexity para evitar duplicados
- [ ] Filtro para mostrar solo empresas sin análisis
- [ ] Exportar resultados a CSV

---

## 📚 Archivos relacionados

- `verticals/quantex_agora/complete_classification_system.py` - Sistema principal
- `quantex/scripts/classify_single_company.py` - Script wrapper
- `quantex-crm/app/api/classify-company/route.ts` - API endpoint
- `quantex-crm/app/prospects/page.tsx` - Frontend integration
- `COMPANY_NAME_SYNC_ARCHITECTURE.md` - Arquitectura de datos














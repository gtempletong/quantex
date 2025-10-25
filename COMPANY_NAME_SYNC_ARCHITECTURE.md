# Arquitectura de Sincronización: Company Names

## 🎯 Principio Fundamental

**UNA SOLA FUENTE DE VERDAD para cada campo compartido**

---

## 📊 FUENTES DE VERDAD DEFINIDAS

### 1. NOMBRE DE LA EMPRESA

**Fuente de verdad:** `apollo_companies.name`

**Campo denormalizado:** `apollo_persons.company_name` (solo para auditoría y reportes)

**Reglas:**
- ✅ `apollo_companies.name` es la fuente de verdad ÚNICA
- ✅ `apollo_persons.company_name` debe SIEMPRE reflejar `apollo_companies.name`
- ✅ Al editar `company_name` desde el CRM:
  1. Se actualiza `apollo_companies.name`
  2. Se sincronizan TODAS las personas (`apollo_persons.company_name`) con ese `company_id`

**Código implementado:** `quantex-crm/app/api/prospects/[id]/route.ts` (líneas 40-69)

```typescript
// Cuando se edita company_name:
if (body.company_name !== undefined && currentPerson?.company_id) {
  // 1. Actualizar apollo_companies.name (fuente de verdad)
  await supabase
    .from('apollo_companies')
    .update({ name: newCompanyName, updated_at: new Date().toISOString() })
    .eq('id', currentPerson.company_id);

  // 2. Sincronizar TODAS las personas de esa empresa
  await supabase
    .from('apollo_persons')
    .update({ company_name: newCompanyName, updated_at: new Date().toISOString() })
    .eq('company_id', currentPerson.company_id);
}
```

---

### 2. WEBSITE DE LA EMPRESA

**Fuente de verdad:** `apollo_companies.website`

**Reglas:**
- ✅ Al editar `website_company` desde el CRM, se actualiza `apollo_companies.website`

**Código implementado:** `quantex-crm/app/api/prospects/[id]/route.ts` (líneas 71-77)

---

### 3. CLASIFICACIÓN AI DE LA EMPRESA

**Fuente de verdad:** `apollo_companies.ai_classification` y `apollo_companies.ai_score`

**Campos denormalizados:** `apollo_persons.company_ai_classification` y `apollo_persons.company_ai_score`

**IMPORTANTE:** La clasificación de la EMPRESA es independiente de la clasificación de la PERSONA:
- `apollo_companies.ai_classification` → ¿Es la empresa relevante?
- `apollo_persons.ai_classification` → ¿Es esta persona un decision-maker relevante?

**Reglas:**
- ✅ Al editar `company_ai_classification` o `company_ai_score`, se actualiza `apollo_companies`
- ✅ La clasificación de la persona (`ai_classification`, `ai_score`) es independiente

**Código implementado:** `quantex-crm/app/api/prospects/[id]/route.ts` (líneas 79-96, 107-110)

---

## 🔧 HERRAMIENTAS

### Script de Sincronización

**Ubicación:** `verticals/quantex_agora/sync_company_names.py`

**Uso:**
```bash
# Ver inconsistencias (DRY RUN):
python verticals/quantex_agora/sync_company_names.py

# Aplicar correcciones:
python verticals/quantex_agora/sync_company_names.py --apply
```

**Función:**
- Detecta empresas donde `apollo_companies.name` ≠ `apollo_persons.company_name`
- Reporta las inconsistencias
- Opcionalmente las corrige (sincroniza desde apollo_companies hacia apollo_persons)

---

## ✅ ESTADO ACTUAL (2025-10-25)

### Inconsistencias detectadas:
1. **Maquipan / Empresas Maquipan**
   - `apollo_companies.name`: "Maquipan"
   - `apollo_persons.company_name`: "Empresas Maquipan"
   - **Acción requerida:** Decidir cuál es el nombre oficial y actualizar apollo_companies manualmente

### Código actualizado:
- ✅ `quantex-crm/app/api/prospects/[id]/route.ts` - Sincronización automática implementada
- ✅ `quantex-crm/app/api/prospects/route.ts` - Query usa JOIN con apollo_companies
- ✅ `quantex-crm/app/prospects/page.tsx` - Frontend usa apollo_companies.name (fuente de verdad)
- ✅ `verticals/quantex_agora/sync_company_names.py` - Script de detección y corrección

### ¿Cómo funcionan los datos ahora?

**REGLA GENERAL:**
- 📊 **Información de empresas** → MANDA `apollo_companies`
- 👤 **Información de personas** → MANDA `apollo_persons`
- 🔗 **Están linkead as** vía `apollo_persons.company_id → apollo_companies.id`

**En el código:**
```typescript
// Backend (quantex-crm/app/api/prospects/route.ts)
.from('apollo_persons')
.select(`
  full_name, email, title,  // Datos de la persona
  apollo_companies!left(    // JOIN para datos de la empresa
    name,                    // ✅ Fuente de verdad
    website,                 // ✅ Fuente de verdad
    ai_classification        // ✅ Fuente de verdad (empresa)
  )
`)

// Frontend (page.tsx)
prospect.apollo_companies?.name  // ✅ Muestra el nombre de apollo_companies
```

**Al editar:**
1. Usuario cambia `company_name` en el modal
2. Backend actualiza `apollo_companies.name` (fuente de verdad)
3. Backend sincroniza `apollo_persons.company_name` para TODAS las personas
4. Frontend refresca y muestra `apollo_companies.name`

---

## 📋 FLUJO DE TRABAJO

### Al editar desde el CRM Dashboard:

1. Usuario edita campo `company_name` de una persona
2. Frontend envía `PUT /api/prospects/{id}` con `{ company_name: "Nuevo Nombre" }`
3. Backend:
   - Obtiene `company_id` de la persona
   - Actualiza `apollo_companies.name = "Nuevo Nombre"` (fuente de verdad)
   - Sincroniza `apollo_persons.company_name = "Nuevo Nombre"` para TODAS las personas con ese `company_id`
4. La persona actual también se actualiza con sus campos propios (email, phone, title, etc.)

### Al importar desde CSV (Apollo.io):

1. CSV trae `company_name` para cada persona
2. Script de importación:
   - Busca/crea empresa en `apollo_companies` con ese nombre
   - Crea persona en `apollo_persons` con `company_name` y `company_id`
3. **IMPORTANTE:** Si el nombre cambia en Apollo.io, usar el script de sincronización para normalizar

---

## 🚨 REGLAS CRÍTICAS

1. **NUNCA** actualizar `apollo_persons.company_name` sin actualizar `apollo_companies.name`
2. **SIEMPRE** sincronizar todas las personas de una empresa cuando cambia el nombre
3. **SEPARAR** clasificación de empresa vs clasificación de persona (son independientes)
4. Ejecutar `sync_company_names.py` periódicamente para detectar/corregir inconsistencias

---

## 🔍 Para el futuro

Campos que también podrían necesitar sincronización:
- `apollo_companies.industry`
- `apollo_companies.employee_count`
- `apollo_companies.location/city/state/country`

Actualmente estos campos NO están denormalizados en `apollo_persons`, por lo que no requieren sincronización.


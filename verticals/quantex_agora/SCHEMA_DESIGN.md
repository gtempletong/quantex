# 🗄️ DISEÑO DE BASE DE DATOS - QUANTEX AGORA

## 📊 ARQUITECTURA DE 3 TABLAS

```
┌─────────────────────────────────────┐
│         COMPANIES (Empresas)        │
├─────────────────────────────────────┤
│ id (UUID, PK)                       │
│ name (TEXT, UNIQUE) ⭐              │
│ industry (TEXT)                     │
│ employee_count (INTEGER) ⭐         │
│ annual_revenue (BIGINT) ⭐          │
│ website (TEXT)                      │
│ linkedin_url (TEXT)                 │
│ location (TEXT) ⭐                  │
│ city (TEXT) ⭐                      │
│ state (TEXT) ⭐                     │
│ country (TEXT) ⭐                   │
│ created_at / updated_at             │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│         PERSONS (Personas)          │
├─────────────────────────────────────┤
│ id (UUID, PK)                       │
│ full_name (TEXT) ⭐                 │
│ email (TEXT, UNIQUE) ⭐             │
│ title (TEXT) ⭐                     │
│ linkedin_url (TEXT, UNIQUE) ⭐      │
│ company_id (UUID, FK) → companies   │
│ seniority (TEXT)                    │
│ phone (TEXT)                        │
│ created_at / updated_at             │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    ACTIVE_CONTACTS (ya existe)      │
├─────────────────────────────────────┤
│ id (UUID, PK)                       │
│ person_id (UUID, FK) → persons ⭐   │
│ full_name (TEXT)                    │
│ email (TEXT)                        │
│ company_name (TEXT)                 │
│ source (TEXT)                       │
│ notes (TEXT)                        │
│ can_receive_communications (BOOL)   │
│ linkedin_url (TEXT)                 │
│ created_at / updated_at             │
└─────────────────────────────────────┘
```

## 🎯 CAMPOS CLAVE (⭐)

### **COMPANIES**
- ✅ **name**: Nombre único de la empresa
- ✅ **employee_count**: Número de empleados (filtrar por tamaño)
- ✅ **annual_revenue**: Ingresos anuales en USD (priorizar empresas grandes)
- ✅ **location**: Ubicación completa
- ✅ **city, state, country**: Desglose de ubicación (filtrar por región)

### **PERSONS**
- ✅ **full_name**: Nombre completo
- ✅ **email**: Email verificado (único)
- ✅ **title**: Cargo (CEO, CFO, etc.)
- ✅ **linkedin_url**: Perfil de LinkedIn (único)

### **ACTIVE_CONTACTS**
- ✅ **person_id**: Referencia a persona completa

---

## 📋 EJEMPLO DE DATOS

### **Company:**
```json
{
  "name": "DPS CHILE",
  "industry": "import & export",
  "employee_count": 160,
  "annual_revenue": 22000000,
  "location": "Santiago, Santiago Metropolitan Region, Chile",
  "city": "Santiago",
  "state": "Santiago Metropolitan Region",
  "country": "Chile"
}
```

### **Person:**
```json
{
  "full_name": "Boris Stumpf Valenzuela",
  "email": "bstumpf@dpschile.cl",
  "title": "Chief Financial Officer",
  "linkedin_url": "http://www.linkedin.com/in/borisstumpf",
  "company_id": "...",
  "seniority": "C suite",
  "phone": "+56 55 261 8292"
}
```

### **Active Contact:**
```json
{
  "person_id": "...",
  "full_name": "Boris Stumpf Valenzuela",
  "email": "bstumpf@dpschile.cl",
  "company_name": "DPS CHILE",
  "source": "prospecto",
  "notes": "Chief Financial Officer | Tel: +56552618292",
  "can_receive_communications": true,
  "linkedin_url": "http://www.linkedin.com/in/borisstumpf"
}
```

---

## 🔍 QUERIES ÚTILES

### **Empresas grandes en Chile:**
```sql
SELECT * FROM companies 
WHERE country = 'Chile' 
  AND employee_count > 500 
ORDER BY annual_revenue DESC;
```

### **CFOs en Chile:**
```sql
SELECT p.*, c.name as company_name, c.employee_count
FROM persons p
LEFT JOIN companies c ON p.company_id = c.id
WHERE p.title ILIKE '%CFO%' 
  AND c.country = 'Chile'
ORDER BY c.employee_count DESC;
```

### **Contactos activos con datos completos:**
```sql
SELECT 
  ac.*,
  p.title,
  p.seniority,
  p.phone,
  c.industry,
  c.employee_count,
  c.annual_revenue,
  c.city,
  c.country
FROM active_contacts ac
LEFT JOIN persons p ON ac.person_id = p.id
LEFT JOIN companies c ON p.company_id = c.id
ORDER BY c.annual_revenue DESC NULLS LAST;
```

---

## 💡 VENTAJAS DE ESTA ARQUITECTURA

### **✅ Sin Duplicados**
- Empresa "DPS CHILE" existe UNA vez
- Persona con email existe UNA vez
- Si actualizas el cargo, se actualiza en un solo lugar

### **✅ Fácil Segmentación**
```sql
-- Empresas grandes de minería
SELECT * FROM companies 
WHERE industry = 'Mining & Metals' 
  AND employee_count > 200;

-- CEOs de empresas grandes
SELECT * FROM persons p
JOIN companies c ON p.company_id = c.id
WHERE p.seniority = 'C suite'
  AND c.employee_count > 500;
```

### **✅ Datos Ricos**
- Saber revenue de empresa
- Saber tamaño por empleados
- Filtrar por ubicación específica

### **✅ Relaciones Claras**
```
Person → Company → Location, Industry, Size, Revenue
```

---

## 🚀 PRÓXIMOS PASOS

1. **Ejecutar SQL** en Supabase para crear tablas
2. **Importar CSV** con `apollo_importer_v2.py`
3. **Verificar datos** en dashboard de Supabase
4. **Crear queries** para segmentación inteligente


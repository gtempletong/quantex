# 🚀 WORKFLOW: Apollo.io → Supabase

## 📋 **FLUJO COMPLETO DE PROSPECCIÓN**

Este flujo te permite usar Apollo.io (GRATIS) para generar leads y agregarlos automáticamente a Supabase.

---

## 🎯 **PASO 1: Crear Lista en Apollo.io**

### **1.1 Ir a People Search**
```
https://app.apollo.io/#/people
```

### **1.2 Aplicar Filtros de Búsqueda**
Ejemplos de filtros útiles:

**Para CEOs de Minería en Chile:**
- **Title**: CEO, Chief Executive Officer, Director General
- **Location**: Chile, Santiago
- **Industry**: Mining & Metals, Copper Mining
- **Company Size**: 51-200, 201-500, 501-1000 employees
- **Seniority**: C-Level, VP-Level

**Para CFOs de Empresas Grandes:**
- **Title**: CFO, Chief Financial Officer, Director Financiero
- **Location**: Chile
- **Company Size**: 500+ employees
- **Industry**: Financial Services, Banking

### **1.3 Crear Lista**
1. Seleccionar contactos:
   - Click en checkbox de cada contacto interesante
   - O usar "Select All" para seleccionar página completa
   
2. Click en "Add to Lists"

3. "Create New List"

4. Nombrar lista descriptivamente:
   - ✅ Ejemplo: "CEOs Minería Chile 2025-10"
   - ✅ Ejemplo: "CFOs Empresas +500 empleados Chile"
   - ❌ Evitar: "Lista 1", "Test"

---

## 📥 **PASO 2: Exportar Lista a CSV**

### **2.1 Ir a Lists**
1. Click en "Lists" en el menú lateral izquierdo
2. Encontrar tu lista creada
3. Click en la lista para abrirla

### **2.2 Exportar CSV**
1. Seleccionar todos los contactos (checkbox superior)

2. Click en "Export" → "Export to CSV"

3. **Configurar campos a exportar** (seleccionar todos):
   - ✅ Name / Full Name
   - ✅ Email
   - ✅ Title / Job Title
   - ✅ Company / Organization Name
   - ✅ Phone / Mobile Phone / Direct Phone
   - ✅ LinkedIn URL
   - ✅ Location / City / State
   - ✅ Industry
   - ✅ Company Size / # Employees

4. Click "Export"

5. Descargar CSV cuando esté listo

### **2.3 Guardar CSV**
Guardar el CSV en:
```
C:\quantex\verticals\quantex_agora\exports\
```

Ejemplo: `ceos_mineria_chile_2025-10-15.csv`

---

## 🔄 **PASO 3: Importar CSV a Supabase**

### **3.1 Modo de Prueba (DRY RUN)**
Primero prueba sin insertar para verificar que todo está OK:

```bash
cd C:\quantex
C:\quantex\venv\Scripts\python.exe verticals\quantex_agora\apollo_csv_importer.py verticals\quantex_agora\exports\tu_archivo.csv --dry-run
```

Verás un resumen de qué se importaría sin insertar nada.

### **3.2 Importación Real**
Si el dry run se ve bien, importa de verdad:

```bash
C:\quantex\venv\Scripts\python.exe verticals\quantex_agora\apollo_csv_importer.py verticals\quantex_agora\exports\tu_archivo.csv
```

### **3.3 Opciones Avanzadas**

**Permitir duplicados** (no recomendado):
```bash
python apollo_csv_importer.py archivo.csv --allow-duplicates
```

**Ver ayuda**:
```bash
python apollo_csv_importer.py --help
```

---

## 📊 **PASO 4: Verificar en Supabase**

### **4.1 Verificar en Dashboard de Supabase**
1. Ir a https://app.supabase.com
2. Seleccionar proyecto Quantex
3. Ir a Table Editor → `active_contacts`
4. Verificar que aparezcan los nuevos contactos

### **4.2 Verificar Estadísticas**
```sql
-- Total de contactos
SELECT COUNT(*) FROM active_contacts;

-- Contactos de Apollo.io
SELECT COUNT(*) FROM active_contacts WHERE 'apollo_io' = ANY(tags);

-- Por fuente
SELECT source, COUNT(*) FROM active_contacts GROUP BY source;

-- Con email
SELECT COUNT(*) FROM active_contacts WHERE email IS NOT NULL;

-- Con LinkedIn
SELECT COUNT(*) FROM active_contacts WHERE linkedin_url IS NOT NULL;
```

---

## 🎯 **MEJORES PRÁCTICAS**

### **✅ DO:**
1. **Nombrar listas descriptivamente** con fecha
2. **Exportar todos los campos** disponibles
3. **Hacer dry-run primero** antes de importar
4. **Verificar duplicados** está activado por defecto
5. **Organizar CSVs** en carpeta `exports/` con nombres claros
6. **Agregar tags específicas** por campaña/búsqueda

### **❌ DON'T:**
1. ❌ No importar el mismo CSV dos veces (duplicados)
2. ❌ No borrar CSVs después de importar (mantener histórico)
3. ❌ No importar contactos sin email ni LinkedIn (inválidos)
4. ❌ No usar nombres genéricos para listas

---

## 🔧 **TROUBLESHOOTING**

### **Error: "Archivo no encontrado"**
- Verificar ruta del CSV
- Usar comillas si hay espacios: `"C:\ruta\con espacios\archivo.csv"`

### **Error: "Variables de entorno de Supabase no configuradas"**
- Verificar que `.env` tenga `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`

### **Muchos contactos saltados como duplicados**
- Es normal si ya importaste antes
- Verificar con: `--dry-run` para ver qué se saltaría

### **CSV con codificación incorrecta (caracteres raros)**
- Abrir CSV en Excel
- Guardar como "CSV UTF-8 (Comma delimited)"
- Volver a importar

---

## 📈 **PRÓXIMOS PASOS**

Una vez que tengas contactos en `active_contacts`:

1. **Segmentar** en el CRM (quantex-crm)
2. **Crear campañas** de email con Brevo
3. **Trackear interacciones** en Supabase
4. **Nutrir leads** con contenido relevante
5. **Convertir** a clientes activos

---

## 💡 **TIPS AVANZADOS**

### **Búsquedas Específicas para Chile**

**Minería:**
```
Title: CEO, CFO, Director, VP
Industry: Mining & Metals, Copper Mining
Location: Chile
Company Size: 200+
```

**Finanzas:**
```
Title: CFO, Tesorero, Gerente Finanzas
Industry: Financial Services, Banking
Location: Chile
Company Size: 500+
```

**Tecnología:**
```
Title: CTO, CIO, Director TI
Industry: Technology, Software
Location: Chile
Company Size: 50+
```

### **Automatización Futura**

Si creces y necesitas más volumen:
- **Upgrade a plan Basic ($49/mes)** para API completa
- **Automatizar búsquedas** con `apollo_client.py`
- **Importación diaria** automática vía cron/scheduled task
- **Integración directa** sin CSV intermedio

---

## 🎉 **¡LISTO!**

Ahora tienes un sistema completo para:
1. ✅ Buscar leads en Apollo.io
2. ✅ Exportar a CSV
3. ✅ Importar a Supabase
4. ✅ Gestionar en tu CRM

**¡Sin restricciones de LinkedIn y 100% GRATIS!** 🚀


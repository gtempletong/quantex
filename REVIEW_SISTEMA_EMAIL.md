# 📧 REVIEW COMPLETO: Sistema de Emails Inteligente

## 🎯 **OBJETIVO DEL SISTEMA**

Crear un sistema inteligente para:
1. **Buscar prospectos** en la base de datos
2. **Identificar** quiénes NO han recibido emails
3. **Preparar** información completa para personalización
4. **Preparar** el envío automático (futuro)

---

## 🏗️ **ARQUITECTURA DEL SISTEMA**

### **Componentes Principales:**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Agent     │    │   Tools Layer   │    │   Supabase DB   │
│                 │    │                 │    │                 │
│ • Planner       │───▶│ • find_person   │───▶│ • personas      │
│ • Query Parser  │    │ • compose_email │    │ • empresas      │
│ • Tool Executor │    │ • send_email    │    │ • email_tracking│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Flujo de Trabajo:**

1. **Usuario** → "Busca personas que no han recibido emails"
2. **LLM** → Analiza query y crea plan
3. **Planner** → Genera tool_calls específicos
4. **Runner** → Ejecuta herramientas
5. **Supabase** → Retorna datos
6. **Sistema** → Procesa y retorna resultado

---

## 📊 **BASE DE DATOS**

### **Tabla `personas`:**
```sql
- id (integer, PK)
- rut_empresa (varchar) → FK a empresas
- nombre_contacto (text)
- cargo_contacto (text)
- email_contacto (text)
- celular_contacto (text)
- telefono_contacto (text)
- email_sent (boolean) → NUEVO: Tracking de emails
- email_sent_at (timestamp) → NUEVO: Fecha de envío
- estado (text)
- tipo_empresa (text)
```

### **Tabla `empresas`:**
```sql
- id (uuid, PK)
- rut_empresa (varchar, UNIQUE)
- razon_social (text)
- sitio_web (text)
- direccion (text)
- comuna (text)
- region (text)
- actividad_economica (text)
```

### **Relación:**
- `personas.rut_empresa` → `empresas.rut_empresa`
- **NO hay FK directa** → Se hace JOIN manual

---

## 🛠️ **HERRAMIENTAS DISPONIBLES**

### **1. `supabase.find_person`** ⭐ **PRINCIPAL**

**Propósito:** Buscar personas con información completa

**Parámetros:**
```json
{
  "search_term": "string",     // Término de búsqueda
  "search_type": "name|email|rut", // Tipo de búsqueda
  "only_unsent": boolean       // Solo personas sin emails
}
```

**Ejemplo de Uso:**
```python
# Buscar por nombre
execute_tool({
  "tool": "supabase.find_person",
  "params": {
    "search_term": "Juan",
    "search_type": "name"
  }
})

# Buscar prospectos sin emails
execute_tool({
  "tool": "supabase.find_person", 
  "params": {
    "search_term": "*",
    "search_type": "name",
    "only_unsent": true
  }
})
```

**Respuesta:**
```json
{
  "ok": true,
  "found": true,
  "person": {
    "id": 193,
    "nombre_contacto": "juan pablo rodriguez ayuso",
    "cargo_contacto": "Jefe de Proyectos",
    "email_contacto": "jprodriguez@empresasryr.cl",
    "celular_contacto": "56-9-2246979",
    "telefono_contacto": "56-2-24104600",
    "email_sent": false,
    "email_sent_at": null,
    "estado": "ACTIVO",
    "tipo_empresa": "GRANDE",
    "empresa": {
      "razon_social": "RODRIGUEZ Y RODRIGUEZ CONSTRUCCIONES LIMITADA",
      "rut_empresa": "86903500-9",
      "sitio_web": null
    }
  }
}
```

### **2. `llm.compose_email`** 📝

**Propósito:** Redactar emails personalizados usando LLM

**Parámetros:**
```json
{
  "recipient_name": "string",
  "recipient_company": "string", 
  "email_purpose": "string",
  "context": "string",
  "tone": "formal|professional|friendly"
}
```

### **3. `brevo.send_email`** 📤

**Propósito:** Enviar emails usando Brevo SDK

**Parámetros:**
```json
{
  "to": ["email@example.com"],
  "subject": "string",
  "html_body": "string"
}
```

---

## 🤖 **COMPONENTE LLM**

### **Planner (`planner.py`):**

**Función:** `plan_action(user_query)`

**Proceso:**
1. Recibe query en lenguaje natural
2. Analiza contexto y herramientas disponibles
3. Genera plan estructurado
4. Retorna `tool_calls` específicos

**Ejemplo:**
```python
# Input
plan_action("Busca a Juan en la base de datos")

# Output
{
  "plan": ["Buscar persona con nombre 'Juan' en la base de datos"],
  "tool_calls": [{
    "tool": "supabase.find_person",
    "params": {
      "search_term": "Juan",
      "search_type": "name"
    }
  }],
  "approvals_needed": False
}
```

### **Runner (`runner.py`):**

**Función:** `execute_tool(tool_call)`

**Proceso:**
1. Recibe `tool_call` del planner
2. Identifica herramienta a ejecutar
3. Llama función específica
4. Retorna resultado

---

## 🔍 **CASOS DE USO PROBADOS**

### **1. Búsqueda Simple**
```python
# Query: "Busca a Juan en la base de datos"
# LLM entiende → name search
# Resultado: Juan Pablo Rodríguez Ayuso
```

### **2. Filtro de Prospectos**
```python
# Query: "Encuentra personas que no han recibido emails"
# LLM entiende → only_unsent=true
# Resultado: Cristian Arancibia Portilla (email_sent=false)
```

### **3. Búsqueda por Email**
```python
# Query: "¿Quién tiene el email jprodriguez@empresasryr.cl?"
# LLM entiende → email search
# Resultado: Juan Pablo Rodríguez Ayuso
```

---

## 🎯 **FORTALEZAS DEL SISTEMA**

### **✅ Ventajas:**

1. **Flexibilidad:** LLM entiende queries naturales
2. **Inteligencia:** Aplica filtros automáticamente
3. **Completitud:** Retorna persona + empresa en una consulta
4. **Escalabilidad:** Fácil agregar nuevas herramientas
5. **Mantenibilidad:** Código modular y bien estructurado

### **🔧 Capacidades Técnicas:**

- **Búsqueda multi-criterio:** nombre, email, RUT
- **JOIN automático:** personas + empresas
- **Filtros inteligentes:** only_unsent, estado, tipo
- **Manejo de errores:** casos no encontrados
- **SDK oficial:** Supabase + Brevo

---

## 🚧 **LIMITACIONES ACTUALES**

### **❌ Pendientes:**

1. **Envío de emails:** Aún no implementado (deliberado)
2. **Tracking completo:** Solo básico (email_sent, email_sent_at)
3. **Personalización avanzada:** Templates más complejos
4. **Bulk operations:** Envío masivo de emails
5. **Analytics:** Métricas de campañas

---

## 📈 **ROADMAP FUTURO**

### **Fase 1: Completar Tracking (ACTUAL)**
- ✅ Columnas de tracking en DB
- ✅ Herramienta de búsqueda
- ✅ LLM integration
- 🔄 Testing exhaustivo

### **Fase 2: Sistema de Envío**
- 📧 Implementar envío real
- 📊 Dashboard de campañas
- 📈 Métricas y analytics
- 🔄 Testing de producción

### **Fase 3: Optimización**
- ⚡ Bulk operations
- 🎨 Templates avanzados
- 🤖 Personalización con IA
- 📱 Integración móvil

---

## 🔧 **CÓDIGO CLAVE**

### **Función Principal de Búsqueda:**

```python
def _execute_supabase_find_person(params):
    # 1. Validar parámetros
    search_term = params.get("search_term", "").strip()
    search_type = params.get("search_type", "name")
    only_unsent = params.get("only_unsent", False)
    
    # 2. Crear cliente Supabase
    supabase = create_client(url, key)
    
    # 3. Construir query
    query = supabase.table('personas').select("""
        id, rut_empresa, nombre_contacto, cargo_contacto,
        email_contacto, celular_contacto, telefono_contacto,
        email_sent, email_sent_at, estado, tipo_empresa
    """)
    
    # 4. Aplicar filtros
    if search_type == "name":
        query = query.ilike('nombre_contacto', f'%{search_term}%')
    elif search_type == "email":
        query = query.ilike('email_contacto', f'%{search_term}%')
    elif search_type == "rut":
        query = query.ilike('rut_empresa', f'%{search_term}%')
    
    if only_unsent:
        query = query.eq('email_sent', False)
    
    # 5. Ejecutar query
    response = query.execute()
    
    # 6. Buscar empresa asociada
    if response.data:
        person_data = response.data[0]
        empresa_info = None
        if person_data.get('rut_empresa'):
            empresa_response = supabase.table('empresas').select(
                'razon_social, rut_empresa, sitio_web'
            ).eq('rut_empresa', person_data['rut_empresa']).execute()
            
            if empresa_response.data:
                empresa_data = empresa_response.data[0]
                empresa_info = {
                    "razon_social": empresa_data.get('razon_social'),
                    "rut_empresa": empresa_data.get('rut_empresa'),
                    "sitio_web": empresa_data.get('sitio_web')
                }
    
    # 7. Retornar resultado
    return {
        "ok": True,
        "found": True,
        "person": {
            **person_data,
            "empresa": empresa_info
        }
    }
```

---

## 🎓 **LECCIONES APRENDIDAS**

### **1. Arquitectura Modular:**
- Separar planner, runner y tools
- Facilita testing y mantenimiento
- Permite escalabilidad

### **2. LLM Integration:**
- LLM entiende contexto natural
- Genera tool_calls específicos
- Maneja casos edge automáticamente

### **3. Database Design:**
- Tracking columns esenciales
- JOIN manual por rut_empresa
- Estructura flexible para queries

### **4. Error Handling:**
- Validación de parámetros
- Manejo de casos no encontrados
- Logging para debugging

---

## 🚀 **PRÓXIMOS PASOS**

1. **Probar más queries** para validar robustez
2. **Implementar envío real** cuando esté listo
3. **Crear dashboard** para monitoreo
4. **Optimizar performance** para bulk operations
5. **Agregar analytics** para métricas

---

## 💡 **CONCLUSIONES**

El sistema actual es **sólido y escalable**:
- ✅ **Funcionalidad core** implementada
- ✅ **LLM integration** funcionando
- ✅ **Base de datos** optimizada
- ✅ **Arquitectura** modular
- 🔄 **Listo para** siguiente fase

**¡El sistema está listo para crecer!** 🎯




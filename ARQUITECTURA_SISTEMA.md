# 🏗️ ARQUITECTURA DEL SISTEMA DE EMAILS INTELIGENTE

## 📋 **DIAGRAMA DE ARQUITECTURA**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA DE EMAILS INTELIGENTE                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   USER INPUT    │    │   LLM AGENT     │    │   TOOLS LAYER   │
│                 │    │                 │    │                 │
│ "Busca a Juan"  │───▶│ • Planner       │───▶│ • find_person   │
│ "Prospectos     │    │ • Query Parser  │    │ • compose_email │
│  sin emails"    │    │ • Tool Executor │    │ • send_email    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RESPONSE      │    │   PLANNER       │    │   SUPABASE DB   │
│                 │    │                 │    │                 │
│ Person + Company│◀───│ • Genera plan   │◀───│ • personas      │
│ Info completa   │    │ • Tool calls    │    │ • empresas      │
│ Email status    │    │ • Parameters    │    │ • tracking      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 **FLUJO DETALLADO**

### **1. ENTRADA DEL USUARIO**
```
Usuario: "Encuentra personas que no han recibido emails"
```

### **2. PROCESAMIENTO LLM**
```
Planner analiza:
- Query: "Encuentra personas que no han recibido emails"
- Contexto: Buscar en base de datos
- Herramientas disponibles: supabase.find_person
- Parámetros necesarios: search_term="*", only_unsent=true
```

### **3. GENERACIÓN DEL PLAN**
```json
{
  "plan": [
    "Buscar todas las personas en la base de datos que no han recibido emails",
    "Usar la función find_person con parámetro only_unsent=true"
  ],
  "tool_calls": [{
    "tool": "supabase.find_person",
    "params": {
      "search_term": "*",
      "search_type": "name", 
      "only_unsent": true
    }
  }],
  "approvals_needed": false
}
```

### **4. EJECUCIÓN DE HERRAMIENTA**
```
Runner ejecuta:
- Tool: supabase.find_person
- Parámetros: search_term="*", search_type="name", only_unsent=true
```

### **5. QUERY A BASE DE DATOS**
```sql
SELECT 
  id, rut_empresa, nombre_contacto, cargo_contacto,
  email_contacto, celular_contacto, telefono_contacto,
  email_sent, email_sent_at, estado, tipo_empresa
FROM personas 
WHERE nombre_contacto ILIKE '%*%' 
  AND email_sent = false
LIMIT 1;
```

### **6. JOIN CON EMPRESAS**
```sql
SELECT razon_social, rut_empresa, sitio_web
FROM empresas 
WHERE rut_empresa = '77202760-5';
```

### **7. RESPUESTA FINAL**
```json
{
  "ok": true,
  "found": true,
  "person": {
    "id": 168,
    "nombre_contacto": "cristian arancibia portilla",
    "cargo_contacto": "Gerente",
    "email_contacto": "funcionalidad@hotelgarradeleon.cl",
    "email_sent": false,
    "email_sent_at": null,
    "empresa": {
      "razon_social": "SOC DE INVERSIONES BARAQUI GIMENEZ Y CIA LTDA",
      "rut_empresa": "77202760-5",
      "sitio_web": "www.hotelgarradeleon.cl"
    }
  }
}
```

## 🛠️ **COMPONENTES TÉCNICOS**

### **1. LLM AGENT (`planner.py`)**
- **Función:** `plan_action(user_query)`
- **Modelo:** Claude Sonnet 4
- **Input:** Query en lenguaje natural
- **Output:** Plan estructurado con tool_calls

### **2. TOOL RUNNER (`runner.py`)**
- **Función:** `execute_tool(tool_call)`
- **Input:** Tool call del planner
- **Output:** Resultado de la herramienta
- **Herramientas:** find_person, compose_email, send_email

### **3. DATABASE LAYER**
- **Supabase Client:** SDK oficial
- **Tables:** personas, empresas
- **Relations:** rut_empresa (manual JOIN)
- **Tracking:** email_sent, email_sent_at

### **4. TOOLS REGISTRY (`tools.json`)**
- **Definición:** Esquemas de herramientas
- **Validación:** Parámetros requeridos
- **Documentación:** Ejemplos de uso

## 📊 **CASOS DE USO SOPORTADOS**

### **1. BÚSQUEDA SIMPLE**
```
Input: "Busca a Juan"
LLM: name search
Query: WHERE nombre_contacto ILIKE '%Juan%'
```

### **2. BÚSQUEDA POR EMAIL**
```
Input: "¿Quién tiene el email juan@empresa.com?"
LLM: email search  
Query: WHERE email_contacto ILIKE '%juan@empresa.com%'
```

### **3. FILTRO DE PROSPECTOS**
```
Input: "Encuentra personas que no han recibido emails"
LLM: only_unsent=true
Query: WHERE email_sent = false
```

### **4. BÚSQUEDA POR RUT**
```
Input: "Busca por RUT 12345678-9"
LLM: rut search
Query: WHERE rut_empresa ILIKE '%12345678%'
```

## 🎯 **VENTAJAS DE LA ARQUITECTURA**

### **✅ MODULARIDAD**
- Componentes independientes
- Fácil testing
- Escalabilidad

### **✅ INTELIGENCIA**
- LLM entiende contexto
- Parámetros automáticos
- Filtros inteligentes

### **✅ FLEXIBILIDAD**
- Queries naturales
- Múltiples criterios
- Fácil extensión

### **✅ ROBUSTEZ**
- Manejo de errores
- Validación de parámetros
- Logging completo

## 🚧 **LIMITACIONES ACTUALES**

### **❌ PENDIENTES**
1. **Envío real de emails** (deliberado)
2. **Bulk operations** (múltiples resultados)
3. **Templates avanzados** (personalización)
4. **Analytics** (métricas de campañas)
5. **Dashboard** (interfaz visual)

## 🚀 **ROADMAP TÉCNICO**

### **FASE 1: CORE (COMPLETADA)**
- ✅ Base de datos con tracking
- ✅ Herramienta de búsqueda
- ✅ LLM integration
- ✅ Testing básico

### **FASE 2: ENVÍO (PRÓXIMA)**
- 📧 Implementar send_email
- 📊 Dashboard de campañas
- 📈 Analytics básicos
- 🔄 Testing de producción

### **FASE 3: OPTIMIZACIÓN**
- ⚡ Bulk operations
- 🎨 Templates personalizados
- 🤖 IA avanzada
- 📱 API móvil

## 💡 **LECCIONES CLAVE**

### **1. SEPARACIÓN DE RESPONSABILIDADES**
- Planner: Lógica de negocio
- Runner: Ejecución de herramientas
- Tools: Operaciones específicas

### **2. LLM COMO ORQUESTADOR**
- No reemplaza lógica de negocio
- Mejora experiencia de usuario
- Facilita queries complejos

### **3. DATABASE DESIGN**
- Tracking columns esenciales
- JOIN manual por flexibilidad
- Estructura escalable

### **4. ERROR HANDLING**
- Validación en cada capa
- Mensajes informativos
- Logging para debugging

---

## 🎓 **CONCLUSIÓN**

El sistema actual es una **base sólida** para un sistema de emails inteligente:

- ✅ **Arquitectura modular** y escalable
- ✅ **LLM integration** funcionando
- ✅ **Base de datos** optimizada
- ✅ **Testing** básico completado
- 🔄 **Listo para** siguiente fase

**¡El sistema está preparado para crecer!** 🚀




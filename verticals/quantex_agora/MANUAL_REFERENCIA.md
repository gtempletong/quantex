# 📚 QUANTEX AGORA - MANUAL DE REFERENCIA

## 🔗 PHANTOMBUSTER API

### API v1 Endpoints
- **[Agent Launch](https://hub.phantombuster.com/reference/launchagent-1)** - `/agent/{id}/launch`
- **[Agent Output](https://hub.phantombuster.com/reference/outputagent-1)** - `/agent/{id}/output`
- **[Agent Containers](https://hub.phantombuster.com/reference/containeragent-1)** - `/agent/{id}/containers`
- **[Agent Info](https://hub.phantombuster.com/reference/getagentrecord-1)** - `/agent/{id}`
- **[Agent Abort](https://hub.phantombuster.com/reference/abortagent-1)** - `/agent/{id}/abort`

### API v2 Endpoints
- **[Agents Launch](https://hub.phantombuster.com/reference/launchagent-2)** - `/agents/launch`
- **[Agents Fetch](https://hub.phantombuster.com/reference/fetchagent-2)** - `/agents/fetch`
- **[Agents Fetch Output](https://hub.phantombuster.com/reference/fetch-outputagent-2)** - `/agents/fetch-output`

### Containers API v2
- **[Containers Fetch All](https://hub.phantombuster.com/reference/get_containers-fetch-all)** - `/containers/fetch-all`
- **[Containers Fetch](https://hub.phantombuster.com/reference/get_containers-fetch)** - `/containers/fetch`
- **[Containers Fetch Output](https://hub.phantombuster.com/reference/get_containers-fetch-output)** - `/containers/fetch-output`
- **[Containers Fetch Result Object](https://hub.phantombuster.com/reference/get_containers-fetch-result-object)** - `/containers/fetch-result-object`

### Phantom IDs
- **LinkedIn Auto Connect**: `5206783097588578`
- **LinkedIn Outreach Manager**: `5011671254988019`
- **Gavin LinkedIn Connections Export**: `186622136052552`

## 🗄️ AIRTABLE TABLES

### Prospectos Table
- **Table ID**: `tblkvQVBNWkpw77iy`
- **Table Name**: "Prospectos"
- **Fields**:
  - `Nombre` (Text)
  - `Empresa` (Long text)
  - `Cargo` (Long text)
  - `LinkedIn Profile URL` (URL)
  - `Estado` (Single select): "Listo para conectar", "Conectado", "Listo para DM", "DM Enviado", "Dm Aceptado", "Rechazado", "Bloqueado", "Convertido"
  - `Phantom Status` (Single select): "Activo", "En Cola", "Inactivo", "Pausado", "Excluido"
  - `Email` (Email)
  - `Fecha ultima actividad` (Long text)
  - `Fecha de Creacion` (Long text)

### Clientes Table
- **Table ID**: `tblXXXXXX` (pendiente)
- **Table Name**: "Clientes"

### Interacciones Table
- **Table ID**: `tblXXXXXX` (pendiente)
- **Table Name**: "Interacciones"

### Conecciones Table
- **Table ID**: `tblXXXXXX` (pendiente)
- **Table Name**: "Conecciones"

## 🔧 ENVIRONMENT VARIABLES

### Phantombuster
```env
PHANTOMBUSTER_API_KEY=xxx
PHANTOMBUSTER_AUTO_CONNECT_PHANTOM_ID=5206783097588578
PHANTOMBUSTER_PHANTOM_ID=5011671254988019
PHANTOMBUSTER_CONECTIONS_EXPORT_PHANTOM_ID=186622136052552
```

### Airtable
```env
AIRTABLE_API_KEY=xxx
AIRTABLE_BASE_ID=xxx
AIRTABLE_PROSPECTOS_TABLE_ID=tblkvQVBNWkpw77iy
AIRTABLE_CLIENTES_TABLE_ID=tblXXXXXX
AIRTABLE_INTERACTIONS_TABLE_ID=tblXXXXXX
AIRTABLE_CONECCIONES_TABLE_ID=tblXXXXXX
```

## 🚀 SISTEMA INTELIGENTE

### Flujo de Trabajo
1. **Leer leads** de Airtable con `Phantom Status = "En Cola"`
2. **Lanzar phantom** con URLs de LinkedIn
3. **Monitorear** ejecución del phantom
4. **Obtener resultados** del CSV/JSON
5. **Actualizar Airtable** con estados

### Estados Simplificados
- **Phantom Status**: Solo "En Cola" y "Activo"
- **Estado**: "Conectado" o "No Conectado"

### Lógica de Estados
- **"already in network"** → `Estado = "Conectado"`
- **"own profile"** → `Estado = "Conectado"`
- **Otros casos** → `Estado = "No Conectado"`

## 📁 ARCHIVOS PRINCIPALES

### Scripts
- `linkedin_auto_connect_manager.py` - Gestión principal del sistema
- `airtable_manager.py` - Interfaz con Airtable
- `phantom_base_manager.py` - Base para Phantombuster

### Configuración
- `.env` - Variables de entorno
- `phantombuster_config.txt` - Configuración de Phantombuster

## 🔍 DEBUGGING

### Logs Importantes
- **Container ID**: Para rastrear ejecuciones
- **CSV Filenames**: `database-linkedin-network-booster.csv`, `result.csv`, `output.csv`, `data.csv`
- **S3 URLs**: `https://phantombuster.s3.amazonaws.com/{orgS3Folder}/{s3Folder}/{csv_filename}`

### Estructura Real del CSV (LinkedIn Auto Connect)
- **Campos disponibles**:
  - `linkedinProfileUrl` - URL del perfil de LinkedIn
  - `error` - Estado de la conexión ("Own profile", "Already in network", etc.)
  - `fullName` - Nombre completo
  - `firstName` - Primer nombre
  - `lastName` - Apellido
  - `connectionDegree` - Grado de conexión ("You", "1st", "2nd", etc.)
  - `timestamp` - Fecha de procesamiento
  - `profileUrl` - URL del perfil
  - `inviterName` - Nombre del que envía la invitación

### Lógica de Estados (Confirmada)
- **"Own profile"** → `Estado = "Conectado"`
- **"Already in network"** → `Estado = "Conectado"`
- **Otros errores** → `Estado = "No Conectado"`

### Endpoints de Prueba
- **Launch**: `POST https://phantombuster.com/api/v1/agent/{id}/launch`
- **Output**: `GET https://phantombuster.com/api/v1/agent/{id}/output`
- **Containers**: `GET https://phantombuster.com/api/v1/agent/{id}/containers`

## 📝 NOTAS IMPORTANTES

- **API Key Header**: `X-Phantombuster-Key-1` (no `X-Phantombuster-Key`)
- **Profile URLs**: Deben ser lista de URLs, no string individual
- **CSV Parsing**: Usar `csv.DictReader` para procesar resultados
- **Error Handling**: Siempre verificar status codes y content types
- **Memory Management**: No crear archivos temporales, usar streams

## 🚨 PHANTOMBUSTER "GOTCHAS" - PROBLEMAS COMUNES

### ❌ PROBLEMAS DE DOCUMENTACIÓN

#### 1. **Headers Incorrectos**
```python
# ❌ INCORRECTO (no funciona)
headers = {"X-Phantombuster-Key": api_key}

# ✅ CORRECTO
headers = {"X-Phantombuster-Key-1": api_key}
```

#### 2. **Endpoints que NO Funcionan**
```python
# ❌ ESTOS ENDPOINTS DEVUELVEN LOGS, NO DATOS:
# /containers/fetch-output → Devuelve console logs
# /containers/fetch-result-object → Devuelve null o logs

# ✅ SOLUCIÓN: Usar S3 directo
# 1. GET /agents/fetch?id={phantom_id} → Obtener orgS3Folder y s3Folder
# 2. Construir URL: https://phantombuster.s3.amazonaws.com/{orgS3Folder}/{s3Folder}/{csv_filename}
```

#### 3. **Estructura de Respuestas Inconsistente**
```python
# ❌ A veces viene así:
{"status": "success", "data": {...}}

# ✅ A veces viene así:
{...}  # Directo, sin wrapper
```

#### 4. **Phantom ID vs Container ID**
```python
# ❌ CONFUSIÓN COMÚN:
# Phantom ID: 5206783097588578 (para lanzar)
# Container ID: 4289303020444560 (para obtener resultados)

# ✅ USAR CORRECTAMENTE:
# - Phantom ID para /agent/{id}/launch
# - Container ID para /containers/fetch
```

#### 5. **CSV Filenames Variables**
```python
# ❌ NO ESTÁ DOCUMENTADO CUÁL NOMBRE USAR:
csv_filenames = [
    "database-linkedin-network-booster.csv",  # Auto Connect
    "result.csv",                             # Gavin Connections
    "output.csv", 
    "data.csv"
]

# ✅ SOLUCIÓN: Probar todos hasta encontrar uno válido
```

#### 6. **S3 Paths Dinámicos**
```python
# ❌ NO HAY DOCUMENTACIÓN DE CÓMO CONSTRUIR URLS S3
# ✅ SOLUCIÓN DESCUBIERTA:
# 1. GET /agents/fetch?id={phantom_id}
# 2. Extraer orgS3Folder y s3Folder
# 3. Construir: https://phantombuster.s3.amazonaws.com/{orgS3Folder}/{s3Folder}/{filename}
```

### 🔍 DEBUGGING TIPS

#### 1. **Verificar Content-Type**
```python
if response.headers.get('Content-Type') == 'text/html':
    # ❌ Phantombuster devolvió la página web, no JSON
    logger.error("API devolvió HTML en lugar de JSON")
```

#### 2. **Usar S3 Explorer**
- **URL**: https://file-browser.phantombuster.com/
- **Útil para**: Verificar que archivos existen en S3

#### 3. **Probar Headers Diferentes**
```python
# Si un endpoint falla, probar:
headers = {"X-Phantombuster-Key-1": api_key}
# vs
headers = {"X-Phantombuster-Key": api_key}
```

#### 4. **Verificar Estructura de Respuesta**
```python
# Siempre verificar si hay wrapper:
if 'status' in response.json():
    data = response.json()['data']
else:
    data = response.json()
```

### 🎯 LECCIONES APRENDIDAS

1. **Phantombuster API es inconsistente** - No confiar en la documentación
2. **S3 directo es más confiable** que endpoints de containers
3. **Siempre verificar Content-Type** antes de parsear JSON
4. **Phantom ID ≠ Container ID** - Son conceptos diferentes
5. **CSV filenames cambian** - Probar múltiples opciones
6. **Headers correctos son críticos** - `X-Phantombuster-Key-1` es la clave

### 💡 RECOMENDACIONES

1. **Usar `/agents/fetch`** para obtener metadatos del phantom
2. **Construir URLs S3 directas** para obtener resultados
3. **Probar múltiples CSV filenames** hasta encontrar el correcto
4. **Siempre verificar status codes** y content types
5. **Mantener logs detallados** para debugging

## 🎯 PRÓXIMOS PASOS

1. ✅ ~~Implementar sistema de dos scripts (enviar + monitorear)~~ **COMPLETADO**
2. ✅ ~~Configurar automatización periódica~~ **COMPLETADO**
3. ✅ ~~Optimizar matching por LinkedIn URL~~ **COMPLETADO**
4. ✅ ~~Documentar "gotchas" de Phantombuster~~ **COMPLETADO**
5. **Pendiente**: Implementar webhooks para notificaciones en tiempo real
6. **Pendiente**: Optimizar frecuencia de monitoreo
7. **Pendiente**: Agregar métricas y dashboard

## 🏆 SISTEMA COMPLETADO

### ✅ FUNCIONALIDADES IMPLEMENTADAS:
- **Pipeline completo** de ingesta de leads
- **Clasificación IA** automática
- **Sistema inteligente** de gestión de prospectos
- **Monitoreo automático** de estados de LinkedIn
- **Detección automática** de conexiones aceptadas
- **Documentación completa** de problemas comunes

### 📊 ARQUITECTURA FINAL:
```
Phantombuster → Supabase → IA Classification → Airtable "Prospectos"
                     ↓
LinkedIn Sender → LinkedIn Auto Connect → LinkedIn Monitor
                     ↓
Gavin Connections Monitor → Detección de conexiones aceptadas
```

---
*Última actualización: 2025-01-13 - Sistema 100% funcional*

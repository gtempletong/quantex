# 🚀 MCP Servers para Quantex LinkedIn Automation

## 📁 Estructura Organizada

```
C:\Quantex\verticals\mcp_servers\
├── airtable-server\           # MCP server para Airtable
│   ├── airtable-mcp-server.js
│   └── package.json
├── phantombuster-server\      # MCP server para Phantombuster
│   ├── phantombuster-mcp-server.js
│   └── package.json
└── README.md                  # Este archivo
```

## 🔧 Servidores Disponibles

### 1. 📊 Airtable MCP Server
**Ubicación:** `airtable-server/`

**Funcionalidades:**
- `airtable_get_records` - Obtener registros de una tabla
- `airtable_update_record` - Actualizar un registro
- `airtable_create_record` - Crear un nuevo registro
- `airtable_search_records` - Buscar registros por campo

### 2. 🚀 Phantombuster MCP Server
**Ubicación:** `phantombuster-server/`

**Funcionalidades:**
- `phantombuster_launch_phantom` - Lanzar un phantom
- `phantombuster_get_container_status` - Estado del container
- `phantombuster_get_containers` - Listar containers
- `phantombuster_get_results` - Obtener resultados
- `phantombuster_get_phantom_info` - Información del phantom

## ⚙️ Instalación

### 1. Instalar dependencias para cada servidor
```bash
# Airtable Server
cd airtable-server
npm install

# Phantombuster Server
cd ../phantombuster-server
npm install
```

### 2. Configurar variables de entorno
```bash
# Airtable
export AIRTABLE_API_KEY="pat_xxxxxxxxxxxxxxxx"
export AIRTABLE_BASE_ID="appxxxxxxxxxxxxxxxx"

# Phantombuster
export PHANTOMBUSTER_API_KEY="your_phantombuster_api_key"
```

### 3. Configurar en Cursor
```json
// .cursor/mcp_servers.json
{
  "mcpServers": {
    "airtable": {
      "command": "node",
      "args": ["C:\\Quantex\\verticals\\mcp_servers\\airtable-server\\airtable-mcp-server.js"],
      "env": {
        "AIRTABLE_API_KEY": "pat_xxxxxxxxxxxxxxxx",
        "AIRTABLE_BASE_ID": "appxxxxxxxxxxxxxxxx"
      }
    },
    "phantombuster": {
      "command": "node",
      "args": ["C:\\Quantex\\verticals\\mcp_servers\\phantombuster-server\\phantombuster-mcp-server.js"],
      "env": {
        "PHANTOMBUSTER_API_KEY": "your_phantombuster_api_key"
      }
    }
  }
}
```

## 📋 Uso

### Airtable
```
Tú: "Get all records from the Prospectos table"
Cursor: [Ejecuta airtable_get_records automáticamente]
```

### Phantombuster
```
Tú: "Launch the LinkedIn Auto Connect phantom with Luis Verdú's profile"
Cursor: [Ejecuta phantombuster_launch_phantom automáticamente]
```

## 🔧 Desarrollo

### Agregar nueva funcionalidad
1. **Editar** el archivo del servidor correspondiente
2. **Agregar** nueva herramienta en `ListToolsRequestSchema`
3. **Implementar** la función en `CallToolRequestSchema`
4. **Reiniciar** Cursor para aplicar cambios

### Estructura de una herramienta
```javascript
{
  name: 'nueva_herramienta',
  description: 'Descripción de la herramienta',
  inputSchema: {
    type: 'object',
    properties: {
      parametro1: {
        type: 'string',
        description: 'Descripción del parámetro'
      }
    },
    required: ['parametro1']
  }
}
```

## 🎯 Beneficios

### ✅ Desarrollo Más Rápido
- **No más código** de integración manual
- **Acceso directo** a APIs desde Cursor
- **Automatización** completa

### ✅ Mantenimiento Fácil
- **Código centralizado** en MCP servers
- **Actualizaciones** en un solo lugar
- **Reutilizable** en otros proyectos

### ✅ Integración Perfecta
- **API específica** para tu proyecto
- **Funciones personalizadas** para tus necesidades
- **Control total** sobre la funcionalidad
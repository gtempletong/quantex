# Guía: Conectar Excel a Supabase usando Power Query (API REST)

## Información de tu proyecto Supabase

- **URL Base:** `https://ikhfknlyhuyygyvoofdu.supabase.co`
- **API Key (Anon):** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGZrbmx5aHV5eWd5dm9vZmR1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUyNDUxMzYsImV4cCI6MjA2MDgyMTEzNn0.pz5y3QWK8xk-yU35Uk42yNQUYaONmslej-FG6STunnk`

## Paso 1: Conectar Excel a Supabase

1. **Abre Excel** y ve a la pestaña **"Datos"**
2. Haz clic en **"Obtener datos"** → **"De otras fuentes"** → **"Desde Web"**
3. En el campo **"URL"**, pega esta URL:

```
https://ikhfknlyhuyygyvoofdu.supabase.co/rest/v1/market_data_ohlcv?ticker=eq.HG=F&select=fecha:timestamp,ticker,precio_cierre:close&order=fecha.desc
```

## Paso 2: Configurar autenticación

1. Después de pegar la URL, haz clic en **"Aceptar"**
2. Excel te pedirá autenticación. Selecciona **"Anónimo"** y haz clic en **"Conectar"**
3. Si no funciona, haz clic en **"Opciones avanzadas"** y agrega estos encabezados:

### Encabezados HTTP:

| Nombre | Valor |
|--------|-------|
| `apikey` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGZrbmx5aHV5eWd5dm9vZmR1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUyNDUxMzYsImV4cCI6MjA2MDgyMTEzNn0.pz5y3QWK8xk-yU35Uk42yNQUYaONmslej-FG6STunnk` |
| `Authorization` | `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGZrbmx5aHV5eWd5dm9vZmR1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUyNDUxMzYsImV4cCI6MjA2MDgyMTEzNn0.pz5y3QWK8xk-yU35Uk42yNQUYaONmslej-FG6STunnk` |
| `Content-Type` | `application/json` |
| `Prefer` | `return=representation` |

## Paso 3: Transformar los datos (Power Query Editor)

1. Excel abrirá el **Editor de Power Query**
2. Si los datos no se ven bien, haz clic derecho en la columna y selecciona **"Cambiar tipo"**:
   - `fecha` → **Fecha/Hora**
   - `precio_cierre` → **Número decimal**
3. Opcional: Renombra las columnas si quieres:
   - `fecha` → **Fecha**
   - `ticker` → **Ticker**
   - `precio_cierre` → **Precio de Cierre**
4. Haz clic en **"Cerrar y cargar"** o **"Cerrar y cargar en..."**

## Paso 4: Crear el gráfico

1. Selecciona los datos importados
2. Ve a **"Insertar"** → **"Gráficos"** → **"Línea"** o **"Dispersión"**
3. Configura el gráfico:
   - **Eje X:** Fecha
   - **Eje Y:** Precio de Cierre

## Paso 5: Actualizar datos automáticamente

1. Haz clic derecho en la tabla de datos
2. Selecciona **"Actualizar"** para obtener datos nuevos
3. Para actualizar automáticamente:
   - Ve a **"Datos"** → **"Consultas y conexiones"**
   - Haz clic derecho en tu consulta → **"Propiedades"**
   - Marca **"Actualizar cada X minutos"** y configura el intervalo

## URL alternativa (si la primera no funciona)

Si la URL con parámetros no funciona, prueba esta versión más simple y luego filtra en Power Query:

```
https://ikhfknlyhuyygyvoofdu.supabase.co/rest/v1/market_data_ohlcv?select=timestamp,ticker,close&ticker=eq.HG=F
```

## Solución de problemas

### Error 401 (No autorizado)
- Verifica que los encabezados `apikey` y `Authorization` estén correctos
- Asegúrate de que la API key no tenga espacios extra

### Error 404 (No encontrado)
- Verifica que la tabla `market_data_ohlcv` existe
- Verifica que el nombre del proyecto en la URL sea correcto

### Los datos no se cargan
- Verifica tu conexión a internet
- Revisa que el formato de la URL sea correcto (sin espacios)

### Paginación (si hay muchos datos)
Si tienes más de 1000 registros, necesitarás paginar. En Power Query Editor:
1. Ve a **"Inicio"** → **"Editor avanzado"**
2. Agrega parámetros de paginación a la URL o usa múltiples consultas

## Nota sobre la vista

La vista `vw_copper_prices` puede no estar accesible directamente vía REST API. Por eso usamos la tabla `market_data_ohlcv` con filtros. Si prefieres usar la vista, prueba:

```
https://ikhfknlyhuyygyvoofdu.supabase.co/rest/v1/vw_copper_prices?select=*
```

Si da error, usa la tabla directamente como se muestra arriba.


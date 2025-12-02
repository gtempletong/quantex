# Guía: Conectar Excel a Supabase

## Problema identificado
El pooler de Supabase requiere un formato específico de usuario que Excel/ODBC puede no reconocer correctamente.

## Solución: Usar usuario `postgres` (no `postgres.ikhfknlyhuyygyvoofdu`)

### Paso 1: Connection String en Excel
```
Driver={PostgreSQL Unicode(x64)};Server=aws-0-us-east-1.pooler.supabase.com;Port=6543;Database=postgres
```

### Paso 2: Credenciales
- **Usuario:** `postgres` (sin el `.ikhfknlyhuyygyvoofdu`)
- **Contraseña:** La contraseña de `SUPABASE_DB_PASSWORD`

### Paso 3: Si sigue fallando - Probar conexión directa

**Connection String:**
```
Driver={PostgreSQL Unicode(x64)};Server=db.ikhfknlyhuyygyvoofdu.supabase.co;Port=5432;Database=postgres
```

**Credenciales:**
- **Usuario:** `postgres`
- **Contraseña:** La contraseña de `SUPABASE_DB_PASSWORD`

## Nota importante
El formato `postgres.ikhfknlyhuyygyvoofdu` es para el pooler cuando se usa desde aplicaciones que lo soportan directamente. Excel/ODBC puede necesitar solo `postgres`.



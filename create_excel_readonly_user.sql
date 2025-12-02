-- Script para crear usuario de solo lectura para Excel
-- Ejecutar en Supabase SQL Editor

-- 1. Crear usuario de solo lectura
CREATE USER excel_readonly WITH PASSWORD 'CambiarPorPasswordSeguro123!';

-- 2. Dar permisos de conexión a la base de datos
GRANT CONNECT ON DATABASE postgres TO excel_readonly;

-- 3. Dar permisos de uso del schema public
GRANT USAGE ON SCHEMA public TO excel_readonly;

-- 4. Dar permisos de SELECT en las tablas necesarias para Excel
-- Tabla principal: precios de cobre (market_data_ohlcv)
GRANT SELECT ON TABLE public.market_data_ohlcv TO excel_readonly;

-- Tabla de definiciones de series (para entender los tickers)
GRANT SELECT ON TABLE public.series_definitions TO excel_readonly;

-- Tabla de series de tiempo (por si necesitas otros datos)
GRANT SELECT ON TABLE public.time_series_data TO excel_readonly;

-- 5. Dar permisos en secuencias (si las hay) para evitar errores
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO excel_readonly;

-- 6. Asegurar permisos en tablas futuras (opcional, para mantenimiento)
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO excel_readonly;

-- Verificar que el usuario fue creado
SELECT usename, usecreatedb, usesuper 
FROM pg_user 
WHERE usename = 'excel_readonly';



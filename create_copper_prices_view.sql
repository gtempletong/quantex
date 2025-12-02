-- Script para crear vista de precios de cobre para Excel
-- Ejecutar en Supabase SQL Editor

-- 1. Crear vista completa con precios de cobre (COMEX, LME, SHFE) e inventarios
DROP VIEW IF EXISTS vw_copper_prices;

CREATE VIEW vw_copper_prices AS
SELECT 
    p.timestamp AS fecha,
    p.close AS precio_comex,  -- Precio COMEX (HG=F)
    lme_price.value AS precio_lme,  -- Precio LME
    shfe_price.value AS precio_shfe,  -- Precio SHFE
    inv_comex.value AS inventarios_comex,
    inv_lme.value AS inventarios_lme,
    inv_shfe.value AS inventarios_shfe,
    inv_totales.value AS inventarios_totales,
    usdcny.close AS usdcny_forex  -- USD/CNY Forex
FROM public.market_data_ohlcv p
LEFT JOIN public.time_series_data lme_price 
    ON p.timestamp = lme_price.timestamp::date 
    AND lme_price.ticker = 'lme'
LEFT JOIN public.time_series_data shfe_price 
    ON p.timestamp = shfe_price.timestamp::date 
    AND shfe_price.ticker = 'shfe'
LEFT JOIN public.time_series_data inv_comex 
    ON p.timestamp = inv_comex.timestamp::date 
    AND inv_comex.ticker = 'inventarios_comex'
LEFT JOIN public.time_series_data inv_lme 
    ON p.timestamp = inv_lme.timestamp::date 
    AND inv_lme.ticker = 'inventarios_lme'
LEFT JOIN public.time_series_data inv_shfe 
    ON p.timestamp = inv_shfe.timestamp::date 
    AND inv_shfe.ticker = 'inventarios_shfe'
LEFT JOIN public.time_series_data inv_totales 
    ON p.timestamp = inv_totales.timestamp::date 
    AND inv_totales.ticker = 'inventarios_totales'
LEFT JOIN public.market_data_ohlcv usdcny 
    ON p.timestamp = usdcny.timestamp::date 
    AND usdcny.ticker = 'USDCNY.FOREX'
WHERE p.ticker = 'HG=F'  -- Usamos COMEX como base (tiene datos más frecuentes)
ORDER BY p.timestamp DESC;

-- 2. Dar permisos al usuario de solo lectura
GRANT SELECT ON vw_copper_prices TO excel_readonly;

-- 3. Verificar que la vista funciona
SELECT * FROM vw_copper_prices LIMIT 10;

-- Opcional: Si quieres incluir otros tickers de cobre también
-- CREATE OR REPLACE VIEW vw_copper_prices_all AS
-- SELECT 
--     timestamp AS fecha,
--     ticker,
--     CASE 
--         WHEN ticker = 'HG=F' THEN 'COMEX (USD/lb)'
--         WHEN ticker = 'lme' THEN 'LME (USD/tonne)'
--         WHEN ticker = 'shfe' THEN 'SHFE (CNY/tonne)'
--         ELSE ticker
--     END AS mercado,
--     close AS precio_cierre,
--     open AS precio_apertura,
--     high AS precio_maximo,
--     low AS precio_minimo,
--     volume AS volumen
-- FROM public.market_data_ohlcv
-- WHERE ticker IN ('HG=F', 'lme', 'shfe')
-- ORDER BY ticker, timestamp DESC;
-- 
-- GRANT SELECT ON vw_copper_prices_all TO excel_readonly;


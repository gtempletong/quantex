/**
 * Quantex Charts - Versión final funcional
 * Basado en TradingView Lightweight Charts
 */

// Variables globales
let chart = null;
let currentSeries = null;
let overlaySeriesMap = {}; // ticker -> series
let overlayScaleMap = {};  // ticker -> 'left' | 'right'
let scaleUsage = { left: 0, right: 0 }; // reference counts por escala
let currentScaleId = null; // escala de la serie principal
let isLoading = false;
let currentRawData = null; // datos crudos de la serie principal
let overlayRawDataMap = {}; // ticker -> data cruda
let usedColors = new Set(); // colores ya asignados

// Configuración de colores
const colors = {
    primary: '#2196F3',
    secondary: '#FF9800',
    success: '#4CAF50',
    warning: '#FF5722',
    info: '#9C27B0'
};

// Paleta de respaldo para asignación única
const COLOR_PALETTE = [
    '#2196F3', '#FF9800', '#4CAF50', '#9C27B0', '#FF5722',
    '#00BCD4', '#8BC34A', '#E91E63', '#607D8B', '#795548'
];

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Quantex Charts iniciado');
    
    // Verificar que TradingView esté cargado
    if (typeof LightweightCharts === 'undefined') {
        console.error('❌ TradingView Lightweight Charts no está cargado');
        showError('TradingView Lightweight Charts no está cargado. Verifica la conexión a internet.');
        return;
    }
    
    console.log('✅ TradingView Lightweight Charts cargado');
    
    // Crear gráfico
    initializeChart();
    
    // Configurar event listeners
    setupEventListeners();
    
    // Cargar series disponibles
    loadAvailableSeries();
});

/**
 * Inicializar el gráfico de TradingView
 */
function initializeChart() {
    const chartContainer = document.getElementById('chart');
    
    if (!chartContainer) {
        console.error('❌ Contenedor del gráfico no encontrado');
        return;
    }
    
    try {
        console.log('🔧 Creando gráfico...');
        
        // Crear gráfico
        chart = LightweightCharts.createChart(chartContainer, {
            width: chartContainer.clientWidth,
            height: 500,
            layout: {
                backgroundColor: '#ffffff',
                textColor: '#333333',
                fontSize: 12,
                fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
            },
            grid: {
                vertLines: {
                    color: '#f0f0f0',
                    style: LightweightCharts.LineStyle.Solid,
                },
                horzLines: {
                    color: '#f0f0f0',
                    style: LightweightCharts.LineStyle.Solid,
                },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    color: '#2196F3',
                    width: 1,
                    style: LightweightCharts.LineStyle.Solid,
                },
                horzLine: {
                    color: '#2196F3',
                    width: 1,
                    style: LightweightCharts.LineStyle.Solid,
                },
            },
            leftPriceScale: {
                visible: true,
                borderColor: '#cccccc',
                scaleMargins: { top: 0.1, bottom: 0.1 },
            },
            rightPriceScale: {
                borderColor: '#cccccc',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
            timeScale: {
                borderColor: '#cccccc',
                timeVisible: true,
                secondsVisible: false,
            },
            watermark: {
                color: 'rgba(33, 150, 243, 0.1)',
                visible: true,
                text: 'Quantex Charts',
                fontSize: 24,
                fontFamily: 'Segoe UI',
                fontStyle: 'bold',
            },
        });
        
        console.log('✅ Gráfico creado correctamente');
        
        // Redimensionar gráfico
        window.addEventListener('resize', () => {
            if (chart) {
                chart.applyOptions({
                    width: chartContainer.clientWidth,
                });
            }
        });
        
    } catch (error) {
        console.error('❌ Error inicializando gráfico:', error);
        showError('Error inicializando gráfico: ' + error.message);
    }
}

/**
 * Configurar event listeners
 */
function setupEventListeners() {
    const loadBtn = document.getElementById('load-btn');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadSelectedData);
    }
    
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearChart);
    }
    const overlayBtn = document.getElementById('overlay-btn');
    if (overlayBtn) {
        overlayBtn.addEventListener('click', loadSelectedOverlays);
    }
    
    const tickerSelect = document.getElementById('ticker-select');
    if (tickerSelect) {
        tickerSelect.addEventListener('change', function() {
            if (this.value) {
                loadSelectedData();
            }
        });
    }

    // Reaplicar normalización al cambiar radio buttons
    const normRadios = document.querySelectorAll('input[name="norm-mode"]');
    normRadios.forEach(r => r.addEventListener('change', reapplyNormalization));
}

/**
 * Cargar series disponibles
 */
async function loadAvailableSeries() {
    try {
        const response = await fetch('/api/charts/series');
        const result = await response.json();
        
        if (result.success && result.series) {
            const select = document.getElementById('ticker-select');
            const overlaySelect = document.getElementById('overlay-select');
            if (select) {
                select.innerHTML = '<option value="">Seleccionar serie...</option>';
                result.series.forEach(series => {
                    const option = document.createElement('option');
                    option.value = series.ticker;
                    option.textContent = series.ticker;
                    select.appendChild(option);
                });
                console.log(`✅ ${result.series.length} series cargadas`);
            }
            if (overlaySelect) {
                overlaySelect.innerHTML = '';
                result.series.forEach(series => {
                    const option = document.createElement('option');
                    option.value = series.ticker;
                    option.textContent = series.ticker;
                    overlaySelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('❌ Error cargando series:', error);
    }
}

/**
 * Cargar datos de la serie seleccionada
 */
async function loadSelectedData() {
    const tickerSelect = document.getElementById('ticker-select');
    const daysSelect = document.getElementById('days-select');
    
    if (!tickerSelect) {
        showError('No se encontró el selector de serie');
        return;
    }
    if (!tickerSelect.value) {
        showError('Por favor selecciona una serie');
        return;
    }
    
    const ticker = tickerSelect.value;
    const days = daysSelect ? daysSelect.value : '365';
    
    await loadData(ticker, days);
}

/**
 * Cargar datos de una serie específica
 */
async function loadData(ticker, days = '365') {
    if (isLoading) return;
    
    if (!chart) {
        showError('Gráfico no inicializado');
        return;
    }
    
    isLoading = true;
    setLoadingState(true);
    
    try {
        console.log(`🔍 Cargando datos para ${ticker} (${days} días)...`);
        updateInfo('current-series', `Cargando ${ticker}...`);
        
        const response = await fetch(`/api/charts/data/${encodeURIComponent(ticker)}?days=${encodeURIComponent(days)}`);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Error desconocido');
        }
        
        if (!result.data || result.data.length === 0) {
            throw new Error('No se encontraron datos para esta serie');
        }
        
        // Limpiar serie anterior principal
        if (currentSeries) {
            chart.removeSeries(currentSeries);
            if (currentScaleId && scaleUsage[currentScaleId] > 0) {
                scaleUsage[currentScaleId] -= 1;
            }
            currentScaleId = null;
        }
        // No tocar overlays aquí
        
        // Crear nueva serie usando el método correcto
        console.log('🔧 Creando serie de línea...');
        const normMode = getCurrentNormMode();
        // Si hay normalización, usamos una sola escala; si no, asignamos dinámicamente: primera serie 'left', segunda 'right'
        const mainScaleId = (normMode && normMode !== 'none') ? 'right' : getAvailableScaleId();
        const mainColor = pickDistinctColor(ticker);
        currentSeries = chart.addSeries(LightweightCharts.LineSeries, {
            color: mainColor,
            lineWidth: 2,
            title: result.metadata.name || ticker,
            priceScaleId: mainScaleId,
        });
        currentScaleId = mainScaleId;
        scaleUsage[mainScaleId] += 1;
        currentRawData = result.data;
        
        // Establecer datos (aplicando normalización si corresponde)
        console.log('📊 Estableciendo datos...');
        const normalizedData = applyNormalizationIfNeeded(result.data, normMode);
        currentSeries.setData(normalizedData);
        
        // Actualizar información
        updateInfo('current-series', result.metadata.name || ticker);
        updateInfo('data-points', result.data.length);
        updateInfo('last-update', new Date().toLocaleString());
        
        // Ocultar errores
        hideError();
        
        console.log(`✅ Datos cargados: ${result.data.length} puntos`);
        
    } catch (error) {
        console.error(`❌ Error cargando ${ticker}:`, error);
        showError(`Error cargando ${ticker}: ${error.message}`);
        
        // Limpiar información
        updateInfo('current-series', 'Error');
        updateInfo('data-points', '0');
        updateInfo('last-update', '-');
    } finally {
        isLoading = false;
        setLoadingState(false);
    }
}

/**
 * Limpiar el gráfico
 */
function clearChart() {
    if (currentSeries) {
        chart.removeSeries(currentSeries);
        currentSeries = null;
        if (currentScaleId && scaleUsage[currentScaleId] > 0) {
            scaleUsage[currentScaleId] -= 1;
        }
        currentScaleId = null;
    }
    // Remover overlays
    Object.entries(overlaySeriesMap).forEach(([t, s]) => {
        chart.removeSeries(s);
        const sid = overlayScaleMap[t];
        if (sid && scaleUsage[sid] > 0) scaleUsage[sid] -= 1;
    });
    overlaySeriesMap = {};
    overlayScaleMap = {};
    scaleUsage = { left: 0, right: 0 };
    usedColors = new Set();
    
    // Limpiar información
    updateInfo('current-series', 'Ninguna');
    updateInfo('data-points', '0');
    updateInfo('last-update', '-');
    
    // Limpiar selección
    const tickerSelect = document.getElementById('ticker-select');
    if (tickerSelect) {
        tickerSelect.value = '';
    }
    
    // Ocultar errores
    hideError();
    
    console.log('🧹 Gráfico limpiado');
}

/**
 * Obtener color para un ticker específico
 */
function getColorForTicker(ticker) {
    const colorMap = {
        'USDCLP.FOREX': colors.primary,
        'copper': colors.secondary,
        'latam_currency_index': colors.success,
        'shfe': colors.warning,
        'lme': colors.info,
        'USDMXN.FOREX': '#1f77b4',
        'USDBRL.FOREX': '#ff7f0e',
        'USDCOP.FOREX': '#2ca02c',
        'USDPEN.FOREX': '#d62728',
    };
    
    return colorMap[ticker] || colors.primary;
}

/**
 * Normalización de datos
 */
function applyNormalizationIfNeeded(data, mode) {
    if (!data || data.length === 0) return data;
    if (!mode || mode === 'none') return data;
    const values = data.map(d => d.value);
    const first = values[0];
    if (first === 0) return data;
    if (mode === 'base100') {
        return data.map(d => ({ time: d.time, value: (d.value / first) * 100 }));
    }
    if (mode === 'pct') {
        return data.map(d => ({ time: d.time, value: ((d.value / first) - 1) * 100 }));
    }
    return data;
}

function getCurrentNormMode() {
    return document.querySelector('input[name="norm-mode"]:checked')?.value || 'none';
}

/**
 * Cargar overlays seleccionados
 */
async function loadSelectedOverlays() {
    const overlaySelect = document.getElementById('overlay-select');
    const daysSelect = document.getElementById('days-select');
    const normMode = document.querySelector('input[name="norm-mode"]:checked')?.value || 'none';
    if (!overlaySelect) return;

    const selected = Array.from(overlaySelect.selectedOptions).map(o => o.value).filter(Boolean);
    if (selected.length === 0) return;

    // Llamar batch
    const days = daysSelect ? daysSelect.value : '365';
    const url = `/api/charts/batch?tickers=${encodeURIComponent(selected.join(','))}&days=${days}`;
    try {
        const resp = await fetch(url);
        const json = await resp.json();
        if (!json.success) throw new Error(json.error || 'Error batch');

        // Crear o actualizar series overlays
        for (const t of selected) {
            const entry = json.series[t];
            if (!entry || !entry.data) continue;
            const color = pickDistinctColor(t);
            const desiredScale = (normMode && normMode !== 'none') ? 'right' : getAvailableScaleId();
            if (overlaySeriesMap[t]) {
                // actualizar
                overlaySeriesMap[t].setData(applyNormalizationIfNeeded(entry.data, normMode));
                // Si cambió el modo de normalización, puede que debamos mover la serie a otra escala
                const prev = overlayScaleMap[t];
                const next = desiredScale;
                if (prev !== next) {
                    overlaySeriesMap[t].applyOptions({ priceScaleId: next });
                    if (prev && scaleUsage[prev] > 0) scaleUsage[prev] -= 1;
                    scaleUsage[next] += 1;
                    overlayScaleMap[t] = next;
                }
                overlayRawDataMap[t] = entry.data;
            } else {
                const s = chart.addSeries(LightweightCharts.LineSeries, { color, lineWidth: 1.5, title: t, priceScaleId: desiredScale });
                s.setData(applyNormalizationIfNeeded(entry.data, normMode));
                overlaySeriesMap[t] = s;
                overlayScaleMap[t] = desiredScale;
                scaleUsage[desiredScale] += 1;
                overlayRawDataMap[t] = entry.data;
            }
        }
        console.log(`✅ Overlays cargados: ${selected.join(', ')}`);
    } catch (e) {
        showError('Error cargando overlays: ' + e.message);
    }
}

/**
 * Preset LATAM: índice + monedas
 */
// presetLatamSet eliminado por solicitud

/**
 * Asignar ejes/precio scale por ticker para múltiples ejes
 * Referencia: Lightweight Charts v5 agrega soporte de múltiples paneles/escala.
 * Doc: https://tradingview.github.io/lightweight-charts/ (v5) [API reference]
 */
function getPriceScaleForTicker(ticker) {
    // Ejemplo: índice LATAM a la izquierda, monedas a la derecha
    if (ticker === 'latam_currency_index') return 'left';
    return 'right';
}

// Obtener próxima escala disponible respetando límite de 2 ejes por pane
function getAvailableScaleId() {
    if (scaleUsage.left === 0) return 'left';
    if (scaleUsage.right === 0) return 'right';
    // Si ambas están ocupadas, por simplicidad reutilizamos la derecha
    return 'right';
}

// Elegir color sin repetir lo ya usado, con fallback a paleta
function pickDistinctColor(ticker) {
    // Primero, si hay un color preasignado por ticker
    const predefined = getColorForTicker(ticker);
    if (!usedColors.has(predefined)) {
        usedColors.add(predefined);
        return predefined;
    }
    // Buscar en la paleta uno libre
    for (const c of COLOR_PALETTE) {
        if (!usedColors.has(c)) {
            usedColors.add(c);
            return c;
        }
    }
    // Último recurso: genera variación simple
    const fallback = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6,'0');
    usedColors.add(fallback);
    return fallback;
}

// Reaplicar normalización al cambiar radios sin recargar datos
function reapplyNormalization() {
    try {
        const mode = getCurrentNormMode();
        // Serie principal
        if (currentSeries && Array.isArray(currentRawData)) {
            const normalized = applyNormalizationIfNeeded(currentRawData, mode);
            currentSeries.setData(normalized);
            if (mode && mode !== 'none') {
                currentSeries.applyOptions({ priceScaleId: 'right' });
            }
        }
        // Overlays
        for (const [t, s] of Object.entries(overlaySeriesMap)) {
            const raw = overlayRawDataMap[t];
            if (!raw) continue;
            const normalized = applyNormalizationIfNeeded(raw, mode);
            s.setData(normalized);
            if (mode && mode !== 'none') {
                s.applyOptions({ priceScaleId: 'right' });
            }
        }
    } catch (e) {
        console.error('❌ Error reaplicando normalización:', e);
    }
}

/**
 * Actualizar información en la interfaz
 */
function updateInfo(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Mostrar error
 */
function showError(message) {
    const errorLog = document.getElementById('error-log');
    const errorContent = document.getElementById('error-content');
    
    if (errorLog && errorContent) {
        errorContent.textContent = message;
        errorLog.style.display = 'block';
    }
    
    console.error('❌ Error:', message);
}

/**
 * Ocultar error
 */
function hideError() {
    const errorLog = document.getElementById('error-log');
    if (errorLog) {
        errorLog.style.display = 'none';
    }
}

/**
 * Establecer estado de carga
 */
function setLoadingState(loading) {
    const loadBtn = document.getElementById('load-btn');
    const container = document.querySelector('.container');
    
    if (loadBtn) {
        loadBtn.disabled = loading;
        loadBtn.textContent = loading ? 'Cargando...' : 'Cargar Datos';
    }
    
    if (container) {
        if (loading) {
            container.classList.add('loading');
        } else {
            container.classList.remove('loading');
        }
    }
}

/**
 * Utilidades para debugging
 */
window.QuantexCharts = {
    chart: () => chart,
    currentSeries: () => currentSeries,
    loadData: loadData,
    clearChart: clearChart,
    showError: showError,
    hideError: hideError,
    LightweightCharts: () => LightweightCharts
};

console.log('📊 Quantex Charts JavaScript cargado');
console.log('🔧 Utilidades disponibles en window.QuantexCharts');


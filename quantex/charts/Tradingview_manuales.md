## Manual TradingView (Lightweight Charts)

- Documentación principal: [Lightweight Charts Docs](https://tradingview.github.io/lightweight-charts/)
- API Reference: [API Overview](https://tradingview.github.io/lightweight-charts/docs/api)
- Crear gráfico: [createChart](https://tradingview.github.io/lightweight-charts/docs/api/classes/ichartapi#functions-create-chart)
- Series (líneas y más): [LineSeries](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/lineseries)
- Opciones de series: [Series Options](https://tradingview.github.io/lightweight-charts/docs/api#series-options)
- Escalas de precio y múltiples ejes: [Price Scale](https://tradingview.github.io/lightweight-charts/docs/api/classes/ipricescaleapi)
- Eje de tiempo: [Time Scale](https://tradingview.github.io/lightweight-charts/docs/api/classes/itimescaleapi)
- Crosshair, grid y layout: [Chart Options](https://tradingview.github.io/lightweight-charts/docs/api#chart-options)
- Ejemplos oficiales: [Examples Gallery](https://tradingview.github.io/lightweight-charts/docs#examples)
- Preguntas frecuentes: [FAQ](https://tradingview.github.io/lightweight-charts/docs/faq)
 
### Setup rápido

```html
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<div id="chart" style="width:100%;height:400px"></div>
<script>
  const chart = LightweightCharts.createChart(document.getElementById('chart'), {
    layout: { background: { type: 'solid', color: '#fff' }, textColor: '#222' },
    grid: { vertLines: { color: '#eee' }, horzLines: { color: '#eee' } },
    timeScale: { borderColor: '#ccc' },
    rightPriceScale: { borderColor: '#ccc' }
  });
  const series = chart.addLineSeries({ color: '#2196F3', lineWidth: 2 });
  // series.setData([{ time: '2024-01-01', value: 100 }, ...])
</script>
```

### Formato de datos

```javascript
// Line series
[{ time: 'YYYY-MM-DD', value: 101.25 }]

// Candlestick
[{ time: 'YYYY-MM-DD', open: 100, high: 105, low: 99, close: 104 }]
```

### Múltiples series y múltiples ejes

```javascript
const left = chart.addLineSeries({ color: '#4CAF50', priceScaleId: 'left' });
const right = chart.addLineSeries({ color: '#FF9800', priceScaleId: 'right' });
// Normalización (Base 100 / % cambio) → use una sola escala para comparabilidad:
// left.applyOptions({ priceScaleId: 'right' }); right.applyOptions({ priceScaleId: 'right' });
```

### Buenas prácticas

- Use ResizeObserver o un handler de window.resize para `applyOptions({ width })`.
- `time` en ISO (YYYY-MM-DD) para día; epoch seconds para intradía.
- Prefiera `setData` para carga inicial y `update` para ticks nuevos.
- Revise DPI/HiDPI: contenedor con width/height reales, no solo CSS.
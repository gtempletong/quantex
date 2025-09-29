#!/usr/bin/env python3
"""
Quantex Charts - Aplicación Flask para visualización de datos financieros
"""

import os
import sys
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Asegurar que el root del proyecto (C:\Quantex) esté en PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from quantex.core.database_manager import supabase
from quantex.core.data_fetcher import get_data_series
# Config inline
load_dotenv()

class Config:
    """Configuración de Quantex Charts (inline)"""
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # Servidor
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5002))

    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

    # CORS
    CORS_ORIGINS = ['http://localhost:5001', 'http://localhost:5002']

from datetime import datetime, timedelta

# Configuración
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})  # Habilitar CORS según config

# Variables de entorno via Config
PORT = Config.PORT
HOST = Config.HOST
def _fetch_fixed_income_points_by_ticker(token: str, days: int) -> dict | None:
    """
    Busca renta fija en fixed_income_definitions:
      1) por ticker == token
      2) si no existe, por name ilike '%token%'
    y devuelve puntos {time, value} desde fixed_income_trades (average_yield) por instrument_id.
    Devuelve dict {'data': [...], 'last_update': '...'} o None si no hay datos.
    """
    try:
        # 1) Intentar resolver instrument_id desde definiciones por ticker (exacto o ilike)
        instrument_id = None
        instrument_name = None
        try:
            def_res = (
                supabase
                .table('fixed_income_definitions')
                .select('id,name,ticker')
                .eq('ticker', token)
                .maybe_single()
                .execute()
            )
            if def_res and def_res.data:
                instrument_id = def_res.data.get('id')
                instrument_name = def_res.data.get('name')
        except Exception:
            pass

        if not instrument_id:
            try:
                def_res = (
                    supabase
                    .table('fixed_income_definitions')
                    .select('id,name,ticker')
                    .ilike('ticker', f"%{token}%")
                    .maybe_single()
                    .execute()
                )
                if def_res and def_res.data:
                    instrument_id = def_res.data.get('id')
                    instrument_name = def_res.data.get('name')
            except Exception:
                pass

        start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

        # 2) Recuperar trades con la mayor tolerancia posible de columnas
        def fetch_trades_by(filters: dict) -> list[dict]:
            try:
                sel = 'trade_date,date,timestamp,average_yield,yield,rate,instrument_id,instrument_name,ticker'
                q = supabase.table('fixed_income_trades').select(sel)
                for k, v in filters.items():
                    q = q.eq(k, v)
                # Filtro por fecha si existe alguna columna de fecha
                # Intentar en orden de probabilidad
                rows = q.execute().data or []
                # Filtrar por rango de fechas a mano (tolerando nombre de columna)
                out = []
                for r in rows:
                    td = r.get('trade_date') or r.get('date') or r.get('timestamp')
                    if not td:
                        continue
                    if isinstance(td, str):
                        dt_str = td[:10]
                    else:
                        dt_str = str(td)[:10]
                    if dt_str >= start_date:
                        out.append(r)
                # Ordenar por fecha ascendente
                out.sort(key=lambda r: (r.get('trade_date') or r.get('date') or r.get('timestamp') or ''))
                return out
            except Exception:
                return []

        candidate_rows = fetch_trades_by({'ticker': token})
        if not candidate_rows and instrument_id:
            candidate_rows = fetch_trades_by({'instrument_id': instrument_id})

        data_points = []
        for r in candidate_rows:
            td = r.get('trade_date') or r.get('date') or r.get('timestamp')
            val = r.get('average_yield')
            if val is None:
                val = r.get('yield') if 'yield' in r else r.get('rate')
            if td is None or val is None:
                continue
            # Normalizar fecha a YYYY-MM-DD
            t_str = td if isinstance(td, str) else str(td)
            t_str = t_str[:10]
            try:
                data_points.append({'time': t_str, 'value': float(val)})
            except Exception:
                continue

        if not data_points:
            return None

        last_update = data_points[-1]['time']
        return {'data': data_points, 'last_update': last_update}
    except Exception:
        return None


@app.route('/')
def index():
    """Página principal con gráficos"""
    return render_template('charts.html')

@app.route('/health')
def health():
    """Endpoint de salud para verificar que el servidor está corriendo"""
    return jsonify({
        'status': 'healthy',
        'service': 'quantex-charts',
        'version': '1.0.0'
    })

@app.route('/api/charts/series')
def get_available_series():
    """Obtener lista de series disponibles"""
    try:
        # Paso a paso: series_definitions + instrument_definitions, SOLO ticker
        tickers = []
        try:
            page_size = 1000
            offset = 0
            while True:
                resp = supabase.table('series_definitions').select('ticker').range(offset, offset + page_size - 1).execute()
                rows = resp.data or []
                if not rows:
                    break
                for r in rows:
                    t = r.get('ticker')
                    if t:
                        tickers.append({'ticker': t})
                if len(rows) < page_size:
                    break
                offset += page_size
        except Exception:
            tickers = []

        # instrument_definitions (ticker OHLCV)
        try:
            page_size = 1000
            offset = 0
            while True:
                resp = supabase.table('instrument_definitions').select('ticker').range(offset, offset + page_size - 1).execute()
                rows = resp.data or []
                if not rows:
                    break
                for r in rows:
                    t = r.get('ticker')
                    if t:
                        tickers.append({'ticker': t})
                if len(rows) < page_size:
                    break
                offset += page_size
        except Exception:
            pass

        # fixed_income_definitions (usar 'ticker' real como identificador de serie)
        try:
            page_size = 1000
            offset = 0
            while True:
                resp = supabase.table('fixed_income_definitions').select('ticker').range(offset, offset + page_size - 1).execute()
                rows = resp.data or []
                if not rows:
                    break
                for r in rows:
                    t = r.get('ticker')
                    if t:
                        tickers.append({'ticker': t})
                if len(rows) < page_size:
                    break
                offset += page_size
        except Exception:
            pass

        # Dedupe por ticker
        uniq = {}
        for item in tickers:
            t = item.get('ticker')
            if t and t not in uniq:
                uniq[t] = {'ticker': t}

        result = sorted(uniq.values(), key=lambda x: (x.get('ticker') or '').lower())
        return jsonify({'success': True, 'total': len(result), 'series': result})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo series: {str(e)}'
        }), 500

@app.route('/api/charts/data/<ticker>')
def get_series_data(ticker):
    """Obtener datos de una serie específica"""
    try:
        # Obtener parámetros de query
        days = int(request.args.get('days', 365))
        
        # Usar el buscador universal de Quantex
        df = get_data_series(ticker, days=days)
        
        # Fallback: si no hay datos, intentar renta fija por ticker (luego instrument_id por definiciones)
        if df is None or df.empty:
            fi = _fetch_fixed_income_points_by_ticker(ticker, days)
            if fi and fi.get('data'):
                metadata = {
                    'ticker': ticker,
                    'name': ticker,
                    'unit': 'percentage',
                    'source': 'fixed_income_trades',
                    'last_update': f"{fi['last_update']}T00:00:00Z"
                }
                return jsonify({'success': True, 'ticker': ticker, 'data': fi['data'], 'metadata': metadata})
            else:
                return jsonify({'success': False, 'error': f'No se encontraron datos para {ticker}'}), 404
        
        # Convertir a formato TradingView
        data = []
        for timestamp, row in df.iterrows():
            data.append({
                'time': timestamp.strftime('%Y-%m-%d'),
                'value': float(row['close']) if 'close' in row else float(row['value'])
            })
        
        # Obtener metadatos
        metadata = {
            'ticker': ticker,
            'name': ticker,
            'unit': 'CLP',
            'source': 'quantex',
            'last_update': df.index[-1].strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        return jsonify({
            'success': True,
            'ticker': ticker,
            'data': data,
            'metadata': metadata
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo datos: {str(e)}'
        }), 500

@app.route('/api/charts/batch')
def get_batch_data():
    """Obtener datos de múltiples series"""
    try:
        tickers = request.args.get('tickers', '').split(',')
        days = int(request.args.get('days', 365))
        
        if not tickers or tickers == ['']:
            return jsonify({
                'success': False,
                'error': 'Parámetro tickers requerido'
            }), 400
        
        results = {}
        
        for ticker in tickers:
            ticker = ticker.strip()
            if not ticker:
                continue
                
            try:
                df = get_data_series(ticker, days=days)
                
                if df is not None and not df.empty:
                    data = []
                    for timestamp, row in df.iterrows():
                        data.append({
                            'time': timestamp.strftime('%Y-%m-%d'),
                            'value': float(row['close']) if 'close' in row else float(row['value'])
                        })
                    
                    results[ticker] = {
                        'data': data,
                        'metadata': {
                            'ticker': ticker,
                            'name': ticker,
                            'unit': 'CLP',
                            'source': 'quantex',
                            'last_update': df.index[-1].strftime('%Y-%m-%dT%H:%M:%SZ')
                        }
                    }
                else:
                    # Fallback renta fija por ticker (luego instrument_id por definiciones)
                    fi = _fetch_fixed_income_points_by_ticker(ticker, days)
                    if fi and fi.get('data'):
                        results[ticker] = {
                            'data': fi['data'],
                            'metadata': {
                                'ticker': ticker,
                                'name': ticker,
                                'unit': 'percentage',
                                'source': 'fixed_income_trades',
                                'last_update': f"{fi['last_update']}T00:00:00Z"
                            }
                        }
                    else:
                        results[ticker] = {'error': f'No se encontraron datos para {ticker}'}
                    
            except Exception as e:
                results[ticker] = {
                    'error': f'Error obteniendo {ticker}: {str(e)}'
                }
        
        return jsonify({
            'success': True,
            'series': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo datos batch: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Manejar errores 404"""
    return jsonify({
        'success': False,
        'error': 'Endpoint no encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejar errores 500"""
    return jsonify({
        'success': False,
        'error': 'Error interno del servidor'
    }), 500

if __name__ == '__main__':
    print("🚀 Iniciando Quantex Charts...")
    print(f"   Puerto: {PORT}")
    print(f"   Host: {HOST}")
    print(f"   Debug: {app.config['DEBUG']}")
    print(f"   URL: http://{HOST}:{PORT}")
    
    app.run(
        host=HOST,
        port=PORT,
        debug=app.config['DEBUG']
    )

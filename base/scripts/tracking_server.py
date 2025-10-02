#!/usr/bin/env python3
"""
Servidor de tracking para emails - Recibe pings del pixel invisible
Reemplaza funcionalidad de Brevo para tracking de apertura de emails
"""

import os
import sys
import json
import base64
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from PIL import Image
import io

# Configuración de rutas
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

from quantex.core.database_manager import supabase

app = Flask(__name__)

# Cache simple para emails por tracking_id (en producción usar Redis)
email_cache = {}

def create_transparent_pixel():
    """Crear imagen 1x1 transparente para tracking"""
    img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))  # Transparente
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

# Crear pixel una sola vez
TRANSPARENT_PIXEL = create_transparent_pixel()

def detect_email_client(user_agent):
    """Detectar qué cliente de email está usando"""
    if not user_agent:
        return 'Unknown'
    
    user_agent_lower = user_agent.lower()
    
    if 'outlook' in user_agent_lower:
        return 'Outlook'
    elif 'thunderbird' in user_agent_lower:
        return 'Thunderbird'
    elif 'apple mail' in user_agent_lower:
        return 'Apple Mail'
    elif 'gmail' in user_agent_lower:
        return 'Gmail'
    elif 'yahoo' in user_agent_lower:
        return 'Yahoo Mail'
    elif 'aol' in user_agent_lower:
        return 'AOL Mail'
    elif 'mozilla' in user_agent_lower:
        return 'Mozilla'
    else:
        return 'Unknown'

def get_email_by_tracking_id(tracking_id):
    """Obtener email asociado a un tracking_id desde cache o Supabase"""
    if tracking_id in email_cache:
        return email_cache[tracking_id]
    
    try:
        # Buscar en Supabase
        result = supabase.table('interactions').select('email').eq('tracking_id', tracking_id).eq('interaction_type', 'email_sent').limit(1).execute()
        
        if result.data:
            email = result.data[0]['email']
            email_cache[tracking_id] = email
            return email
    except Exception as e:
        print(f"❌ Error obteniendo email para tracking_id {tracking_id}: {e}")
    
    return None

@app.route('/track/<tracking_id>')
def track_email_open(tracking_id):
    """
    Endpoint principal para tracking de apertura de emails
    Se llama automáticamente cuando el pixel se carga
    """
    try:
        # Obtener email asociado al tracking_id
        email = get_email_by_tracking_id(tracking_id)
        
        if not email:
            print(f"⚠️ Tracking ID no encontrado: {tracking_id}")
            # Devolver pixel igual para no romper el email
            return send_file(io.BytesIO(TRANSPARENT_PIXEL), mimetype='image/png')
        
        # Recopilar datos del request
        tracking_data = {
            'email': email,
            'interaction_type': 'email_opened',
            'tracking_id': tracking_id,
            'detail': json.dumps({
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'email_client': detect_email_client(request.headers.get('User-Agent')),
                'referer': request.headers.get('Referer'),
                'timestamp': datetime.now().isoformat(),
                'source': 'gmail_api'
            })
        }
        
        # Insertar en Supabase
        result = supabase.table('interactions').insert(tracking_data).execute()
        
        if result.data:
            print(f"✅ Email abierto registrado: {email} - Tracking ID: {tracking_id}")
        else:
            print(f"❌ Error insertando tracking para {email}")
        
        # Devolver imagen 1x1 transparente
        return send_file(io.BytesIO(TRANSPARENT_PIXEL), mimetype='image/png')
        
    except Exception as e:
        print(f"❌ Error en tracking: {e}")
        # Devolver pixel igual para no romper el email
        return send_file(io.BytesIO(TRANSPARENT_PIXEL), mimetype='image/png')

@app.route('/stats/<tracking_id>')
def get_tracking_stats(tracking_id):
    """Ver estadísticas de un tracking_id específico"""
    try:
        # Buscar todos los eventos para este tracking_id
        result = supabase.table('interactions').select('*').eq('tracking_id', tracking_id).order('created_at').execute()
        
        if not result.data:
            return jsonify({"error": "Tracking ID no encontrado"}), 404
        
        events = result.data
        email = events[0]['email'] if events else 'Unknown'
        
        # Contar eventos
        sent_count = len([e for e in events if e['interaction_type'] == 'email_sent'])
        opened_count = len([e for e in events if e['interaction_type'] == 'email_opened'])
        
        stats = {
            'tracking_id': tracking_id,
            'email': email,
            'events': {
                'sent': sent_count,
                'opened': opened_count,
                'open_rate': opened_count / sent_count if sent_count > 0 else 0
            },
            'timeline': events
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats/email/<email>')
def get_email_stats(email):
    """Ver estadísticas de un email específico"""
    try:
        # Buscar todos los eventos para este email
        result = supabase.table('interactions').select('*').eq('email', email).order('created_at', desc=True).execute()
        
        if not result.data:
            return jsonify({"error": "Email no encontrado"}), 404
        
        events = result.data
        
        # Contar eventos por tipo
        event_counts = {}
        for event in events:
            event_type = event['interaction_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Calcular tasa de apertura
        sent_count = event_counts.get('email_sent', 0)
        opened_count = event_counts.get('email_opened', 0)
        
        stats = {
            'email': email,
            'total_events': len(events),
            'event_counts': event_counts,
            'open_rate': opened_count / sent_count if sent_count > 0 else 0,
            'recent_events': events[:10]  # Últimos 10 eventos
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Health check del servidor"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "supabase_connected": supabase is not None
    })

@app.route('/')
def index():
    """Página de inicio del servidor"""
    return """
    <h1>Quantex Email Tracking Server</h1>
    <p>Servidor de tracking para emails - Reemplazo de Brevo</p>
    <h2>Endpoints disponibles:</h2>
    <ul>
        <li><code>/track/&lt;tracking_id&gt;</code> - Tracking de apertura (pixel)</li>
        <li><code>/stats/&lt;tracking_id&gt;</code> - Estadísticas por tracking ID</li>
        <li><code>/stats/email/&lt;email&gt;</code> - Estadísticas por email</li>
        <li><code>/health</code> - Health check</li>
    </ul>
    """

if __name__ == '__main__':
    print("🚀 Iniciando servidor de tracking de emails...")
    print("📊 Endpoints disponibles:")
    print("   - /track/<tracking_id> - Tracking de apertura")
    print("   - /stats/<tracking_id> - Estadísticas por tracking ID")
    print("   - /stats/email/<email> - Estadísticas por email")
    print("   - /health - Health check")
    print("")
    print("🌐 Servidor ejecutándose en: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

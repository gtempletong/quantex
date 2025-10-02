#!/usr/bin/env python3
"""
Script para consultar estadísticas de emails enviados
Reemplaza funcionalidad de reportes de Brevo
"""

import os
import sys
import argparse
import requests
import json
from datetime import datetime, timedelta

# Configuración de rutas
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

from quantex.core.database_manager import supabase

# URL del servidor de tracking
TRACKING_SERVER_URL = os.getenv('TRACKING_SERVER_URL', 'http://localhost:5000')

def get_email_stats_from_supabase(email=None, days_back=7):
    """Obtener estadísticas directamente de Supabase"""
    try:
        # Construir query
        query = supabase.table('interactions').select('*')
        
        if email:
            query = query.eq('email', email)
        
        # Filtrar por días
        since_date = datetime.now() - timedelta(days=days_back)
        query = query.gte('created_at', since_date.isoformat())
        
        result = query.order('created_at', desc=True).execute()
        
        if not result.data:
            return {"error": "No se encontraron datos"}
        
        events = result.data
        
        # Procesar estadísticas
        stats = {
            'period': f"{days_back} días",
            'total_events': len(events),
            'emails': {},
            'summary': {
                'total_sent': 0,
                'total_opened': 0,
                'unique_emails': set(),
                'unique_tracking_ids': set()
            }
        }
        
        for event in events:
            email_addr = event['email']
            tracking_id = event['tracking_id']
            event_type = event['interaction_type']
            
            # Inicializar email si no existe
            if email_addr not in stats['emails']:
                stats['emails'][email_addr] = {
                    'sent': 0,
                    'opened': 0,
                    'tracking_ids': set(),
                    'events': []
                }
            
            # Contar eventos
            if event_type == 'email_sent':
                stats['emails'][email_addr]['sent'] += 1
                stats['summary']['total_sent'] += 1
            elif event_type == 'email_opened':
                stats['emails'][email_addr]['opened'] += 1
                stats['summary']['total_opened'] += 1
            
            # Agregar tracking_id
            stats['emails'][email_addr]['tracking_ids'].add(tracking_id)
            stats['summary']['unique_emails'].add(email_addr)
            stats['summary']['unique_tracking_ids'].add(tracking_id)
            
            # Agregar evento
            stats['emails'][email_addr]['events'].append(event)
        
        # Calcular tasas de apertura
        for email_addr in stats['emails']:
            email_data = stats['emails'][email_addr]
            email_data['open_rate'] = email_data['opened'] / email_data['sent'] if email_data['sent'] > 0 else 0
            email_data['tracking_ids'] = list(email_data['tracking_ids'])
        
        # Convertir sets a listas para JSON
        stats['summary']['unique_emails'] = list(stats['summary']['unique_emails'])
        stats['summary']['unique_tracking_ids'] = list(stats['summary']['unique_tracking_ids'])
        stats['summary']['overall_open_rate'] = stats['summary']['total_opened'] / stats['summary']['total_sent'] if stats['summary']['total_sent'] > 0 else 0
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}

def get_tracking_stats_from_server(tracking_id):
    """Obtener estadísticas de un tracking_id específico desde el servidor"""
    try:
        response = requests.get(f"{TRACKING_SERVER_URL}/stats/{tracking_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error del servidor: {response.status_code}"}
    except Exception as e:
        return {"error": f"Error conectando con servidor: {e}"}

def get_email_stats_from_server(email):
    """Obtener estadísticas de un email específico desde el servidor"""
    try:
        response = requests.get(f"{TRACKING_SERVER_URL}/stats/email/{email}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error del servidor: {response.status_code}"}
    except Exception as e:
        return {"error": f"Error conectando con servidor: {e}"}

def print_stats(stats, title="Estadísticas de Emails"):
    """Imprimir estadísticas de forma legible"""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print(f"{'='*60}")
    
    if 'error' in stats:
        print(f"❌ Error: {stats['error']}")
        return
    
    # Resumen general
    if 'summary' in stats:
        summary = stats['summary']
        print(f"\n📈 RESUMEN GENERAL ({stats.get('period', 'N/A')}):")
        print(f"   📧 Emails únicos: {len(summary['unique_emails'])}")
        print(f"   📬 Total enviados: {summary['total_sent']}")
        print(f"   👁️  Total abiertos: {summary['total_opened']}")
        print(f"   📊 Tasa de apertura: {summary['overall_open_rate']:.2%}")
    
    # Detalle por email
    if 'emails' in stats:
        print(f"\n📧 DETALLE POR EMAIL:")
        for email, data in stats['emails'].items():
            print(f"\n   📮 {email}:")
            print(f"      📤 Enviados: {data['sent']}")
            print(f"      👁️  Abiertos: {data['opened']}")
            print(f"      📊 Tasa: {data['open_rate']:.2%}")
            print(f"      🆔 Tracking IDs: {len(data['tracking_ids'])}")

def main():
    """CLI principal para estadísticas de emails"""
    parser = argparse.ArgumentParser(description='Estadísticas de emails - Reemplazo de Brevo')
    parser.add_argument('--email', '-e', help='Email específico para consultar')
    parser.add_argument('--tracking-id', '-t', help='Tracking ID específico para consultar')
    parser.add_argument('--days', '-d', type=int, default=7, help='Días hacia atrás (default: 7)')
    parser.add_argument('--server', '-s', action='store_true', help='Usar servidor de tracking en lugar de Supabase directo')
    parser.add_argument('--json', '-j', action='store_true', help='Output en formato JSON')
    
    args = parser.parse_args()
    
    try:
        if args.tracking_id:
            # Estadísticas de tracking ID específico
            if args.server:
                stats = get_tracking_stats_from_server(args.tracking_id)
            else:
                # Buscar en Supabase directamente
                result = supabase.table('interactions').select('*').eq('tracking_id', args.tracking_id).order('created_at').execute()
                if result.data:
                    stats = {
                        'tracking_id': args.tracking_id,
                        'events': result.data,
                        'email': result.data[0]['email'] if result.data else 'Unknown'
                    }
                else:
                    stats = {"error": "Tracking ID no encontrado"}
            
            title = f"Estadísticas para Tracking ID: {args.tracking_id}"
            
        elif args.email:
            # Estadísticas de email específico
            if args.server:
                stats = get_email_stats_from_server(args.email)
            else:
                stats = get_email_stats_from_supabase(args.email, args.days)
            
            title = f"Estadísticas para Email: {args.email}"
            
        else:
            # Estadísticas generales
            stats = get_email_stats_from_supabase(days_back=args.days)
            title = f"Estadísticas Generales ({args.days} días)"
        
        # Output
        if args.json:
            print(json.dumps(stats, indent=2, default=str))
        else:
            print_stats(stats, title)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

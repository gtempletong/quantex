#!/usr/bin/env python3
"""
Script standalone para enviar reportes por email (ENVÍO MASIVO).
Se ejecuta desde Next.js vía subprocess.
No requiere servidor Flask.

⚠️ IMPORTANTE: Este script envía SOLO emails en TEXTO PLANO (sin HTML)
para evitar filtros de spam y mejorar el deliverability.

Uso:
    python send_report_emails.py
    
Lee JSON desde stdin:
    {
        "recipients": ["email1@domain.com", "email2@domain.com"],
        "report_topic": "clp"
    }
    
Imprime JSON a stdout:
    {
        "success": true,
        "successful_sends": 2,
        "failed_sends": 0,
        "results": [...]
    }
"""

import sys
import json
import base64
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path
import os

# El script está en: C:\quantex\quantex\scripts\send_report_emails.py
# Para hacer "import quantex", necesitamos que C:\quantex esté en sys.path
# __file__ = C:\quantex\quantex\scripts\send_report_emails.py
# dirname(__file__) = C:\quantex\quantex\scripts
# dirname(dirname(__file__)) = C:\quantex\quantex
# dirname(dirname(dirname(__file__))) = C:\quantex ← Este es el que necesitamos
script_dir = os.path.dirname(os.path.abspath(__file__))  # C:\quantex\quantex\scripts
quantex_package_dir = os.path.dirname(script_dir)        # C:\quantex\quantex
project_root = os.path.dirname(quantex_package_dir)      # C:\quantex

# Añadir C:\quantex al sys.path para que "import quantex" funcione
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Cambiar al directorio raíz del proyecto para que las rutas relativas funcionen
os.chdir(project_root)

from quantex.core.agents.modular_agent.gmail_send_tool import send_email
from quantex.core import database_manager as db


def main():
    """Función principal del script."""
    try:
        # 1. Leer JSON desde stdin
        input_data = json.loads(sys.stdin.read())
        recipients = input_data.get('recipients', [])
        report_topic = input_data.get('report_topic', '')
        custom_subject = input_data.get('subject', '')
        custom_body = input_data.get('body', '')
        attach_report_clp = input_data.get('attach_report_clp', False)
        attach_report_copper = input_data.get('attach_report_copper', False)
        
        if not recipients:
            print(json.dumps({'success': False, 'error': 'No se proporcionaron destinatarios'}))
            sys.exit(1)
        
        if not report_topic:
            print(json.dumps({'success': False, 'error': 'No se proporcionó report_topic'}))
            sys.exit(1)
        
        print(f"📧 Enviando reporte '{report_topic}' a {len(recipients)} destinatarios...", file=sys.stderr)
        
        # 2. Obtener último reporte de Supabase
        latest_report = db.get_latest_report(report_keyword=report_topic)
        if not latest_report:
            print(json.dumps({'success': False, 'error': f'No se encontró reporte para "{report_topic}"'}))
            sys.exit(1)
        
        pdf_url = latest_report.get('pdf_url')
        if not pdf_url:
            print(json.dumps({'success': False, 'error': f'El reporte "{report_topic}" no tiene PDF generado'}))
            sys.exit(1)
        
        print(f"📎 PDF encontrado: {pdf_url}", file=sys.stderr)
        
        # 3. Descargar PDF una sola vez
        pdf_response = requests.get(pdf_url)
        if pdf_response.status_code != 200:
            print(json.dumps({'success': False, 'error': f'Error descargando PDF: {pdf_response.status_code}'}))
            sys.exit(1)
        
        pdf_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
        
        # 4. Obtener y descargar reportes adicionales si están solicitados
        additional_attachments = []
        
        if attach_report_clp:
            print(f"📎 Obteniendo reporte CLP adicional...", file=sys.stderr)
            clp_report = db.get_latest_report(report_keyword='clp')
            if clp_report and clp_report.get('pdf_url'):
                clp_pdf_response = requests.get(clp_report['pdf_url'])
                if clp_pdf_response.status_code == 200:
                    additional_attachments.append({
                        'filename': 'clp_reporte.pdf',
                        'content': base64.b64encode(clp_pdf_response.content).decode('utf-8'),
                        'encoding': 'base64',
                        'type': 'application/pdf'
                    })
                    print(f"  ✅ Reporte CLP agregado", file=sys.stderr)
                else:
                    print(f"  ⚠️ No se pudo descargar reporte CLP", file=sys.stderr)
            else:
                print(f"  ⚠️ Reporte CLP no encontrado", file=sys.stderr)
        
        if attach_report_copper:
            print(f"📎 Obteniendo reporte Cobre adicional...", file=sys.stderr)
            copper_report = db.get_latest_report(report_keyword='cobre')
            if copper_report and copper_report.get('pdf_url'):
                copper_pdf_response = requests.get(copper_report['pdf_url'])
                if copper_pdf_response.status_code == 200:
                    additional_attachments.append({
                        'filename': 'cobre_reporte.pdf',
                        'content': base64.b64encode(copper_pdf_response.content).decode('utf-8'),
                        'encoding': 'base64',
                        'type': 'application/pdf'
                    })
                    print(f"  ✅ Reporte Cobre agregado", file=sys.stderr)
                else:
                    print(f"  ⚠️ No se pudo descargar reporte Cobre", file=sys.stderr)
            else:
                print(f"  ⚠️ Reporte Cobre no encontrado", file=sys.stderr)
        
        # 5. Mapeo de nombres de reportes
        report_names = {
            'clp': 'Peso Chileno',
            'copper': 'Cobre',
            'cobre': 'Cobre',
            'gold': 'Oro',
            'silver': 'Plata'
        }
        report_name = report_names.get(report_topic, report_topic)
        filename = f"{report_topic}_reporte.pdf"
        
        # 6. Enviar a cada destinatario
        successful = 0
        failed = 0
        results = []
        
        for email in recipients:
            try:
                # Buscar nombre del contacto en apollo_persons
                contact_result = db.supabase.table('apollo_persons')\
                    .select('full_name')\
                    .eq('email', email)\
                    .limit(1)\
                    .execute()
                
                first_name = 'Cliente'
                if contact_result.data and contact_result.data[0].get('full_name'):
                    first_name = contact_result.data[0]['full_name'].split()[0]
                
                print(f"  → Enviando a: {email} ({first_name})", file=sys.stderr)
                
                # Usar body personalizado si está disponible, sino usar template por defecto
                if custom_body:
                    # Reemplazar {nombre} con el nombre del contacto si existe en el body
                    body = custom_body.replace('{nombre}', first_name)
                    # Convertir HTML a texto plano si es necesario (remover tags básicos)
                    import re
                    body = re.sub(r'<br\s*/?>', '\n', body)
                    body = re.sub(r'<p>', '', body)
                    body = re.sub(r'</p>', '\n\n', body)
                    body = re.sub(r'<[^>]+>', '', body)  # Remover otros tags HTML
                    body = body.strip()
                else:
                    # Template por defecto
                    body = f"Hola {first_name},\n\nAdjunto encontrarás el informe del {report_name}.\n\nSaludos cordiales,\nGavin Templeton"
                
                # Construir lista de adjuntos (reporte principal + adicionales)
                all_attachments = [{
                    'filename': filename,
                    'content': pdf_base64,
                    'encoding': 'base64',
                    'type': 'application/pdf'
                }] + additional_attachments
                
                # Usar subject personalizado si está disponible
                email_subject = custom_subject if custom_subject else f"Informe del {report_name}"
                
                # Enviar email directamente usando gmail_send_tool
                # ✅ SOLO TEXTO PLANO (sin HTML)
                result = send_email(
                    to=email,
                    subject=email_subject,
                    body=body,          # ✅ Texto plano
                    html_body=None,     # ❌ NUNCA HTML (explícito)
                    from_email='gavintempleton@gavintempleton.net',
                    attachments=all_attachments
                )
                
                # Registrar en email_messages si fue exitoso
                if result.get('ok'):
                    # Buscar contact_id y company_id
                    contact_id_val = None
                    company_id_val = None
                    
                    try:
                        person_result = db.supabase.table('apollo_persons')\
                            .select('id, company_id')\
                            .eq('email', email)\
                            .limit(1)\
                            .execute()
                        
                        if person_result.data:
                            contact_id_val = person_result.data[0].get('id')
                            company_id_val = person_result.data[0].get('company_id')
                    except Exception:
                        pass
                    
                    # Construir lista de adjuntos para registrar en DB
                    db_attachments = [{'filename': filename, 'url': pdf_url}]
                    if attach_report_clp:
                        clp_report = db.get_latest_report(report_keyword='clp')
                        if clp_report and clp_report.get('pdf_url'):
                            db_attachments.append({'filename': 'clp_reporte.pdf', 'url': clp_report['pdf_url']})
                    if attach_report_copper:
                        copper_report = db.get_latest_report(report_keyword='cobre')
                        if copper_report and copper_report.get('pdf_url'):
                            db_attachments.append({'filename': 'cobre_reporte.pdf', 'url': copper_report['pdf_url']})
                    
                    # Insertar en email_messages
                    db.supabase.table('email_messages').insert({
                        'direction': 'sent',
                        'contact_id': contact_id_val,
                        'company_id': company_id_val,
                        'from_email': 'gavintempleton@gavintempleton.net',
                        'to_emails': [email],
                        'cc_emails': [],
                        'subject': email_subject,
                        'body_html': '',
                        'body_text': body,
                        'message_id': result.get('message_id'),
                        'thread_id': None,
                        'sent_at': datetime.now(timezone.utc).isoformat(),
                        'message_kind': 'report',
                        'attachments': db_attachments
                    }).execute()
                    
                    print(f"    ✅ Enviado exitosamente", file=sys.stderr)
                    successful += 1
                else:
                    print(f"    ❌ Error: {result.get('error')}", file=sys.stderr)
                    failed += 1
                
                results.append({
                    'email': email,
                    'success': result.get('ok', False),
                    'error': result.get('error') if not result.get('ok') else None
                })
                
            except Exception as e:
                print(f"    ❌ Excepción: {e}", file=sys.stderr)
                failed += 1
                results.append({
                    'email': email,
                    'success': False,
                    'error': str(e)
                })
        
        # 7. Imprimir resultado final a stdout
        print(json.dumps({
            'success': True,
            'successful_sends': successful,
            'failed_sends': failed,
            'results': results
        }))
        
        print(f"\n📊 Resumen: {successful}/{len(recipients)} emails enviados exitosamente", file=sys.stderr)
        
    except json.JSONDecodeError as e:
        print(json.dumps({'success': False, 'error': f'Error parseando JSON: {e}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'success': False, 'error': f'Error inesperado: {str(e)}'}))
        sys.exit(1)


if __name__ == '__main__':
    # Redirigir warnings de Python a stderr para mantener stdout limpio (solo JSON)
    import warnings
    warnings.filterwarnings('ignore')
    
    main()


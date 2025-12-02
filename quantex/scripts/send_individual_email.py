#!/usr/bin/env python3
"""
Script standalone para enviar emails individuales desde el CRM.
Se ejecuta desde Next.js vía subprocess.
No requiere servidor Flask ni Modular Agent.

⚠️ IMPORTANTE: Este script envía SOLO emails en TEXTO PLANO (sin HTML)
para evitar filtros de spam y mejorar el deliverability.

Uso:
    python send_individual_email.py
    
Lee JSON desde stdin:
    {
        "to": "cliente@empresa.com",
        "subject": "Asunto del email",
        "body": "Contenido en texto plano...",  ← SOLO texto plano
        "attachments": [
            {
                "filename": "documento.pdf",
                "content": "base64_content",
                "type": "application/pdf"
            }
        ],
        "contact_id": "123",
        "prospect_id": "456"
    }
    
Imprime JSON a stdout:
    {
        "ok": true,
        "message_id": "18f1234abc..."
    }
"""

import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path
import os

# El script está en: C:\quantex\quantex\scripts\send_individual_email.py
# Para hacer "import quantex", necesitamos que C:\quantex esté en sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
quantex_package_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(quantex_package_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)

from quantex.core.agents.modular_agent.gmail_send_tool import send_email
from quantex.core import database_manager as db


def main():
    """Función principal del script."""
    try:
        # 1. Leer JSON desde stdin
        input_data = json.loads(sys.stdin.read())
        to = input_data.get('to', '')
        subject = input_data.get('subject', '')
        body = input_data.get('body', '')  # SOLO texto plano
        attachments = input_data.get('attachments', [])
        contact_id = input_data.get('contact_id')
        prospect_id = input_data.get('prospect_id')
        company_id = input_data.get('company_id')
        
        if not to:
            print(json.dumps({'ok': False, 'error': 'Destinatario requerido'}))
            sys.exit(1)
        
        if not subject:
            print(json.dumps({'ok': False, 'error': 'Asunto requerido'}))
            sys.exit(1)
        
        if not body:
            print(json.dumps({'ok': False, 'error': 'Contenido del email requerido'}))
            sys.exit(1)
        
        print(f"📧 Enviando email a: {to}", file=sys.stderr)
        print(f"📋 Asunto: {subject}", file=sys.stderr)
        print(f"📝 Formato: TEXTO PLANO (sin HTML)", file=sys.stderr)
        print(f"📎 Attachments: {len(attachments)}", file=sys.stderr)
        
        # 2. Enviar email directamente usando gmail_send_tool
        # GARANTIZAR 100% TEXTO PLANO (sin HTML)
        plain_text_body = body if body else ''
        
        result = send_email(
            to=to,
            subject=subject,
            body=plain_text_body,  # ✅ SIEMPRE texto plano
            html_body=None,        # ❌ NUNCA HTML (explícitamente None)
            from_email='gavintempleton@gavintempleton.net',
            attachments=attachments if attachments else None
        )
        
        if not result.get('ok'):
            print(json.dumps(result))
            sys.exit(1)
        
        print(f"  ✅ Email enviado exitosamente", file=sys.stderr)
        print(f"  📧 Message ID: {result.get('message_id')}", file=sys.stderr)
        
        # 3. Registrar en email_messages
        try:
            sent_at = datetime.now(timezone.utc).isoformat()
            
            # Determinar el tipo de mensaje
            # Valores permitidos: 'intro', 'follow_up', 'report', 'other'
            message_kind = 'other'
            if prospect_id:
                message_kind = 'intro'  # Email inicial a prospect
            elif contact_id:
                message_kind = 'follow_up'  # Email a cliente existente
            
            # Preparar attachments para BD
            db_attachments = []
            if attachments:
                for att in attachments:
                    db_attachments.append({
                        'filename': att.get('filename'),
                        'type': att.get('type', 'application/octet-stream')
                    })
            
            # Insertar en email_messages
            email_record = {
                'direction': 'sent',
                'from_email': 'gavintempleton@gavintempleton.net',
                'to_emails': [to],
                'cc_emails': [],
                'subject': subject,
                'body_html': '',  # NUNCA HTML (siempre vacío)
                'body_text': body,  # SOLO texto plano
                'message_id': result.get('message_id'),
                'thread_id': None,
                'sent_at': sent_at,
                'message_kind': message_kind,
                'attachments': db_attachments
            }
            
            # Agregar IDs si existen
            if contact_id:
                email_record['contact_id'] = contact_id
            if company_id:
                email_record['company_id'] = company_id
            
            db.supabase.table('email_messages').insert(email_record).execute()
            print(f"  📝 Registrado en email_messages", file=sys.stderr)
            
            # 4. Actualizar apollo_persons si es prospect
            if prospect_id:
                db.supabase.table('apollo_persons').update({
                    'email_sent': True,
                    'email_sent_at': sent_at
                }).eq('id', prospect_id).execute()
                print(f"  🏷️  Actualizado apollo_persons.email_sent", file=sys.stderr)
            
        except Exception as db_error:
            print(f"  ⚠️ Error registrando en BD: {db_error}", file=sys.stderr)
            # No fallar el envío si el registro en BD falla
        
        # 5. Retornar resultado exitoso
        print(json.dumps({
            'ok': True,
            'message_id': result.get('message_id'),
            'to': to,
            'subject': subject
        }))
        
    except json.JSONDecodeError as e:
        print(json.dumps({'ok': False, 'error': f'Error parseando JSON: {e}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': f'Error inesperado: {str(e)}'}))
        sys.exit(1)


if __name__ == '__main__':
    # Redirigir warnings de Python a stderr
    import warnings
    warnings.filterwarnings('ignore')
    
    main()


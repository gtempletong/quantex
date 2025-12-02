#!/usr/bin/env python3
"""
Herramienta de envío de emails via Gmail API (sin tracking)
Tool name: "gmail.send_email"
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES_SEND = ['https://www.googleapis.com/auth/gmail.send']


def _authenticate_gmail(credentials_file: Optional[str], token_file: Optional[str], scopes: Optional[list] = None):
    creds = None
    requested_scopes = scopes or SCOPES_SEND

    if not credentials_file or not os.path.exists(credentials_file):
        raise FileNotFoundError(f"No se encontró el archivo de credenciales de Gmail: {credentials_file}")

    # Intentar cargar token existente
    if token_file and os.path.exists(token_file):
        try:
            # Cargar credenciales desde archivo
            creds = Credentials.from_authorized_user_file(token_file, requested_scopes)
        except Exception:
            creds = None

    def _has_required_scopes(c):
        try:
            current = set(c.scopes or [])
            needed = set(requested_scopes)
            return needed.issubset(current)
        except Exception:
            return False

    # Si no hay credenciales, están inválidas o no incluyen los scopes requeridos, forzar re-consentimiento
    if (not creds or not creds.valid) or (creds and not _has_required_scopes(creds)):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # Verificación adicional: leer el archivo JSON y comprobar scopes efectivos guardados
        file_scopes_ok = True
        try:
            if token_file and os.path.exists(token_file):
                import json
                with open(token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                saved_scopes = set(token_data.get('scopes') or token_data.get('_scopes') or [])
                needed = set(requested_scopes)
                file_scopes_ok = needed.issubset(saved_scopes)
        except Exception:
            file_scopes_ok = False

        if (not creds) or (not _has_required_scopes(creds)) or (not file_scopes_ok):
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, requested_scopes)
            creds = flow.run_local_server(port=0)

        if token_file:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def _create_message(to_email: str, subject: str, body: str, from_email: Optional[str], 
                   html_body: Optional[str] = None, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Crea un mensaje de email con soporte para HTML y attachments.
    
    attachments: Lista de diccionarios con formato:
        [{
            'filename': 'archivo.pdf',
            'content': 'base64_encoded_content',  # Para archivos manuales
            'encoding': 'base64',
            'type': 'application/pdf'
        }]
        O con URL (para PDFs de Supabase):
        [{
            'filename': 'archivo.pdf',
            'url': 'https://supabase.co/storage/...',  # Para PDFs desde URL
            'type': 'application/pdf'
        }]
    """
    import requests
    
    message = MIMEMultipart()
    message['to'] = to_email
    message['subject'] = subject
    if from_email:
        message['from'] = from_email

    # Adjuntar body (HTML o plain text)
    if html_body:
        message.attach(MIMEText(html_body, 'html'))
    else:
        message.attach(MIMEText(body, 'plain'))

    # Adjuntar archivos si existen
    if attachments:
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            
            # Verificar si es URL o base64
            if 'url' in attachment:
                # Descargar archivo desde URL
                try:
                    response = requests.get(attachment['url'], timeout=30)
                    response.raise_for_status()
                    file_content = response.content
                    part.set_payload(file_content)
                except Exception as e:
                    print(f"⚠️ Error descargando attachment desde URL: {e}")
                    continue
            else:
                # Decodificar desde base64
                part.set_payload(base64.b64decode(attachment['content']))
            
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment["filename"]}"')
            if attachment.get('type'):
                part.set_type(attachment['type'])
            message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}


def send_email(to: str, subject: str, body: str = '', html_body: Optional[str] = None, from_email: Optional[str] = None,
               attachments: Optional[List[Dict[str, Any]]] = None,
               credentials_file: Optional[str] = None, token_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Envía un email usando Gmail API con soporte para HTML y attachments.
    
    Args:
        to: Email destinatario
        subject: Asunto del email
        body: Cuerpo en texto plano (opcional si se usa html_body)
        html_body: Cuerpo en formato HTML (opcional)
        from_email: Email remitente (opcional)
        attachments: Lista de archivos adjuntos en formato base64
        credentials_file: Ruta al archivo de credenciales OAuth
        token_file: Ruta al archivo de token OAuth
    """
    try:
        # Usar credenciales de negocio por defecto para envío
        credentials_path = credentials_file or os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials_business.json')
        token_path = token_file or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token_business.json')

        service = _authenticate_gmail(credentials_path, token_path, scopes=SCOPES_SEND)
        message = _create_message(to, subject, body, from_email, html_body, attachments)
        sent = service.users().messages().send(userId='me', body=message).execute()

        return {
            "ok": True,
            "message_id": sent.get('id'),
            "to": to,
            "subject": subject,
            "from": from_email,
            "attachments_count": len(attachments) if attachments else 0
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}



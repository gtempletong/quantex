#!/usr/bin/env python3
"""
Herramienta de envío de emails via Gmail API (sin tracking)
Tool name: "gmail.send_email"
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any

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


def _create_message(to_email: str, subject: str, html_body: str, from_email: Optional[str]) -> Dict[str, Any]:
    message = MIMEMultipart()
    message['to'] = to_email
    message['subject'] = subject
    if from_email:
        message['from'] = from_email

    message.attach(MIMEText(html_body, 'html'))

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}


def send_email(to: str, subject: str, html_body: str, from_email: Optional[str] = None,
               credentials_file: Optional[str] = None, token_file: Optional[str] = None) -> Dict[str, Any]:
    """Envía un email simple en HTML usando Gmail API."""
    try:
        credentials_path = credentials_file or os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')
        token_path = token_file or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')

        service = _authenticate_gmail(credentials_path, token_path, scopes=SCOPES_SEND)
        message = _create_message(to, subject, html_body, from_email)
        sent = service.users().messages().send(userId='me', body=message).execute()

        return {
            "ok": True,
            "message_id": sent.get('id'),
            "to": to,
            "subject": subject,
            "from": from_email
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}



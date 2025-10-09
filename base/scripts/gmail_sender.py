#!/usr/bin/env python3
"""
Sistema de envío de emails usando Gmail API
"""

import os
import sys
import base64
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# (Tracking eliminado) Sin dependencia de Supabase para registrar eventos

# Cargar variables de entorno
load_dotenv()

# Scopes necesarios para Gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailSender:
    def __init__(self, credentials_file=None, token_file=None):
        # Usar variables de entorno o valores por defecto
        self.credentials_file = credentials_file or os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')
        self.token_file = token_file or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Autenticar con Gmail API"""
        creds = None
        
        # Verificar que existe el archivo de credenciales
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"❌ No se encontró el archivo de credenciales: {self.credentials_file}")
        
        # Cargar token existente
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Si no hay credenciales válidas, hacer login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refrescando token de acceso...")
                creds.refresh(Request())
            else:
                print("🔐 Iniciando flujo de autenticación OAuth2...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Guardar credenciales para próxima vez
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            print("💾 Token guardado para futuras sesiones")
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Autenticado con Gmail API para envío")
        print("✅ Autenticado con Gmail API")
    
    def create_message(self, to, subject, body, from_email=None):
        """Crear mensaje de email (HTML)."""
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message['from'] = from_email or 'gavintempleton@gavintempleton.net'
        
        # Agregar cuerpo del mensaje
        message.attach(MIMEText(body, 'html'))
        
        # Codificar en base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}
    
    def send_email(self, to, subject, body, from_email=None):
        """Enviar email (sin tracking)."""
        try:
            message = self.create_message(to, subject, body, from_email)
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            print(f"✅ Email enviado a {to} - ID: {sent_message['id']}")
            
            return sent_message['id']
            
        except Exception as e:
            print(f"❌ Error enviando email a {to}: {e}")
            return None
    
    def send_bulk_emails(self, email_list, subject_template, body_template):
        """Enviar emails masivos"""
        results = []
        
        for email_data in email_list:
            # Personalizar contenido
            subject = subject_template.format(**email_data)
            body = body_template.format(**email_data)
            
            # Enviar email
            message_id = self.send_email(
                to=email_data['email'],
                subject=subject,
                body=body
            )
            
            results.append({
                'email': email_data['email'],
                'message_id': message_id,
                'status': 'sent' if message_id else 'failed'
            })
        
        return results

def main():
    """CLI principal para Gmail Sender"""
    parser = argparse.ArgumentParser(description='Gmail Sender - Envía emails usando Gmail API')
    parser.add_argument('--to', '-t', help='Dirección de email destinatario')
    parser.add_argument('--subject', '-s', help='Asunto del email')
    parser.add_argument('--body', '-b', help='Cuerpo del email (HTML o texto)')
    parser.add_argument('--from', '-f', help='Dirección de email remitente (opcional)')
    parser.add_argument('--test', action='store_true', help='Enviar email de prueba')
    # Tracking eliminado
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.test:
        if not args.to:
            print("❌ Error: --to es requerido cuando usas --test")
            sys.exit(1)
    else:
        if not all([args.to, args.subject, args.body]):
            print("❌ Error: --to, --subject y --body son requeridos (o usa --test)")
            sys.exit(1)
    
    try:
        sender = GmailSender()
        
        if args.test:
            # Email de prueba
            subject = "Test desde Gmail API"
            body = """
            <h2>Hola!</h2>
            <p>Este es un email de prueba enviado desde Gmail API.</p>
            <p>Saludos,<br>Quantex</p>
            """
            to_email = args.to
        else:
            subject = args.subject
            body = args.body
            to_email = args.to
        
        # Enviar email
        message_id = sender.send_email(
            to=to_email,
            subject=subject,
            body=body,
            from_email=getattr(args, 'from', None)
        )
        
        if message_id:
            print(f"✅ Email enviado exitosamente - ID: {message_id}")
        else:
            print("❌ Error enviando email")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("💡 Asegúrate de tener el archivo gmail_credentials.json en la carpeta base/scripts/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()








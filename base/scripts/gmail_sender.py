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
from email.mime.application import MIMEApplication
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

# Template por defecto para el cuerpo del email
DEFAULT_EMAIL_TEMPLATE = """Hola {recipient_name},

Te adjunto el informe del {report_name}.

Saludos,

Gavin Templeton"""

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
    
    def create_message(self, to, subject, body, from_email=None, attachments=None):
        """Crear mensaje de email (solo PDF adjunto)."""
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message['from'] = from_email or 'gavintempleton@gavintempleton.net'
        
        # Usar el cuerpo proporcionado
        message.attach(MIMEText(body, 'plain'))
        
        # Agregar attachments si existen
        if attachments:
            for attachment_data in attachments:
                attachment = MIMEApplication(
                    attachment_data['content'],
                    _subtype=attachment_data.get('subtype', 'pdf')
                )
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_data["filename"]}"'
                )
                message.attach(attachment)
        
        # Codificar en base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}
    
    def send_email(self, to, subject, body, from_email=None, attachments=None):
        """Enviar email (sin tracking) con attachments opcionales."""
        try:
            message = self.create_message(to, subject, body, from_email, attachments)
            
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
    parser.add_argument('--body-file', help='Archivo con el cuerpo del email')
    parser.add_argument('--attachment', '-a', help='Ruta al archivo PDF para adjuntar')
    parser.add_argument('--attachment-url', help='URL del PDF para descargar y adjuntar')
    parser.add_argument('--test', action='store_true', help='Modo de prueba')
    parser.add_argument('--recipient-name', help='Nombre del destinatario para el template')
    parser.add_argument('--report-name', help='Nombre del informe para el template')
    parser.add_argument('--use-template', action='store_true', help='Usar template por defecto')
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.test:
        if not args.to:
            print("❌ Error: --to es requerido cuando usas --test")
            sys.exit(1)
    else:
        if not args.to or not args.subject:
            print("❌ Error: --to y --subject son requeridos")
            sys.exit(1)
        if not args.body and not args.body_file and not args.use_template:
            print("❌ Error: --body, --body-file o --use-template son requeridos")
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
            to_email = args.to
            
            # Leer cuerpo del email
            if args.use_template:
                # Usar template por defecto
                recipient_name = args.recipient_name or "Cliente"
                report_name = args.report_name or "día"
                body = DEFAULT_EMAIL_TEMPLATE.format(
                    recipient_name=recipient_name,
                    report_name=report_name
                )
                print(f"📝 Usando template con: recipient_name='{recipient_name}', report_name='{report_name}'")
                print(f"📝 Template resultante:\n{body}")
            elif args.body_file:
                # Leer desde archivo
                try:
                    with open(args.body_file, 'r', encoding='utf-8') as f:
                        body = f.read()
                    print(f"📄 Leyendo cuerpo desde archivo: {args.body_file}")
                except Exception as e:
                    print(f"❌ Error leyendo archivo de cuerpo: {e}")
                    sys.exit(1)
            elif args.body:
                # Usar cuerpo directo
                body = args.body
            else:
                print("❌ Error: Se requiere --body, --body-file o --use-template")
                sys.exit(1)
        
        # Preparar attachments si existen
        attachments = None
        if args.attachment or args.attachment_url:
            attachments = []
            
            if args.attachment:
                # Adjuntar archivo local
                try:
                    with open(args.attachment, 'rb') as f:
                        pdf_content = f.read()
                    attachments.append({
                        'content': pdf_content,
                        'filename': os.path.basename(args.attachment),
                        'subtype': 'pdf'
                    })
                    print(f"📎 Adjuntando archivo local: {args.attachment}")
                except Exception as e:
                    print(f"❌ Error leyendo archivo adjunto: {e}")
                    sys.exit(1)
            
            if args.attachment_url:
                # Descargar PDF desde URL
                try:
                    import requests
                    response = requests.get(args.attachment_url)
                    response.raise_for_status()
                    
                    # Extraer nombre del archivo de la URL
                    filename = args.attachment_url.split('/')[-1]
                    if not filename.endswith('.pdf'):
                        filename = f"reporte_{filename}.pdf"
                    
                    attachments.append({
                        'content': response.content,
                        'filename': filename,
                        'subtype': 'pdf'
                    })
                    print(f"📎 Descargando y adjuntando PDF desde URL: {args.attachment_url}")
                except Exception as e:
                    print(f"❌ Error descargando PDF desde URL: {e}")
                    sys.exit(1)
        
        # Enviar email
        message_id = sender.send_email(
            to=to_email,
            subject=subject,
            body=body,
            from_email=getattr(args, 'from', None),
            attachments=attachments
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








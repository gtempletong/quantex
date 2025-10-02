#!/usr/bin/env python3
"""
Sistema de monitoreo de emails usando Gmail API
Lee respuestas de clientes y prospectos
"""

import os
import sys
import re
import argparse
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailMonitor:
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
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refrescando token de acceso...")
                creds.refresh(Request())
            else:
                print("🔐 Iniciando flujo de autenticación OAuth2...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            print("💾 Token guardado para futuras sesiones")
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Autenticado con Gmail API para monitoreo")
    
    def search_emails(self, query, max_results=10):
        """Buscar emails con query específica"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
            
        except Exception as e:
            print(f"❌ Error buscando emails: {e}")
            return []
    
    def get_email_content(self, message_id):
        """Obtener contenido completo de un email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extraer headers
            headers = message['payload'].get('headers', [])
            email_data = {}
            
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'from':
                    email_data['from'] = value
                elif name == 'to':
                    email_data['to'] = value
                elif name == 'subject':
                    email_data['subject'] = value
                elif name == 'date':
                    email_data['date'] = value
            
            # Extraer cuerpo del email
            body = self.extract_body(message['payload'])
            email_data['body'] = body
            
            return email_data
            
        except Exception as e:
            print(f"❌ Error obteniendo email {message_id}: {e}")
            return None
    
    def extract_body(self, payload):
        """Extraer cuerpo del email del payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def get_replies(self, from_email=None, days_back=7):
        """Obtener respuestas de los últimos días"""
        # Construir query de búsqueda
        date_query = f"newer_than:{days_back}d"
        query = f"in:inbox {date_query}"
        
        if from_email:
            query += f" from:{from_email}"
        
        # Buscar emails
        messages = self.search_emails(query, max_results=50)
        
        replies = []
        for message in messages:
            email_data = self.get_email_content(message['id'])
            if email_data:
                replies.append(email_data)
        
        return replies
    
    def get_campaign_replies(self, campaign_subject, days_back=7):
        """Obtener respuestas de una campaña específica"""
        # Buscar emails que contengan el asunto de la campaña
        query = f"in:inbox newer_than:{days_back}d subject:\"Re: {campaign_subject}\""
        
        messages = self.search_emails(query, max_results=50)
        
        replies = []
        for message in messages:
            email_data = self.get_email_content(message['id'])
            if email_data:
                replies.append(email_data)
        
        return replies
    
    def mark_as_read(self, message_id):
        """Marcar email como leído"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"✅ Email {message_id} marcado como leído")
        except Exception as e:
            print(f"❌ Error marcando email como leído: {e}")
    
    def get_unread_count(self):
        """Obtener número de emails no leídos"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='in:inbox is:unread'
            ).execute()
            
            return results.get('resultSizeEstimate', 0)
        except Exception as e:
            print(f"❌ Error obteniendo conteo de emails: {e}")
            return 0
    
    def check_email_read_status(self, message_id):
        """Verificar si un email fue leído (usando labels)"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Labels']
            ).execute()
            
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            
            return {
                'message_id': message_id,
                'is_read': not is_unread,
                'is_unread': is_unread,
                'labels': labels
            }
            
        except Exception as e:
            print(f"❌ Error verificando estado de email {message_id}: {e}")
            return None
    
    def track_email_by_subject(self, subject, days_back=7):
        """Buscar emails enviados por asunto y verificar su estado de lectura"""
        try:
            # Buscar emails enviados con ese asunto
            sent_query = f'in:sent subject:"{subject}" newer_than:{days_back}d'
            sent_messages = self.search_emails(sent_query, max_results=10)
            
            results = []
            for msg in sent_messages:
                status = self.check_email_read_status(msg['id'])
                if status:
                    results.append(status)
            
            return results
            
        except Exception as e:
            print(f"❌ Error trackeando emails por asunto: {e}")
            return []

def main():
    """CLI principal para Gmail Monitor"""
    parser = argparse.ArgumentParser(description='Gmail Monitor - Lee respuestas de clientes y prospectos')
    parser.add_argument('--query', '-q', help='Query de búsqueda (ej: "from:cliente@empresa.com")')
    parser.add_argument('--days', '-d', type=int, default=7, help='Días hacia atrás para buscar (default: 7)')
    parser.add_argument('--max', '-m', type=int, default=10, help='Máximo número de resultados (default: 10)')
    parser.add_argument('--unread', '-u', action='store_true', help='Solo mostrar emails no leídos')
    parser.add_argument('--replies', '-r', action='store_true', help='Buscar respuestas a emails enviados')
    parser.add_argument('--track', '-t', help='Verificar estado de lectura de emails por asunto')
    parser.add_argument('--status', '-s', help='Verificar estado de un email específico por ID')
    
    args = parser.parse_args()
    
    try:
        monitor = GmailMonitor()
        
        print(f"📧 Emails no leídos: {monitor.get_unread_count()}")
        
        if args.track:
            # Verificar estado de emails por asunto
            print(f"\n📊 Verificando estado de emails con asunto: '{args.track}'")
            tracking_results = monitor.track_email_by_subject(args.track, args.days)
            
            print(f"📬 Emails enviados encontrados: {len(tracking_results)}")
            for i, result in enumerate(tracking_results):
                status = "✅ LEÍDO" if result['is_read'] else "❌ NO LEÍDO"
                print(f"\n--- Email {i+1} ---")
                print(f"ID: {result['message_id']}")
                print(f"Estado: {status}")
                print(f"Labels: {', '.join(result['labels'])}")
            
            emails = []  # No mostrar contenido para tracking
            
        elif args.status:
            # Verificar estado de un email específico
            print(f"\n📊 Verificando estado del email: {args.status}")
            status = monitor.check_email_read_status(args.status)
            if status:
                status_text = "✅ LEÍDO" if status['is_read'] else "❌ NO LEÍDO"
                print(f"Estado: {status_text}")
                print(f"Labels: {', '.join(status['labels'])}")
            else:
                print("❌ Email no encontrado o error")
            emails = []  # No mostrar contenido para status
            
        elif args.unread:
            # Solo emails no leídos
            message_ids = monitor.search_emails('in:inbox is:unread', args.max)
            print(f"\n📬 Emails no leídos encontrados: {len(message_ids)}")
            emails = []
            for msg in message_ids:
                email_data = monitor.get_email_content(msg['id'])
                if email_data:
                    emails.append(email_data)
        elif args.replies:
            # Respuestas a emails enviados
            emails = monitor.get_replies(days_back=args.days)
            print(f"\n📬 Respuestas encontradas: {len(emails)}")
        elif args.query:
            # Query personalizada
            message_ids = monitor.search_emails(args.query, args.max)
            print(f"\n📬 Emails encontrados: {len(message_ids)}")
            emails = []
            for msg in message_ids:
                email_data = monitor.get_email_content(msg['id'])
                if email_data:
                    emails.append(email_data)
        else:
            # Por defecto: respuestas de los últimos N días
            emails = monitor.get_replies(days_back=args.days)
            print(f"\n📬 Respuestas de los últimos {args.days} días: {len(emails)}")
        
        # Mostrar resultados
        for i, email in enumerate(emails[:args.max]):
            print(f"\n--- Email {i+1} ---")
            print(f"De: {email.get('from', 'N/A')}")
            print(f"Asunto: {email.get('subject', 'N/A')}")
            print(f"Fecha: {email.get('date', 'N/A')}")
            body = email.get('body', 'N/A')
            if len(body) > 200:
                body = body[:200] + "..."
            print(f"Cuerpo: {body}")
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("💡 Asegúrate de tener el archivo gmail_credentials.json en la carpeta base/scripts/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()








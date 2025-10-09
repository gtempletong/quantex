#!/usr/bin/env python3
"""
Herramienta de ingesta de emails recibidos vía Gmail API
Tool name: "gmail.ingest_received"
"""

import os
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from .gmail_send_tool import _authenticate_gmail  # reutilizamos auth
except ImportError:
    # Permitir ejecución directa del script fuera del paquete
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from gmail_send_tool import _authenticate_gmail  # type: ignore


def _get_service(credentials_file: Optional[str], token_file: Optional[str]):
    # Solicitar explícitamente scopes de lectura
    SCOPES_READ = ['https://www.googleapis.com/auth/gmail.readonly']
    return _authenticate_gmail(credentials_file, token_file, scopes=SCOPES_READ)


def _parse_payload_to_bodies(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    html_body = None
    text_body = None

    def decode_part(body):
        data = body.get('data')
        if not data:
            return None
        return base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')

    if not payload:
        return {"html_body": None, "text_body": None}

    mime_type = payload.get('mimeType')
    if mime_type == 'text/html':
        html_body = decode_part(payload.get('body', {}))
    elif mime_type == 'text/plain':
        text_body = decode_part(payload.get('body', {}))
    else:
        # multipart
        for part in payload.get('parts', []) or []:
            ptype = part.get('mimeType')
            if ptype == 'text/html' and not html_body:
                html_body = decode_part(part.get('body', {}))
            elif ptype == 'text/plain' and not text_body:
                text_body = decode_part(part.get('body', {}))

    return {"html_body": html_body, "text_body": text_body}


def ingest_received(max_results: int = 10, query: Optional[str] = None,
                    credentials_file: Optional[str] = None, token_file: Optional[str] = None) -> Dict[str, Any]:
    """Lee emails recibidos recientes y los persiste en public.email_messages.

    Args:
        max_results: límite de mensajes a leer.
        query: consulta Gmail (por defecto inbox de los últimos 2 días).
        credentials_file/token_file: rutas opcionales si no se usan las de env.
    """
    try:
        credentials_path = credentials_file or os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')
        token_path = token_file or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')
        service = _get_service(credentials_path, token_path)

        q = query or 'in:inbox newer_than:2d'
        resp = service.users().messages().list(userId='me', q=q, maxResults=max_results).execute()
        messages = resp.get('messages', []) or []

        from quantex.core import database_manager as db

        inserted: List[str] = []
        skipped: List[str] = []
        for m in messages:
            msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
            headers = {h['name'].lower(): h.get('value', '') for h in msg.get('payload', {}).get('headers', [])}
            from_email = headers.get('from', '')
            subject = headers.get('subject', '')
            to_value = headers.get('to', '')
            date_hdr = headers.get('date', '')
            # Fecha
            received_at = None
            try:
                received_at = datetime.fromtimestamp(int(msg.get('internalDate', '0')) / 1000, tz=timezone.utc)
            except Exception:
                received_at = datetime.now(timezone.utc)

            bodies = _parse_payload_to_bodies(msg.get('payload', {}))

            # Resolver contact_id/company_id por from_email exacto (si coincide)
            contact_id_val = None
            company_id_val = None
            try:
                # Extraer email puro entre <...> si viene con nombre
                from_email_clean = from_email
                if '<' in from_email and '>' in from_email:
                    from_email_clean = from_email.split('<')[-1].split('>')[0].strip()

                contact_res = db.supabase.table('personas').select('id,rut_empresa').eq('email_contacto', from_email_clean).limit(1).execute()
                if contact_res and contact_res.data:
                    contact_id_val = contact_res.data[0].get('id')
                    rut_emp = contact_res.data[0].get('rut_empresa')
                    if rut_emp:
                        emp_res = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_emp).limit(1).execute()
                        if emp_res and emp_res.data:
                            company_id_val = emp_res.data[0].get('id')
            except Exception:
                pass

            # Deduplicación por message_id
            try:
                existing = db.supabase.table('email_messages').select('id').eq('message_id', msg.get('id')).limit(1).execute()
                if existing and existing.data:
                    skipped.append(msg.get('id'))
                    continue
            except Exception:
                # Si falla el check, seguimos e intentamos insertar (mejor tener dato que perderlo)
                pass

            payload_row = {
                'direction': 'received',
                **({'contact_id': contact_id_val} if contact_id_val is not None else {}),
                **({'company_id': company_id_val} if company_id_val is not None else {}),
                'from_email': from_email,
                'to_emails': [to_value] if to_value else [],
                'cc_emails': [],
                'subject': subject,
                'body_html': bodies.get('html_body'),
                'body_text': bodies.get('text_body'),
                'message_id': msg.get('id'),
                'thread_id': msg.get('threadId'),
                'received_at': received_at.isoformat(),
            }
            db.supabase.table('email_messages').insert(payload_row).execute()
            inserted.append(msg.get('id'))

        return {"ok": True, "inserted_count": len(inserted), "skipped_count": len(skipped), "message_ids": inserted, "skipped_ids": skipped}
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API error: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    # Ejecución directa para pruebas rápidas
    try:
        q = os.getenv('INGEST_QUERY')  # ej: "in:inbox newer_than:2d"
        max_r = int(os.getenv('INGEST_MAX_RESULTS', '10'))
        result = ingest_received(max_results=max_r, query=q,
                                 credentials_file=os.getenv('GMAIL_CREDENTIALS_FILE'),
                                 token_file=os.getenv('GMAIL_TOKEN_FILE'))
        print(result)
    except Exception as e:
        print({"ok": False, "error": str(e)})



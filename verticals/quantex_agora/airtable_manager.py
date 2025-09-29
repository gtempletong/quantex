import os
import sys
import traceback
import requests
import json
from dotenv import load_dotenv
from pyairtable import Api
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from quantex.core import database_manager as db

# --- Configuración de APIs ---
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# --- SECCIÓN 2: HERRAMIENTAS DE BAJO NIVEL (Caja de Herramientas) ---

def get_contacts(table_name: str = "Contacts") -> list | None:
    """
    Obtiene todos los registros de una tabla específica en Airtable.
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("  -> ❌ [Airtable] Error: Claves de API o Base ID no encontradas en .env")
        return None
    try:
        print(f"  -> ☁️  [Airtable] Conectando para obtener contactos de la tabla '{table_name}'...")
        api = Api(AIRTABLE_API_KEY)
        airtable_table = api.table(AIRTABLE_BASE_ID, table_name)
        all_records = airtable_table.all()
        print(f"    -> ✅ [Airtable] Se encontraron {len(all_records)} registros.")
        return all_records
    except Exception as e:
        print(f"  -> ❌ [Airtable] Error al conectar u obtener registros: {e}")
        return None

def _determine_contact_type(contact_id: str) -> str:
    """
    Determina si un contacto es cliente o prospecto basado en su ID.
    """
    try:
        # Buscar en Clientes primero
        clientes = get_contacts("Clientes")
        if clientes and any(c.get('id') == contact_id for c in clientes):
            return "clientes"
        
        # Si no está en Clientes, buscar en Prospectos
        prospectos = get_contacts("Prospectos")
        if prospectos and any(p.get('id') == contact_id for p in prospectos):
            return "prospectos"
        
        # Por defecto, asumir clientes
        return "clientes"
    except Exception:
        return "clientes"

def log_interaction(contact_id: str, interaction_type: str, detail: str, subject: str | None = None, raw_event: dict | str | None = None, table_type: str = None):
    """
    Crea un nuevo registro en la tabla 'Interactions Clientes' o 'Interactions Prospectos' de Airtable.
    """
    if not all([AIRTABLE_API_KEY, AIRTABLE_BASE_ID, contact_id]):
        print("  -> ⚠️  [Airtable Log] Faltan datos para registrar la interacción.")
        return
    try:
        api = Api(AIRTABLE_API_KEY)
        # Determinar qué tabla usar basado en el tipo
        if table_type is None:
            table_type = _determine_contact_type(contact_id)
        
        table_name = "Interactions Clientes" if table_type.lower() == "clientes" else "Interactions Prospectos"
        interactions_table = api.table(AIRTABLE_BASE_ID, table_name)

        # Intentar mapear el campo de enlace al contacto según naming más común
        link_field_candidates = ["Contact", "Cliente", "Contacto"]
        link_payloads = [
            {candidate: [contact_id]} for candidate in link_field_candidates
        ]

        # IDs/nombres reales de la tabla Interactions (provistos por el usuario)
        # Preferimos IDs para máxima robustez, pero aceptamos nombres por compatibilidad
        field_candidates_by_semantic = {
            "link": ["fldfHHYB6SxmV8HRE", "Contact", "Cliente", "Contacto"],
            "date": ["fldb7ymYJwN6zUqiy", "Date", "Fecha"],
            "interaction_type": ["fldM0zY4im0B13wWR", "InteractionType"],
            "detail": ["fld8s8q8iUEHzJUxY", "Detail", "Detalle", "Detalles"],
            "event_type": ["fldEpHfo46EZhYUpg", "event_type"],
            "subject": ["fldRLJrNjKJVdTiYG", "subject", "Subject"]
        }

        # Intentar crear con el primer campo de enlace que funcione
        last_error = None
        from datetime import datetime
        base_fields = {}
        # Set date
        for key in field_candidates_by_semantic["date"]:
            base_fields[key] = datetime.utcnow().strftime('%Y-%m-%d')
            break
        # Set interaction type, detail, subject, event
        for key in field_candidates_by_semantic["interaction_type"]:
            base_fields[key] = interaction_type
            break
        for key in field_candidates_by_semantic["detail"]:
            base_fields[key] = detail
            break
        if subject:
            for key in field_candidates_by_semantic["subject"]:
                base_fields[key] = subject
                break
        if raw_event is not None:
            raw_str = raw_event if isinstance(raw_event, str) else json.dumps(raw_event, ensure_ascii=False)
            for key in field_candidates_by_semantic["event_type"]:
                base_fields[key] = raw_str
                break

        for payload in link_payloads:
            try:
                # map link key to preferred id/name
                link_mapped = {}
                for candidate in field_candidates_by_semantic["link"]:
                    link_mapped[candidate] = payload.get(list(payload.keys())[0])
                    break
                fields = {**base_fields, **link_mapped}
                interactions_table.create(fields)
                print("  -> ✅ [Airtable Log] Interacción registrada en 'Interactions'.")
                return
            except Exception as e:
                last_error = e
                continue

        # Si ninguno funcionó, intentar al menos sin campo link (degradado)
        try:
            # Intento sin link: crear usando campos por ID/nombre
            interactions_table.create(base_fields)
            print("  -> ⚠️  [Airtable Log] Interacción creada sin vínculo al contacto (revisar campos de enlace).")
            return
            # Último recurso: crear un registro mínimo con un campo de notas genérico
            for notes_key in ["Notes", "Notas", "Observaciones", "Description"]:
                try:
                    interactions_table.create({notes_key: f"{interaction_type}: {detail}"})
                    print("  -> ⚠️  [Airtable Log] Interacción creada con campo de notas genérico.")
                    return
                except Exception as e:
                    last_error = e
                    continue
            print(f"  -> ❌ [Airtable Log] No fue posible registrar la interacción. Último error: {last_error}")
        except Exception as e:
            print(f"  -> ❌ [Airtable Log] Error creando interacción: {e} | Último error de enlace: {last_error}")
    except Exception as e:
        print(f"  -> ❌ [Airtable Log] Error inesperado registrando la interacción: {e}")

def update_contact(contact_id: str, update_data: dict, table_name: str = "Contacts") -> bool:
    """
    Actualiza un contacto en Airtable
    
    Args:
        contact_id: ID del contacto a actualizar
        update_data: Diccionario con los campos a actualizar
        
    Returns:
        True si se actualizó correctamente
    """
    if not all([AIRTABLE_API_KEY, AIRTABLE_BASE_ID, contact_id]):
        print("  -> ⚠️  [Airtable Update] Faltan datos para actualizar el contacto.")
        return False
    
    try:
        print(f"  -> ☁️  [Airtable] Actualizando contacto {contact_id} en tabla '{table_name}'...")
        api = Api(AIRTABLE_API_KEY)
        airtable_table = api.table(AIRTABLE_BASE_ID, table_name)
        
        airtable_table.update(contact_id, update_data)
        print(f"    -> ✅ [Airtable] Contacto actualizado exitosamente.")
        return True
        
    except Exception as e:
        print(f"  -> ❌ [Airtable] Error actualizando contacto: {e}")
        return False

# --- SECCIÓN 3: LÓGICA DE NEGOCIO DE ALTO NIVEL (Acciones) ---

def list_contacts_action():
    """
    Acción de negocio para obtener y formatear una lista de contactos.
    (Lógica de _handle_list_contacts en respaldo.py)
    """
    contact_list = get_contacts("Clientes")
    if not contact_list:
        return "No se encontraron contactos."
    
    response_text = "Contactos encontrados:\n" + "\n".join(
        [f"- {c.get('fields', {}).get('Name', 'Sin Nombre')}" for c in contact_list]
    )
    return response_text


def _send_email_brevo(subject: str, html_content: str, recipient_email: str, recipient_name: str) -> bool:
    """Función interna para enviar un correo electrónico usando la API de Brevo."""

    # --- INICIO DEL CÓDIGO DE DEPURACIÓN ---
    print(f"🕵️  [ESPÍA DE CLAVE] Usando BREVO_API_KEY que empieza con: '{str(BREVO_API_KEY)[:10]}' y termina con: '{str(BREVO_API_KEY)[-4:]}'")
    # --- FIN DEL CÓDIGO DE DEPURACIÓN ---

    if not BREVO_API_KEY:
        print("  -> ❌ [Brevo] Error: La clave de API de Brevo no está configurada.")
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = sib_api_v3_sdk.SendSmtpEmailSender(name="Quantex Reports", email="gavintempleton@gavintempleton.net") # Reemplazar si es necesario
    to = [sib_api_v3_sdk.SendSmtpEmailTo(email=recipient_email, name=recipient_name)]
    
    smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, sender=sender, html_content=html_content, subject=subject)

    try:
        api_instance.send_transac_email(smtp_email)
        print(f"      -> ✅ [Brevo] Email enviado exitosamente a {recipient_name}.")
        return True
    except ApiException as e:
        print(f"      -> ❌ [Brevo] Excepción al enviar el email: {e}")
        return False
    
def process_webhook_event_action(event_data: dict):
    """
    Procesa un evento de webhook recibido de Brevo y lo registra en Airtable.
    """
    try:
        event_type = event_data.get("event")
        recipient_email = event_data.get("email")
        subject = event_data.get("subject")

        if not all([event_type, recipient_email]):
            print("  -> [Webhook] Evento recibido incompleto. Faltan datos clave.")
            return

        print(f"  -> 📥 [Webhook] Evento recibido: '{event_type}' para '{recipient_email}'")

        # 1. Buscar al contacto en Airtable por su email
        #    Usar 'Clientes' (antes: 'Contacts')
        all_contacts = get_contacts("Clientes")
        if not all_contacts: return

        target_contact = next((c for c in all_contacts if c.get('fields', {}).get('Email', '').lower() == recipient_email.lower()), None)

        if not target_contact:
            print(f"    -> ⚠️  [Webhook] No se encontró un contacto con el email '{recipient_email}'.")
            return

        # 2. Registrar la interacción
        contact_id = target_contact.get('id')
        log_interaction(
            contact_id=contact_id,
            interaction_type=f"Email {event_type.capitalize()}", # Ej: "Email Opened"
            detail=f"Asunto: {subject}"
        )
        print(f"    -> ✅ [Webhook] Interacción registrada exitosamente para {recipient_email}.")

    except Exception as e:
        print(f"  -> ❌ [Webhook] Error procesando el evento: {e}")    

# --- SECCIÓN 3: LÓGICA DE NEGOCIO DE ALTO NIVEL (Acciones) ---

def send_report_action(report_topic: str, target: str) -> str:
    """
    (Versión Unificada y Corregida)
    Acción de negocio para enviar un informe a un segmento (por Type) o a un individuo (por Name).
    """
    try:
        print(f"-> 📧 Iniciando envío: Informe '{report_topic}' para el objetivo '{target}'...")
        
        # Obtener el último informe final desde Supabase
        latest_report = db.get_latest_report(report_keyword=report_topic)
        if not latest_report or not latest_report.get('full_content'):
            # Fallback mínimo si no existe artefacto
            html_content = f"<h1>Reporte: {report_topic}</h1><p>Contenido del reporte...</p>"
        else:
            html_content = latest_report.get('full_content')
        # Asunto del correo según el tópico del informe
        topic_lc = (report_topic or '').strip().lower()
        if topic_lc in ('cobre', 'hg=f'):
            report_subject = "Informe Diario del Cobre"
        elif topic_lc in ('clp', 'peso chileno'):
            report_subject = "Informe Diario del Peso Chileno"
        else:
            report_subject = f"Quantex Report: {report_topic.capitalize()}"

        # Leer destinatarios desde 'Clientes' y permitir también 'Prospectos'
        all_clients = get_contacts("Clientes") or []
        all_prospects = get_contacts("Prospectos") or []
        if not all_clients and not all_prospects:
            return "No se pudo obtener la lista de contactos de Airtable."

        # --- Lógica de Búsqueda/Selección Flexible ---
        
        def get_field(fields: dict, candidates: list[str]) -> str:
            for key in candidates:
                if key in fields and isinstance(fields[key], str) and fields[key].strip():
                    return fields[key]
            return ''

        target_lc = (target or '').strip().lower()

        contacts_to_send = []

        # 0) Email literal
        if '@' in target_lc and ' ' not in target_lc:
            pseudo_contact = {
                'id': 'manual',
                'fields': {'Email': target, 'Name': target}
            }
            contacts_to_send = [pseudo_contact]
        else:
            # 1) Grupo completo: 'clientes' o 'prospectos'
            if target_lc in ("clientes", "cliente"):
                contacts_to_send = list(all_clients)
            elif target_lc in ("prospectos", "prospecto"):
                contacts_to_send = list(all_prospects)

            # 2) Si no, buscar por nombre exacto en ambas tablas
            if not contacts_to_send:
                print(f"  -> No se encontró segmento directo. Buscando por nombre en Clientes y Prospectos...")
                by_name_clients = [
                    c for c in all_clients
                    if get_field(c.get('fields', {}), ['Name', 'Nombre']).strip().lower() == target_lc
                ]
                by_name_prospects = [
                    p for p in all_prospects
                    if get_field(p.get('fields', {}), ['Name', 'Nombre']).strip().lower() == target_lc
                ]
                contacts_to_send = by_name_clients + by_name_prospects

        if not contacts_to_send:
            return f"No se encontraron contactos para el objetivo '{target}' (ni como segmento ni como nombre)."

        success_count = 0
        for contact in contacts_to_send:
            contact_id = contact.get('id')
            fields = contact.get('fields', {})
            recipient_email = get_field(fields, ['Email', 'Correo', 'E-mail'])
            recipient_name = get_field(fields, ['Name', 'Nombre'])
            
            if recipient_email:
                print(f"    -> 📤 Enviando a {recipient_name} ({recipient_email})...")
                # Esta es la llamada real al servicio de envío de correos
                if _send_email_brevo(report_subject, html_content, recipient_email, recipient_name):
                    success_count += 1
                    # Interactions logging moved to Supabase only. Airtable logging disabled.
                    print(f"      -> 📒 [Interactions] Logged in Supabase. (Airtable disabled)")
                else:
                    print(f"      -> ⚠️  Fallo en el envío a {recipient_name}.")
        
        if success_count > 0:
            return f"✅ Informe enviado exitosamente a {success_count} contacto(s)."
        else:
            return f"Se encontraron {len(contacts_to_send)} contacto(s) para '{target}', pero ninguno tenía un email válido para el envío."

    except Exception as e:
        traceback.print_exc()
        return f"Ocurrió un error inesperado durante el envío: {e}"  
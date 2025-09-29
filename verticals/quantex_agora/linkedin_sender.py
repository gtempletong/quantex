#!/usr/bin/env python3
"""
LinkedIn Sender - Script para enviar URLs al phantom
Ejecutar 1 vez al día - Solo envía URLs con Phantom Status = "En Cola"
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

try:
    import gspread
except Exception:
    gspread = None

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Importar clases existentes
from verticals.quantex_agora.phantom_base_manager import PhantomBaseManager
from verticals.quantex_agora import airtable_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_sender.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LinkedInSender(PhantomBaseManager):
    """Script especializado para enviar URLs al phantom"""
    
    def __init__(self):
        """Inicializar el sender"""
        # Phantom ID del LinkedIn Auto Connect
        phantom_id = os.getenv("PHANTOMBUSTER_AUTO_CONNECT_PHANTOM_ID")
        
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_AUTO_CONNECT_PHANTOM_ID no encontrada en variables de entorno")
        
        phantom_name = "LinkedIn Auto Connect"
        
        super().__init__(phantom_id, phantom_name)
        
        logger.info("LinkedIn Sender inicializado")
        # Defaults hardcodeados (no sensibles) para Spreadsheet mode
        self.DEFAULT_INPUT_MODE = "spreadsheet"  # "spreadsheet" | "profileUrl"
        self.DEFAULT_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DfQVldALoUA5lRnMlL2dEKzIVWZNSSq7QdsXPE26my4/edit?usp=sharing"  # URL del Google Sheet
        self.DEFAULT_SPREADSHEET_TAB = "leads"
        self.DEFAULT_ADDS_PER_LAUNCH = 20

        # Log de configuración efectiva
        try:
            effective_mode = (os.getenv("PHANTOMBUSTER_INPUT_MODE") or self.DEFAULT_INPUT_MODE).strip().lower()
            effective_sheet_url = (os.getenv("PHANTOMBUSTER_SPREADSHEET_URL") or self.DEFAULT_SPREADSHEET_URL).strip()
            effective_sheet_tab = (os.getenv("PHANTOMBUSTER_SPREADSHEET_TAB") or self.DEFAULT_SPREADSHEET_TAB).strip()
            logger.info(f"Configuración sender → input_mode='{effective_mode}', sheet_url='{effective_sheet_url}', tab='{effective_sheet_tab}'")
        except Exception as _log_exc:
            logger.warning(f"No se pudo registrar configuración inicial del sender: {_log_exc}")

    def _normalize_linkedin_url(self, url: str) -> str:
        try:
            if not url:
                return ''
            u = url.strip()
            for sep in ['#', '?']:
                if sep in u:
                    u = u.split(sep, 1)[0]
            u = u.lower()
            u = u.replace('wwww.linkedin.com', 'www.linkedin.com')
            if u.endswith('/'):
                u = u[:-1]
            return u
        except Exception:
            return url or ''
    
    def get_leads_en_cola(self, max_count: int = None) -> list:
        """
        Obtener leads desde Airtable 'Prospectos' listos para enviar:
        - Estado = "Listo para conectar"
        - Phantom Status vacío

        Returns:
            Lista de leads listos para enviar
        """
        try:
            logger.info("=== Obteniendo prospectos desde Airtable (Listo para conectar, Phantom Status vacío) ===")
            prospects = airtable_manager.get_contacts("Prospectos") or []

            leads = []
            # Cap: spreadsheet -> 2000; profileUrl -> PHANTOMBUSTER_ADDS_PER_LAUNCH (20 por defecto)
            input_mode = (os.getenv("PHANTOMBUSTER_INPUT_MODE") or self.DEFAULT_INPUT_MODE).strip().lower()
            if input_mode == "spreadsheet":
                cap_default = 2000
            else:
                cap_default = int(os.getenv("PHANTOMBUSTER_ADDS_PER_LAUNCH", str(self.DEFAULT_ADDS_PER_LAUNCH)))
            cap = max_count if isinstance(max_count, int) and max_count > 0 else cap_default
            for p in prospects:
                fields = p.get('fields', {})
                estado = fields.get('Estado') or fields.get('fldBKjhECLwJib5dG') or []
                phantom_status = fields.get('Phantom Status') or fields.get('fldo6tefvKlf880qu') or []
                linkedin_url = fields.get('fldnQnqKX2wSgiZUg') or fields.get('LinkedIn Profile URL') or ''

                estado_vals = estado if isinstance(estado, list) else ([estado] if estado else [])
                phantom_vals = phantom_status if isinstance(phantom_status, list) else ([phantom_status] if phantom_status else [])

                # Elegibles: Estado = Listo para conectar y Phantom Status vacío
                if ('Listo para conectar' in estado_vals) and (len(phantom_vals) == 0):
                    name = fields.get('Nombre') or fields.get('Name') or ''
                    leads.append({
                        'airtable_id': p.get('id'),
                        'name': name,
                        'linkedin_url': linkedin_url,
                        'company': fields.get('Empresa', ''),
                        'title': fields.get('Cargo', '')
                    })

                if len(leads) >= cap:
                    break

            logger.info(f"Leads listos para enviar: {len(leads)} (cap {cap})")
            # ESPÍA: muestra de leads y URLs crudas (máx 5)
            try:
                sample = [
                    {
                        'name': l.get('name'),
                        'linkedin_url_raw': l.get('linkedin_url'),
                        'company': l.get('company'),
                        'title': l.get('title')
                    }
                    for l in leads[:5]
                ]
                logger.info(f"Espía leads (máx 5): {sample}")
            except Exception:
                pass
            return leads

        except Exception as e:
            logger.error(f"Error obteniendo leads desde Airtable: {e}")
            return []
    
    def update_phantom_status_to_activo(self, leads: list) -> bool:
        """
        Actualizar Phantom Status de los leads a "Activo" en Airtable
        
        Args:
            leads: Lista de leads que se van a enviar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando Phantom Status a 'Activo' para {len(leads)} leads en Airtable")
            
            updated_count = 0
            for lead in leads:
                try:
                    # Buscar el prospecto en Airtable por LinkedIn URL
                    prospects = airtable_manager.get_contacts("Prospectos")
                    
                    matched_prospect = None
                    for prospect in prospects:
                        fields = prospect.get('fields', {})
                        prospect_url = fields.get('fldnQnqKX2wSgiZUg', '') or fields.get('LinkedIn Profile URL', '')
                        
                        if self._normalize_linkedin_url(prospect_url) == self._normalize_linkedin_url(lead.get('linkedin_url', '')):
                            matched_prospect = prospect
                            break
                    
                    if matched_prospect:
                        # Usar IDs de campos: Estado (fldBKjhECLwJib5dG), Phantom Status (fldo6tefvKlf880qu)
                        # Al enviar payload: Estado -> "Enviado a Phantom", Phantom Status -> "En Cola"
                        update_data = {
                            'fldBKjhECLwJib5dG': ["Enviado a Phantom"],
                            'fldo6tefvKlf880qu': ["En Cola"]
                        }
                        
                        success = airtable_manager.update_contact(matched_prospect['id'], update_data, table_name="Prospectos")
                        if success:
                            updated_count += 1
                            logger.info(f"Actualizado {lead['name']}: Phantom Status = 'Activo'")
                        else:
                            logger.error(f"Error actualizando {lead['name']}")
                    else:
                        logger.warning(f"No se encontró prospecto para {lead['name']} en Airtable")
                        
                except Exception as e:
                    logger.error(f"Error actualizando {lead['name']}: {e}")
                    continue
            
            logger.info(f"RESUMEN: {updated_count}/{len(leads)} leads actualizados a 'Activo'")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error actualizando Phantom Status: {e}")
            return False
    
    def create_auto_connect_payload(self, leads: list) -> dict:
        """
        Crear payload para el phantom LinkedIn Auto Connect
        
        Args:
            leads: Lista de leads a enviar
            
        Returns:
            Payload para el phantom
        """
        try:
            logger.info("Creando payload para LinkedIn Auto Connect...")
            
            # Extraer URLs de LinkedIn
            profile_urls = []
            for lead in leads:
                linkedin_url = lead.get('linkedin_url', '')
                if linkedin_url:
                    profile_urls.append(linkedin_url)
            
            if not profile_urls:
                logger.error("No se encontraron URLs de LinkedIn válidas")
                return {}
            
            # Límite por lanzamiento (configurable), el phantom usará este tope
            adds_per_launch = min(
                len(profile_urls),
                int(os.getenv("PHANTOMBUSTER_ADDS_PER_LAUNCH", str(self.DEFAULT_ADDS_PER_LAUNCH)))
            )

            # Mensaje configurable por .env (permite tokens como #firstName#)
            default_msg = (
                "Hola #firstName#, Me especializo en cobertura de tipo de cambio para importadores y exportadores. Me gustaría conectar contigo para enviarte el informe del peso chileno y cobre. En mi sitio web te puedes inscribir gratis.  https://www.gavintempleton.net/ \n\nSaludos,\nGavin Templeton"
            )
            connect_message = os.getenv("PHANTOMBUSTER_CONNECT_MESSAGE", default_msg)

            # Modo de entrada: 'profileUrl' (por defecto) o 'spreadsheet'
            input_mode = (os.getenv("PHANTOMBUSTER_INPUT_MODE") or self.DEFAULT_INPUT_MODE).strip().lower()

            if input_mode == "spreadsheet":
                sheet_url = (os.getenv("PHANTOMBUSTER_SPREADSHEET_URL") or self.DEFAULT_SPREADSHEET_URL).strip()
                sheet_tab = (os.getenv("PHANTOMBUSTER_SPREADSHEET_TAB") or self.DEFAULT_SPREADSHEET_TAB).strip()
                creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json").strip()

                if not sheet_url:
                    logger.error("PHANTOMBUSTER_SPREADSHEET_URL no está configurado para modo spreadsheet")
                    return {}

                if gspread is None:
                    logger.error("gspread no está instalado. Instala 'gspread' para usar modo spreadsheet.")
                    return {}

                try:
                    logger.info("Actualizando Google Sheet con URLs para el phantom...")
                    client = gspread.service_account(filename=creds_path)
                    # Abrir por URL o por key
                    try:
                        sh = client.open_by_url(sheet_url)
                    except Exception:
                        # Extraer ID si viene como key
                        parsed = urlparse(sheet_url)
                        # fallback simple: tomar segmento después de '/d/'
                        if "/d/" in sheet_url:
                            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                            sh = client.open_by_key(sheet_id)
                        else:
                            raise
                    try:
                        # Log de identificación del spreadsheet
                        sheet_title = getattr(sh, 'title', 'desconocido')
                        sheet_id = None
                        try:
                            sheet_id = getattr(sh, 'id') if hasattr(sh, 'id') else None
                        except Exception:
                            sheet_id = None
                        logger.info(f"Spreadsheet abierto: title='{sheet_title}'" + (f", id='{sheet_id}'" if sheet_id else ""))
                    except Exception:
                        pass
                    try:
                        ws = sh.worksheet(sheet_tab)
                    except Exception:
                        ws = sh.add_worksheet(title=sheet_tab, rows=str(len(profile_urls) + 10), cols="4")
                    try:
                        ws_gid = getattr(ws, 'id') if hasattr(ws, 'id') else None
                        if ws_gid:
                            # Construir URL directa al worksheet si es posible
                            if "/d/" in sheet_url:
                                base_url = sheet_url.split("/edit")[0]
                                logger.info(f"Worksheet abierto: tab='{sheet_tab}', gid='{ws_gid}', url='{base_url}#gid={ws_gid}'")
                            else:
                                logger.info(f"Worksheet abierto: tab='{sheet_tab}', gid='{ws_gid}'")
                    except Exception:
                        pass

                    # Header
                    header = ws.row_values(1)
                    if not header or (header and (len(header) == 0 or header[0].lower() != 'profileurl')):
                        ws.update('A1:D1', [["profileUrl", "nombre", "empresa", "cargo"]])

                    # Dedupe contra URLs ya presentes
                    try:
                        existing = ws.col_values(1)[1:]  # sin header
                    except Exception:
                        existing = []
                    existing_set = {self._normalize_linkedin_url(u) for u in existing}

                    # Snapshot previo (conteo y últimas 5 URLs no vacías)
                    try:
                        non_empty_existing = [u for u in existing if isinstance(u, str) and u.strip()]
                        prev_non_empty_count = len(non_empty_existing)
                        logger.info(f"Col A antes de append: {prev_non_empty_count} URLs no vacías. Últimas 5: {non_empty_existing[-5:]} ")
                    except Exception:
                        prev_non_empty_count = None

                    rows_to_append = []
                    sample_norm_candidates = []
                    for lead in leads:
                        norm_url = self._normalize_linkedin_url(lead.get('linkedin_url', ''))
                        if len(sample_norm_candidates) < 5 and norm_url:
                            sample_norm_candidates.append(norm_url)
                        if not norm_url or norm_url in existing_set:
                            continue
                        row = [
                            str(norm_url),
                            str(lead.get('name', '') or ''),
                            str(lead.get('company', '') or ''),
                            str(lead.get('title', '') or '')
                        ]
                        rows_to_append.append(row)
                        existing_set.add(norm_url)
                        if len(existing_set) >= 2000:
                            break

                    if rows_to_append:
                        # ESPÍA: vista previa de filas a insertar
                        try:
                            preview = rows_to_append[:5]
                            logger.info(f"Espía rows_to_append (máx 5): {preview}")
                            logger.info(f"Total rows_to_append: {len(rows_to_append)}")
                        except Exception:
                            pass

                        spy_mode = (os.getenv("SENDER_SPY_MODE") or "").strip().lower()
                        if spy_mode == "individual":
                            # Modo espía: insertar fila por fila con verificación
                            appended = 0
                            for idx, row in enumerate(rows_to_append, start=1):
                                try:
                                    ws.append_row(row, value_input_option='USER_ENTERED')
                                    # Verificar tamaño de Col A tras el append
                                    try:
                                        col_a_after = ws.col_values(1)[1:]
                                        non_empty_after = [u for u in col_a_after if isinstance(u, str) and u.strip()]
                                        last_val = non_empty_after[-1] if non_empty_after else None
                                        logger.info(f"[SPY] Appended {idx}/{len(rows_to_append)}: '{row[0]}'. ColA now {len(non_empty_after)}. Last='{last_val}'")
                                    except Exception as ve:
                                        logger.warning(f"[SPY] Verificación posterior falló: {ve}")
                                    appended += 1
                                except Exception as ae:
                                    logger.error(f"[SPY] Error append_row idx={idx}: {ae}")
                                    continue
                            logger.info(f"[SPY] Appended individual total: {appended}/{len(rows_to_append)}")
                        else:
                            # Modo normal: append por lote con rango explícito A1:D1
                            ws.append_rows(
                                rows_to_append,
                                value_input_option='USER_ENTERED',
                                table_range='A1:D1'
                            )
                        try:
                            all_vals = ws.get_all_values()
                            total_rows = len(all_vals)
                            # Tomar últimas 5 filas no vacías de la columna A
                            col_a_after = ws.col_values(1)[1:]
                            non_empty_after = [u for u in col_a_after if isinstance(u, str) and u.strip()]
                            after_count = len(non_empty_after)
                            logger.info(f"Col A después de append: {after_count} URLs no vacías. Últimas 5: {non_empty_after[-5:]} ")
                            # Fallback si el append por lote no escribió valores
                            if prev_non_empty_count is not None and after_count == prev_non_empty_count:
                                try:
                                    start_row = 2 + prev_non_empty_count
                                    end_row = start_row + len(rows_to_append) - 1
                                    range_name = f"A{start_row}:D{end_row}"
                                    logger.warning(f"Append parece vacío. Aplicando fallback update en rango {range_name} ...")
                                    ws.update(range_name, rows_to_append, value_input_option='USER_ENTERED')
                                    # Re-verificar
                                    col_a_after2 = ws.col_values(1)[1:]
                                    non_empty_after2 = [u for u in col_a_after2 if isinstance(u, str) and u.strip()]
                                    logger.info(f"Fallback: Col A ahora {len(non_empty_after2)}. Últimas 5: {non_empty_after2[-5:]} ")
                                except Exception as fb:
                                    logger.error(f"Error en fallback range update: {fb}")
                        except Exception:
                            total_rows = 'desconocido'
                        logger.info(f"Google Sheet actualizado: +{len(rows_to_append)} URLs (tab '{sheet_tab}'). Filas totales ahora: {total_rows}")
                    else:
                        logger.info("Google Sheet sin cambios (no hay nuevas URLs para agregar)")
                        logger.info(f"Muestra de URLs normalizadas candidatas (máx 5): {sample_norm_candidates}")
                except Exception as e:
                    logger.error(f"Error actualizando Google Sheet: {e}")
                    return {}

                payload = {
                    "inputType": "spreadsheetUrl",
                    "spreadsheetUrl": sheet_url,
                    "numberOfAddsPerLaunch": adds_per_launch,
                    "message": connect_message,
                    "sessionCookie": os.getenv("LINKEDIN_SESSION_COOKIE"),
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                }
            else:
                payload = {
                    "inputType": "profileUrl",
                    "profileUrl": profile_urls,
                    "numberOfAddsPerLaunch": adds_per_launch,
                    "message": connect_message,
                    "sessionCookie": os.getenv("LINKEDIN_SESSION_COOKIE"),
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                }
            
            logger.info(f"Payload creado con {len(profile_urls)} URLs")
            return payload
            
        except Exception as e:
            logger.error(f"Error creando payload: {e}")
            return {}
    
    def launch_auto_connect_phantom(self, payload: dict) -> dict:
        """
        Lanzar phantom LinkedIn Auto Connect
        
        Args:
            payload: Payload para el phantom
            
        Returns:
            Resultado del lanzamiento
        """
        try:
            logger.info("Lanzando phantom LinkedIn Auto Connect...")
            
            # Usar endpoint correcto de API v1
            launch_url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/launch"
            
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Lanzando {self.phantom_name} con payload: {len(payload.get('profileUrl', []))} URLs")
            
            import requests
            response = requests.post(launch_url, headers=headers, json=payload)
            
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                container_id = result.get('data', {}).get('containerId')
                if container_id:
                    logger.info(f"Phantom lanzado exitosamente - Container ID: {container_id}")
                    return result
                else:
                    logger.error("No se obtuvo Container ID del lanzamiento")
                    return None
            else:
                logger.error(f"Error lanzando {self.phantom_name}: {response.status_code}")
                logger.error(f"Respuesta: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error lanzando phantom: {e}")
            return None
    
    def send_leads_to_phantom(self, leads: list) -> dict:
        """
        Enviar leads al phantom - SOLO 2 FUNCIONES:
        1. Cargar payload
        2. Ejecutar phantom
        
        Args:
            leads: Lista de leads a enviar
            
        Returns:
            Resultado del envío
        """
        try:
            logger.info(f"=== ENVIANDO {len(leads)} LEADS AL PHANTOM ===")
            
            # 1. CARGAR PAYLOAD
            logger.info("1. Cargando payload...")
            payload = self.create_auto_connect_payload(leads)
            
            if not payload:
                return {"status": "error", "message": "Error creando payload"}
            
            logger.info(f"Payload creado exitosamente")
            
            # 2. EJECUTAR PHANTOM
            logger.info("2. Ejecutando phantom...")
            launch_result = self.launch_auto_connect_phantom(payload)
            
            if launch_result:
                container_id = launch_result.get('data', {}).get('containerId')
                if container_id:
                    logger.info(f"Phantom ejecutado exitosamente - Container ID: {container_id}")
                    return {
                        "status": "success",
                        "message": "Phantom ejecutado exitosamente",
                        "container_id": container_id,
                        "leads_sent": len(leads)
                    }
                else:
                    return {"status": "error", "message": "No se obtuvo Container ID"}
            else:
                return {"status": "error", "message": "Error ejecutando phantom"}
                
        except Exception as e:
            logger.error(f"Error enviando leads al phantom: {e}")
            return {"status": "error", "message": str(e)}
    
    def run_daily_send(self) -> dict:
        """
        Ejecutar envío diario de leads
        
        Returns:
            Resultado del envío diario
        """
        try:
            logger.info("=== INICIANDO ENVÍO DIARIO DE LEADS ===")
            
            # 1. Obtener leads en cola
            logger.info("1. Obteniendo leads en cola...")
            leads_en_cola = self.get_leads_en_cola()
            
            if not leads_en_cola:
                return {
                    "status": "info",
                    "message": "No hay leads en cola para enviar",
                    "leads_sent": 0
                }
            
            # 2. Actualizar Phantom Status a "Activo"
            logger.info("2. Actualizando Phantom Status a 'Activo'...")
            update_success = self.update_phantom_status_to_activo(leads_en_cola)
            
            if not update_success:
                logger.warning("Error actualizando Phantom Status, pero continuando...")
            
            # 3. Enviar leads al phantom (solo si no estamos en spreadsheet-mode)
            input_mode = (os.getenv("PHANTOMBUSTER_INPUT_MODE") or self.DEFAULT_INPUT_MODE).strip().lower()
            if input_mode == "spreadsheet":
                logger.info("3. Modo spreadsheet: solo actualizar Google Sheet (sin lanzar phantom)...")
                _ = self.create_auto_connect_payload(leads_en_cola)  # Esto actualiza el Sheet
                logger.info("Hoja actualizada. Saltando lanzamiento del phantom por control manual.")
                logger.info("=== PROCESO COMPLETADO (SOLO SHEET) ===")
                return {
                    "status": "success",
                    "message": "Sheet actualizado; lanzamiento manual pendiente",
                    "leads_sent": len(leads_en_cola)
                }

            logger.info("3. Enviando leads al phantom...")
            send_result = self.send_leads_to_phantom(leads_en_cola)
            
            if send_result["status"] == "success":
                logger.info("=== ENVÍO DIARIO COMPLETADO EXITOSAMENTE ===")
                return {
                    "status": "success",
                    "message": "Envío diario completado exitosamente",
                    "leads_sent": len(leads_en_cola),
                    "container_id": send_result.get("container_id")
                }
            else:
                logger.error("=== ERROR EN ENVÍO DIARIO ===")
                return {
                    "status": "error",
                    "message": f"Error en envío diario: {send_result['message']}",
                    "leads_sent": 0
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando envío diario: {e}")
            return {
                "status": "error",
                "message": str(e),
                "leads_sent": 0
            }

if __name__ == "__main__":
    print("🚀 LINKEDIN SENDER - ENVÍO DIARIO")
    print("=" * 50)
    
    sender = LinkedInSender()
    result = sender.run_daily_send()
    
    print(f"\n📊 RESULTADO: {result['status'].upper()}")
    print(f"📋 Mensaje: {result['message']}")
    print(f"📈 Leads enviados: {result.get('leads_sent', 0)}")
    
    if result.get('container_id'):
        print(f"🆔 Container ID: {result['container_id']}")
    
    if result['status'] == 'success':
        print("\n✅ ENVÍO DIARIO COMPLETADO EXITOSAMENTE!")
        print("🔄 Ejecutar linkedin_monitor.py para monitorear resultados")
    else:
        print(f"\n❌ ERROR: {result['message']}")


#!/usr/bin/env python3
"""
LinkedIn Monitor - Script para monitorear resultados del phantom
Ejecutar múltiples veces al día - Obtiene CSV y actualiza Airtable
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

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
        logging.FileHandler('linkedin_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LinkedInMonitor(PhantomBaseManager):
    """Script especializado para monitorear resultados del phantom"""
    
    def __init__(self):
        """Inicializar el monitor"""
        # Phantom ID del LinkedIn Auto Connect
        phantom_id = os.getenv("PHANTOMBUSTER_AUTO_CONNECT_PHANTOM_ID")
        
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_AUTO_CONNECT_PHANTOM_ID no encontrada en variables de entorno")
        
        phantom_name = "LinkedIn Auto Connect"
        
        super().__init__(phantom_id, phantom_name)
        
        logger.info("LinkedIn Monitor inicializado")
    
    def get_latest_container_id(self) -> str:
        """
        Buscar el último Container ID del phantom
        
        Returns:
            Container ID del último container o None si hay error
        """
        try:
            logger.info("Buscando último Container ID del phantom...")
            
            import requests
            
            # Usar endpoint para obtener containers del phantom
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Obtener containers del phantom usando API v1
            fetch_url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/containers"
            response = requests.get(fetch_url, headers=headers)
            
            if response.status_code == 200:
                containers_data = response.json()
                
                # API v1 puede devolver datos directamente o con wrapper
                if isinstance(containers_data, list):
                    containers = containers_data
                elif isinstance(containers_data, dict) and 'data' in containers_data:
                    containers = containers_data.get('data', [])
                else:
                    containers = []
                
                if containers:
                    # Obtener el primer container (más reciente)
                    latest_container = containers[0]
                    container_id = latest_container.get('id') or latest_container.get('containerId')
                    status = latest_container.get('status', 'unknown')
                    
                    logger.info(f"Último Container ID encontrado: {container_id}")
                    logger.info(f"Status del container: {status}")
                    
                    return container_id
                else:
                    logger.warning("No se encontraron containers para el phantom")
                    return None
            else:
                logger.error(f"Error obteniendo containers: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error buscando último Container ID: {e}")
            return None
    
    def check_container_status(self, container_id: str) -> str:
        """
        Verificar status del container
        
        Args:
            container_id: ID del container a verificar
            
        Returns:
            Status del container
        """
        try:
            logger.info(f"Verificando status del container {container_id}...")
            
            import requests
            
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Verificar estado del container
            fetch_url = f"https://api.phantombuster.com/api/v2/containers/fetch?id={container_id}"
            response = requests.get(fetch_url, headers=headers)
            
            if response.status_code == 200:
                container_data = response.json()
                status = container_data.get('status', 'unknown')
                
                logger.info(f"Status del container: {status}")
                return status
            else:
                logger.error(f"Error verificando status: HTTP {response.status_code}")
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error verificando status del container: {e}")
            return 'unknown'
    
    def get_phantom_results_from_s3(self, container_id: str = None) -> list:
        """
        Obtener resultados del phantom desde S3 usando Container ID dinámico
        
        Args:
            container_id: ID del container (opcional, si no se proporciona usa el último)
            
        Returns:
            Lista de resultados procesados
        """
        try:
            logger.info("Obteniendo resultados del phantom desde S3...")
            
            import requests
            import csv
            import io
            
            # Si no se proporciona container_id, buscar el último
            if not container_id:
                container_id = self.get_latest_container_id()
                if not container_id:
                    logger.error("No se pudo obtener Container ID")
                    return []
            
            logger.info(f"Usando Container ID: {container_id}")
            
            # Obtener información del phantom para construir URL S3
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Obtener info del phantom
            fetch_url = f"https://api.phantombuster.com/api/v2/agents/fetch?id={self.phantom_id}"
            response = requests.get(fetch_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error obteniendo info del phantom: HTTP {response.status_code}")
                return []
            
            phantom_data = response.json()
            org_s3_folder = phantom_data.get('orgS3Folder', '')
            s3_folder = phantom_data.get('s3Folder', '')
            
            if not org_s3_folder or not s3_folder:
                logger.error("No se encontraron S3 folders")
                return []
            
            logger.info(f"orgS3Folder: {org_s3_folder}")
            logger.info(f"s3Folder: {s3_folder}")
            
            # Construir URL del CSV (nombres comunes)
            csv_filenames = [
                "database-linkedin-network-booster.csv",
                "result.csv",
                "linkedin_auto_connect.csv",
                "auto_connect_results.csv"
            ]
            
            csv_url = None
            for csv_filename in csv_filenames:
                csv_url = f"https://phantombuster.s3.amazonaws.com/{org_s3_folder}/{s3_folder}/{csv_filename}"
                logger.info(f"Probando CSV: {csv_filename}")
                
                # Verificar si el archivo existe
                test_response = requests.head(csv_url)
                if test_response.status_code == 200:
                    logger.info(f"Archivo encontrado: {csv_filename}")
                    break
                else:
                    csv_url = None
            
            if not csv_url:
                logger.error("No se encontró ningún archivo CSV de resultados")
                return []
            
            # Descargar CSV
            logger.info(f"Descargando CSV desde: {csv_url}")
            csv_response = requests.get(csv_url)
            
            if csv_response.status_code != 200:
                logger.error(f"Error descargando CSV: HTTP {csv_response.status_code}")
                return []
            
            logger.info("CSV descargado exitosamente")
            
            # Procesar CSV
            csv_content = csv_response.text
            logger.info(f"CSV contenido: {len(csv_content)} caracteres")
            
            # Convertir a diccionarios
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            results = list(csv_reader)
            
            logger.info(f"Resultados procesados: {len(results)} registros")
            return results
            
        except Exception as e:
            logger.error(f"Error obteniendo resultados desde S3: {e}")
            return []
    
    def parse_csv_results_real(self, csv_results: list) -> list:
        """
        Procesar resultados del CSV usando la estructura real descubierta
        
        Args:
            csv_results: Resultados crudos del CSV
            
        Returns:
            Lista de resultados procesados
        """
        try:
            logger.info(f"Procesando {len(csv_results)} resultados del CSV")
            
            processed_results = []
            
            for result in csv_results:
                # Usar la estructura real del CSV descubierta
                processed_result = {
                    'linkedin_url': result.get('linkedinProfileUrl', ''),
                    'full_name': result.get('fullName', ''),
                    'first_name': result.get('firstName', ''),
                    'last_name': result.get('lastName', ''),
                    'connection_degree': result.get('connectionDegree', ''),
                    'error': result.get('error', ''),
                    'timestamp': result.get('timestamp', ''),
                    'profile_url': result.get('profileUrl', ''),
                    'processed_at': datetime.now().isoformat()
                }
                
                processed_results.append(processed_result)
            
            logger.info(f"Resultados procesados: {len(processed_results)} registros")
            return processed_results
            
        except Exception as e:
            logger.error(f"Error procesando resultados del CSV: {e}")
            return []

    def _normalize_linkedin_url(self, url: str) -> str:
        """
        Normalizar LinkedIn URL para matching robusto:
        - minúsculas
        - quitar query/fragment
        - corregir www/wwww
        - eliminar slash final
        """
        try:
            if not url:
                return ''
            u = url.strip()
            # quitar fragmentos y query
            for sep in ['#', '?']:
                if sep in u:
                    u = u.split(sep, 1)[0]
            u = u.lower()
            u = u.replace('wwww.linkedin.com', 'www.linkedin.com')
            # quitar slash final
            if u.endswith('/'):
                u = u[:-1]
            return u
        except Exception:
            return url or ''
    
    def determine_status_from_error(self, error: str) -> str:
        """
        Determinar estado basado en el campo 'error' del CSV
        
        Args:
            error: Campo 'error' del CSV
            
        Returns:
            Estado para Airtable
        """
        if not error:
            return "DM Enviado"  # Si no hay error, se envió el DM
        
        error_lower = error.lower()
        
        # Lógica basada en estructura real del CSV
        if 'own profile' in error_lower:
            return "Conectado"  # Ya está conectado
        elif 'already in network' in error_lower:
            return "Conectado"  # Ya está conectado
        elif 'rejected' in error_lower or 'declined' in error_lower:
            return "Rechazado"  # Rechazó la conexión
        elif 'blocked' in error_lower:
            return "Bloqueado"  # Usuario bloqueado
        elif 'connected' in error_lower or 'accepted' in error_lower:
            return "Conectado"  # Aceptó la conexión
        else:
            # Si hay algún error pero no es específico, asumir que se envió el DM
            return "DM Enviado"
    
    def update_airtable_with_real_results(self, processed_results: list) -> bool:
        """
        Actualizar Airtable con los resultados procesados
        
        Args:
            processed_results: Resultados procesados del CSV
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando Airtable con {len(processed_results)} resultados")
            
            # Obtener todos los prospectos una sola vez
            prospects = airtable_manager.get_contacts("Prospectos")
            logger.info(f"Encontrados {len(prospects)} prospectos en Airtable")
            
            updated_count = 0
            matched_count = 0
            
            for result in processed_results:
                try:
                    # Buscar match por LinkedIn URL
                    linkedin_url = result.get('linkedin_url', '')
                    if not linkedin_url:
                        logger.warning(f"Resultado sin LinkedIn URL: {result}")
                        continue
                    norm_result_url = self._normalize_linkedin_url(linkedin_url)

                    # Buscar prospecto con matching URL
                    matched_prospect = None
                    for prospect in prospects:
                        fields = prospect.get('fields', {})
                        # Usar Field ID hardcodeado primero y fallback al nombre
                        prospect_url = fields.get('fldnQnqKX2wSgiZUg', '') or fields.get('LinkedIn Profile URL', '')
                        norm_prospect_url = self._normalize_linkedin_url(prospect_url)

                        if norm_prospect_url and norm_prospect_url == norm_result_url:
                            matched_prospect = prospect
                            matched_count += 1
                            break
                    
                    if matched_prospect:
                        # Hay match - actualizar estado
                        fields = matched_prospect.get('fields', {})
                        prospect_name = fields.get('Nombre', 'N/A')
                        
                        # Regla solicitada:
                        # - Estado ya fue puesto en "Enviado a Phantom" por el sender.
                        # - Aquí solo movemos Phantom Status → "Solicitud Enviada" cuando el phantom ha intentado el envío.
                        err = (result.get('error', '') or '').strip()
                        sent = False
                        if not err:
                            sent = True
                        else:
                            # Algunos mensajes implican ya estar conectado; igualmente consideramos el intento como completado
                            low = err.lower()
                            if any(k in low for k in ['accepted', 'connected', 'already in network']):
                                sent = True

                        update_data = {
                            'fldo6tefvKlf880qu': ["Solicitud Enviada"] if sent else ["En Cola"]  # Phantom Status
                        }
                        
                        # Actualizar en Airtable (tabla Prospectos)
                        success = airtable_manager.update_contact(matched_prospect['id'], update_data, table_name="Prospectos")
                        
                        if success:
                            updated_count += 1
                            logger.info(f"Actualizado {prospect_name}: Phantom Status = {'Solicitud Enviada' if sent else 'En Cola'} (error: {result.get('error', 'N/A')})")
                        else:
                            logger.error(f"Error actualizando {prospect_name}")
                    else:
                        # No hay match - no hacer nada
                        logger.info(f"No se encontró match para {linkedin_url} - No se actualiza")
                
                except Exception as e:
                    logger.error(f"Error procesando resultado: {e}")
                    continue
            
            logger.info(f"RESUMEN: {matched_count} matches encontrados, {updated_count} actualizados")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error actualizando Airtable con resultados: {e}")
            return False
    
    def run_monitoring_cycle(self) -> dict:
        """
        Ejecutar ciclo de monitoreo con flujo correcto:
        1. Buscar último Container ID
        2. Verificar status del phantom
        3. Obtener CSV y actualizar Airtable
        
        Returns:
            Resultado del monitoreo
        """
        try:
            logger.info("=== INICIANDO CICLO DE MONITOREO ===")
            
            # 1. BUSCAR ÚLTIMO CONTAINER ID
            logger.info("1. Buscando último Container ID...")
            container_id = self.get_latest_container_id()
            
            if not container_id:
                return {
                    "status": "error",
                    "message": "No se pudo obtener Container ID",
                    "results_processed": 0
                }
            
            # 2. VERIFICAR STATUS DEL PHANTOM
            logger.info("2. Verificando status del phantom...")
            status = self.check_container_status(container_id)
            
            logger.info(f"Status del phantom: {status}")
            
            # 3. OBTENER RESULTADOS DEL PHANTOM DESDE S3
            logger.info("3. Obteniendo resultados del phantom desde S3...")
            csv_results = self.get_phantom_results_from_s3(container_id)
            
            if not csv_results:
                return {
                    "status": "info",
                    "message": "No hay resultados disponibles del phantom",
                    "results_processed": 0,
                    "container_id": container_id,
                    "status": status
                }
            
            # 4. PROCESAR RESULTADOS USANDO ESTRUCTURA REAL
            logger.info("4. Procesando resultados del CSV...")
            processed_results = self.parse_csv_results_real(csv_results)
            
            if not processed_results:
                return {
                    "status": "error",
                    "message": "Error procesando resultados del CSV",
                    "results_processed": 0,
                    "container_id": container_id,
                    "status": status
                }
            
            # 5. ACTUALIZAR AIRTABLE
            logger.info("5. Actualizando Airtable...")
            update_success = self.update_airtable_with_real_results(processed_results)
            
            if update_success:
                logger.info("=== CICLO DE MONITOREO COMPLETADO EXITOSAMENTE ===")
                return {
                    "status": "success",
                    "message": "Ciclo de monitoreo completado exitosamente",
                    "results_processed": len(processed_results),
                    "container_id": container_id,
                    "phantom_status": status
                }
            else:
                logger.warning("=== CICLO DE MONITOREO COMPLETADO CON ADVERTENCIAS ===")
                return {
                    "status": "warning",
                    "message": "Ciclo completado pero con errores en actualizaciones",
                    "results_processed": len(processed_results),
                    "container_id": container_id,
                    "phantom_status": status
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando ciclo de monitoreo: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results_processed": 0
            }

if __name__ == "__main__":
    print("📊 LINKEDIN MONITOR - CICLO DE MONITOREO")
    print("=" * 50)
    
    monitor = LinkedInMonitor()
    result = monitor.run_monitoring_cycle()
    
    print(f"\n📊 RESULTADO: {result['status'].upper()}")
    print(f"📋 Mensaje: {result['message']}")
    print(f"📈 Resultados procesados: {result.get('results_processed', 0)}")
    
    if result.get('container_id'):
        print(f"🆔 Container ID: {result['container_id']}")
    
    if result.get('phantom_status'):
        print(f"📊 Status del Phantom: {result['phantom_status']}")
    
    if result['status'] == 'success':
        print("\n✅ MONITOREO COMPLETADO EXITOSAMENTE!")
        print("🔄 Airtable actualizado con resultados del phantom")
    elif result['status'] == 'warning':
        print("\n⚠️ MONITOREO COMPLETADO CON ADVERTENCIAS!")
        print("🔧 Revisar logs para más detalles")
    else:
        print(f"\n❌ ERROR: {result['message']}")
        print("🔧 Revisar logs para más detalles")

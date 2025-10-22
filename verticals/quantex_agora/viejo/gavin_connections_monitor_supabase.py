#!/usr/bin/env python3
"""
Gavin Connections Monitor Supabase - Script para monitorear conexiones de LinkedIn
Detecta cuando alguien acepta una solicitud de conexión y actualiza Supabase
"""

import os
import sys
import json
import requests
import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Importar clases existentes
from verticals.quantex_agora.phantom_base_manager import PhantomBaseManager

# Configurar salida estándar a UTF-8 en Windows para evitar UnicodeEncodeError
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Configurar logging (UTF-8 en archivo y consola)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gavin_connections_monitor_supabase.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GavinConnectionsMonitorSupabase(PhantomBaseManager):
    """Monitor para el phantom de exportación de conexiones de LinkedIn - Versión Supabase"""
    
    def __init__(self):
        """Inicializar el monitor de conexiones"""
        # Phantom ID del Gavin LinkedIn Connections Export
        phantom_id = os.getenv("PHANTOMBUSTER_CONECTIONS_EXPORT_PHANTOM_ID")
        
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_CONECTIONS_EXPORT_PHANTOM_ID no encontrada en variables de entorno")
        
        phantom_name = "Gavin LinkedIn Connections Export"
        
        super().__init__(phantom_id, phantom_name)
        
        # Configuración específica
        self.session_cookie = os.getenv("LINKEDIN_SESSION_COOKIE")
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        
        if not self.session_cookie:
            logger.warning("LINKEDIN_SESSION_COOKIE no encontrada en variables de entorno")
        
        # Inicializar Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY son requeridos")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        logger.info(f"Gavin Connections Monitor Supabase inicializado correctamente")
    
    def create_connections_export_payload(self) -> Dict:
        """
        Crear payload para el phantom de exportación de conexiones
        
        Returns:
            Payload para el phantom
        """
        try:
            payload = {
                "sessionCookie": self.session_cookie,
                "userAgent": self.user_agent,
                "csvName": f"gavin_connections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "numberOfConnectionsToExport": 1000,  # Exportar hasta 1000 conexiones
                "exportConnections": True
            }
            
            logger.info("Payload de exportación de conexiones creado exitosamente")
            return payload
            
        except Exception as e:
            logger.error(f"Error creando payload de exportación: {e}")
            return {}
    
    def launch_connections_export(self) -> Optional[Dict]:
        """
        Lanzar phantom de exportación de conexiones
        
        Returns:
            Resultado del lanzamiento o None si hay error
        """
        try:
            logger.info("Lanzando phantom de exportación de conexiones...")
            
            # Crear payload
            payload = self.create_connections_export_payload()
            
            if not payload:
                logger.error("No se pudo crear payload para exportación")
                return None
            
            # Usar endpoint correcto de API v1
            launch_url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/launch"
            
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Lanzando {self.phantom_name} con payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(launch_url, headers=headers, json=payload)
            
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                container_id = result.get('data', {}).get('containerId')
                if container_id:
                    logger.info(f"Phantom de exportación lanzado exitosamente - Container ID: {container_id}")
                    return result
                else:
                    logger.error("No se obtuvo Container ID del lanzamiento")
                    return None
            else:
                logger.error(f"Error lanzando {self.phantom_name}: {response.status_code}")
                logger.error(f"Respuesta: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error lanzando phantom de exportación: {e}")
            return None
    
    def get_connections_csv_from_s3(self, container_id: str = None) -> List[Dict]:
        """
        Obtener CSV de conexiones desde S3
        
        Args:
            container_id: ID del container del phantom
            
        Returns:
            Lista de conexiones del CSV
        """
        try:
            logger.info(f"Obteniendo CSV de conexiones desde S3...")
            
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
                "database-linkedin-connections.csv",
                "result.csv",
                "gavin_connections.csv",
                "connections_export.csv"
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
                logger.error("No se encontró ningún archivo CSV de conexiones")
                return []
            
            # Descargar CSV
            logger.info(f"Descargando CSV desde: {csv_url}")
            csv_response = requests.get(csv_url)
            
            if csv_response.status_code != 200:
                logger.error(f"Error descargando CSV: HTTP {csv_response.status_code}")
                return []
            
            logger.info("CSV de conexiones descargado exitosamente")
            
            # Procesar CSV
            csv_content = csv_response.text
            logger.info(f"CSV contenido: {len(csv_content)} caracteres")
            
            # Mostrar primeras líneas
            lines = csv_content.split('\n')
            logger.info(f"Primeras líneas del CSV:")
            for i, line in enumerate(lines[:3]):
                logger.info(f"  {i+1}: {line}")
            
            # Convertir a diccionarios
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            connections = list(csv_reader)
            
            logger.info(f"Conexiones procesadas: {len(connections)} registros")
            
            # Mostrar estructura del CSV
            if connections:
                logger.info("Estructura del CSV de conexiones:")
                for key in connections[0].keys():
                    logger.info(f"  - {key}")
            
            return connections
            
        except Exception as e:
            logger.error(f"Error obteniendo CSV de conexiones: {e}")
            return []
    
    def parse_connections_data(self, connections: List[Dict]) -> List[Dict]:
        """
        Procesar datos de conexiones
        
        Args:
            connections: Lista de conexiones del CSV
            
        Returns:
            Lista de conexiones procesadas
        """
        try:
            logger.info(f"Procesando {len(connections)} conexiones")
            
            processed_connections = []
            
            for connection in connections:
                # Procesar cada conexión
                processed_connection = {
                    'linkedin_url': connection.get('profileUrl', ''),
                    'full_name': connection.get('fullName', ''),
                    'first_name': connection.get('firstName', ''),
                    'last_name': connection.get('lastName', ''),
                    'company': connection.get('companyName', ''),
                    'title': connection.get('title', ''),
                    'location': connection.get('location', ''),
                    'connection_date': connection.get('connectionSince', ''),
                    'connection_degree': connection.get('connectionDegree', ''),
                    'processed_at': datetime.now().isoformat()
                }
                
                processed_connections.append(processed_connection)
            
            logger.info(f"Conexiones procesadas: {len(processed_connections)} registros")
            return processed_connections
            
        except Exception as e:
            logger.error(f"Error procesando conexiones: {e}")
            return []
    
    def update_supabase_with_new_connections(self, connections: List[Dict]) -> bool:
        """
        Actualizar Supabase con nuevas conexiones detectadas
        
        Args:
            connections: Lista de conexiones procesadas
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando Supabase con {len(connections)} conexiones")
            
            # Obtener todos los leads de LinkedIn
            response = self.supabase.table('linkedin_leads').select('*').execute()
            leads = response.data
            logger.info(f"Encontrados {len(leads)} leads en Supabase")
            
            # Crear lista de URLs de conexiones actuales
            current_connection_urls = set()
            for connection in connections:
                linkedin_url = connection.get('linkedin_url', '')
                if linkedin_url:
                    current_connection_urls.add(linkedin_url)
            
            logger.info(f"URLs de conexiones actuales: {len(current_connection_urls)}")
            
            # Debug: mostrar algunas URLs de conexiones y leads
            logger.info("[DEBUG] Primeras 3 URLs de conexiones:")
            for i, url in enumerate(list(current_connection_urls)[:3]):
                logger.info(f"  {i+1}: {url}")
            
            logger.info("[DEBUG] Primeras 3 URLs de leads:")
            for i, lead in enumerate(leads[:3]):
                lead_url = lead.get('linkedin_profile_url', '')
                phantom_status = lead.get('phantom_status', '')
                connection_status = lead.get('connection_status', '')
                logger.info(f"  {i+1}: {lead_url} (Phantom: {phantom_status}, Conexión: {connection_status})")
            
            updated_count = 0
            matched_count = 0
            
            # PROCESAR NUEVAS CONEXIONES - DETECTAR ACEPTACIONES
            logger.info("=== DETECTANDO ACEPTACIONES DE CONEXIONES ===")
            for connection in connections:
                try:
                    # Buscar match por LinkedIn URL
                    linkedin_url = connection.get('linkedin_url', '')
                    if not linkedin_url:
                        continue
                    
                    # Buscar lead con matching URL
                    matched_lead = None
                    for lead in leads:
                        lead_url = lead.get('linkedin_profile_url', '')
                        current_phantom_status = lead.get('phantom_status', '')
                        current_connection_status = lead.get('connection_status', '')
                        
                        # Normalizar URLs para comparación
                        def normalize_url(url):
                            if not url:
                                return ''
                            # Remover www. y trailing slash
                            url = url.replace('https://www.', 'https://').replace('https://', '').rstrip('/')
                            return url
                        
                        normalized_lead_url = normalize_url(lead_url)
                        normalized_connection_url = normalize_url(linkedin_url)
                        
                        # Debug: mostrar comparación
                        if normalized_lead_url == normalized_connection_url:
                            logger.info(f"[DEBUG] URL MATCH encontrado: {linkedin_url}")
                            logger.info(f"[DEBUG] Phantom Status actual: '{current_phantom_status}'")
                            logger.info(f"[DEBUG] Connection Status actual: '{current_connection_status}'")
                            
                            # Solo actualizar si phantom_status es "Solicitud Enviada" y connection_status no es "Conectado"
                            if current_phantom_status == 'Solicitud Enviada' and current_connection_status != 'Conectado':
                                matched_lead = lead
                                matched_count += 1
                                logger.info(f"[DEBUG] MATCH VALIDO - lead sera actualizado")
                                break
                            else:
                                logger.info(f"[DEBUG] Match encontrado pero no cumple condiciones para actualizar")
                    
                    if matched_lead:
                        # Hay match - actualizar connection_status a "Conectado"
                        lead_name = matched_lead.get('full_name', 'N/A')
                        connection_date = connection.get('connection_date', '')
                        
                        # Convertir connection_date a timestamp si existe
                        connection_accepted_at = None
                        if connection_date:
                            try:
                                # Parsear fecha de conexión
                                connection_accepted_at = datetime.fromisoformat(connection_date.replace('Z', '+00:00')).isoformat()
                            except:
                                connection_accepted_at = datetime.now().isoformat()
                        else:
                            connection_accepted_at = datetime.now().isoformat()
                        
                        update_data = {
                            'connection_status': 'Conectado',
                            'connection_accepted_at': connection_accepted_at,
                            'last_activity_at': datetime.now().isoformat()
                        }
                        
                        # Actualizar en Supabase
                        update_response = self.supabase.table('linkedin_leads') \
                            .update(update_data) \
                            .eq('id', matched_lead['id']) \
                            .execute()
                        
                        if not update_response.data:
                            logger.error(f"Error actualizando {lead_name}: {update_response.error}")
                        else:
                            updated_count += 1
                            logger.info(f"[ACEPTACION] {lead_name} cambio a 'Conectado' - Fecha: {connection_accepted_at}")
                    else:
                        # No hay match - nueva conexión no está en leads o ya está conectado
                        logger.info(f"Nueva conexión no está en leads o ya está conectado: {linkedin_url}")
                
                except Exception as e:
                    logger.error(f"Error procesando conexión: {e}")
                    continue
            
            logger.info(f"RESUMEN: {matched_count} matches encontrados, {updated_count} leads actualizados a 'Conectado'")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error actualizando Supabase con conexiones: {e}")
            return False
    
    def monitor_phantom_execution(self, container_id: str) -> bool:
        """
        Monitorear ejecución del phantom hasta que termine
        
        Args:
            container_id: ID del container del phantom
            
        Returns:
            True si el phantom terminó exitosamente
        """
        try:
            import time
            
            logger.info(f"Iniciando monitoreo del container {container_id}")
            
            max_wait_time = 300  # 5 minutos máximo
            check_interval = 15  # Verificar cada 15 segundos
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    # Verificar estado del container
                    headers = {
                        "X-Phantombuster-Key-1": self.api_key,
                        "Content-Type": "application/json"
                    }
                    
                    # Usar endpoint de containers para verificar estado
                    fetch_url = f"https://api.phantombuster.com/api/v2/containers/fetch?id={container_id}"
                    response = requests.get(fetch_url, headers=headers)
                    
                    if response.status_code == 200:
                        container_data = response.json()
                        status = container_data.get('status', 'unknown')
                        
                        logger.info(f"Estado del container: {status} (tiempo transcurrido: {elapsed_time}s)")
                        
                        if status == 'finished':
                            logger.info("[OK] Phantom termino exitosamente")
                            return True
                        elif status == 'error':
                            logger.error("[ERROR] Phantom termino con error")
                            return False
                        elif status in ['running', 'queued', 'starting']:
                            logger.info(f"[WAIT] Phantom {status}, esperando...")
                        else:
                            logger.warning(f"[WARN] Estado desconocido: {status}")
                    
                    else:
                        logger.warning(f"Error verificando estado: HTTP {response.status_code}")
                    
                    # Esperar antes del siguiente check
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                    
                except Exception as e:
                    logger.error(f"Error durante monitoreo: {e}")
                    time.sleep(check_interval)
                    elapsed_time += check_interval
            
            # Timeout alcanzado
            logger.warning(f"[TIMEOUT] Timeout alcanzado ({max_wait_time}s). Phantom puede seguir ejecutandose.")
            return False
            
        except Exception as e:
            logger.error(f"Error monitoreando phantom: {e}")
            return False
    
    def run_connections_monitoring(self) -> Dict:
        """
        Ejecutar monitoreo de conexiones
        
        Returns:
            Resultado del monitoreo
        """
        try:
            logger.info("=== INICIANDO MONITOREO DE CONEXIONES (SUPABASE) ===")
            
            # 1. Lanzar phantom de exportación
            logger.info("1. Lanzando phantom de exportación de conexiones...")
            launch_result = self.launch_connections_export()
            
            if not launch_result:
                return {
                    "status": "error",
                    "message": "Error lanzando phantom de exportación",
                    "connections_processed": 0
                }
            
            container_id = launch_result.get('data', {}).get('containerId')
            if not container_id:
                return {
                    "status": "error",
                    "message": "No se obtuvo Container ID",
                    "connections_processed": 0
                }
            
            # 2. Monitorear ejecución del phantom
            logger.info("2. Monitoreando ejecución del phantom...")
            monitor_success = self.monitor_phantom_execution(container_id)
            
            if not monitor_success:
                return {
                    "status": "error",
                    "message": "Error monitoreando ejecución del phantom",
                    "connections_processed": 0
                }
            
            # 3. Obtener CSV de conexiones
            logger.info("3. Obteniendo CSV de conexiones...")
            connections = self.get_connections_csv_from_s3(container_id)
            
            if not connections:
                return {
                    "status": "error",
                    "message": "No se obtuvieron conexiones del phantom",
                    "connections_processed": 0
                }
            
            # 4. Procesar conexiones
            logger.info("4. Procesando conexiones...")
            processed_connections = self.parse_connections_data(connections)
            
            if not processed_connections:
                return {
                    "status": "error",
                    "message": "Error procesando conexiones",
                    "connections_processed": 0
                }
            
            # 5. Actualizar Supabase
            logger.info("5. Actualizando Supabase...")
            update_success = self.update_supabase_with_new_connections(processed_connections)
            
            if update_success:
                logger.info("=== MONITOREO DE CONEXIONES COMPLETADO EXITOSAMENTE ===")
                return {
                    "status": "success",
                    "message": "Monitoreo completado exitosamente",
                    "connections_processed": len(processed_connections)
                }
            else:
                logger.warning("=== MONITOREO COMPLETADO CON ADVERTENCIAS ===")
                return {
                    "status": "warning",
                    "message": "Monitoreo completado pero con errores en actualizaciones",
                    "connections_processed": len(processed_connections)
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando monitoreo de conexiones: {e}")
            return {
                "status": "error",
                "message": str(e),
                "connections_processed": 0
            }
    
    def run_simple_monitoring(self) -> Dict:
        """
        Ejecutar monitoreo simplificado (solo obtener CSV y actualizar Supabase)
        
        Returns:
            Resultado del monitoreo
        """
        try:
            logger.info("=== INICIANDO MONITOREO SIMPLIFICADO DE CONEXIONES (SUPABASE) ===")
            
            # 1. Obtener CSV de conexiones directamente
            logger.info("1. Obteniendo CSV de conexiones...")
            connections = self.get_connections_csv_from_s3()
            
            if not connections:
                return {
                    "status": "error",
                    "message": "No se obtuvieron conexiones del CSV",
                    "connections_processed": 0
                }
            
            # 2. Procesar conexiones
            logger.info("2. Procesando conexiones...")
            processed_connections = self.parse_connections_data(connections)
            
            if not processed_connections:
                return {
                    "status": "error",
                    "message": "Error procesando conexiones",
                    "connections_processed": 0
                }
            
            # 3. Actualizar Supabase
            logger.info("3. Actualizando Supabase...")
            update_success = self.update_supabase_with_new_connections(processed_connections)
            
            if update_success:
                logger.info("=== MONITOREO SIMPLIFICADO COMPLETADO EXITOSAMENTE ===")
                return {
                    "status": "success",
                    "message": "Monitoreo simplificado completado exitosamente",
                    "connections_processed": len(processed_connections)
                }
            else:
                logger.warning("=== MONITOREO COMPLETADO CON ADVERTENCIAS ===")
                return {
                    "status": "warning",
                    "message": "Monitoreo completado pero con errores en actualizaciones",
                    "connections_processed": len(processed_connections)
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando monitoreo simplificado: {e}")
            return {
                "status": "error",
                "message": str(e),
                "connections_processed": 0
            }

if __name__ == "__main__":
    print("🔗 GAVIN CONNECTIONS MONITOR - SUPABASE VERSION")
    print("=" * 50)
    
    monitor = GavinConnectionsMonitorSupabase()
    
    # Usar run_simple_monitoring() para obtener CSV directamente
    result = monitor.run_simple_monitoring()
    
    print(f"\n📊 RESULTADO: {result['status'].upper()}")
    print(f"📋 Mensaje: {result['message']}")
    print(f"📈 Conexiones procesadas: {result.get('connections_processed', 0)}")
    
    if result['status'] == 'success':
        print("\n✅ MONITOREO COMPLETADO EXITOSAMENTE!")
        print("🔄 Supabase actualizado con nuevas conexiones detectadas")
    elif result['status'] == 'warning':
        print("\n⚠️ MONITOREO COMPLETADO CON ADVERTENCIAS!")
        print("🔧 Revisar logs para más detalles")
    else:
        print(f"\n❌ ERROR: {result['message']}")
        print("🔧 Revisar logs para más detalles")




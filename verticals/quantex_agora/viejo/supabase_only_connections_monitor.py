#!/usr/bin/env python3
"""
Supabase Only Connections Monitor - Versión que usa solo Supabase (sin Airtable)
Agrega conexiones orgánicas a la tabla active_contacts
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('supabase_only_connections_monitor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SupabaseOnlyConnectionsMonitor(PhantomBaseManager):
    """
    Monitor que usa solo Supabase:
    1. Detecta conexiones aceptadas (actualiza linkedin_leads)
    2. Agrega conexiones orgánicas a active_contacts
    """
    
    def __init__(self):
        super().__init__(
            phantom_id=os.getenv("PHANTOMBUSTER_CONECTIONS_EXPORT_PHANTOM_ID"),
            phantom_name="Gavin LinkedIn Connections Export"
        )
        
        # Inicializar Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Usar SERVICE_KEY en lugar de ANON_KEY
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase Only Connections Monitor inicializado correctamente")
    
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
            
            # Procesar CSV con codificación correcta
            csv_content = csv_response.content.decode('utf-8')
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
        """Procesar datos de conexiones del CSV"""
        try:
            processed_connections = []
            
            for connection in connections:
                # Extraer datos del CSV
                profile_url = connection.get('profileUrl', '')
                full_name = connection.get('fullName', '')
                first_name = connection.get('firstName', '')
                last_name = connection.get('lastName', '')
                title = connection.get('title', '')
                connection_since = connection.get('connectionSince', '')
                
                # Normalizar URL
                linkedin_url = self._normalize_linkedin_url(profile_url)
                
                processed_connection = {
                    'linkedin_url': linkedin_url,
                    'full_name': full_name,
                    'first_name': first_name,
                    'last_name': last_name,
                    'title': title,
                    'connection_date': connection_since,
                    'raw_data': connection
                }
                
                processed_connections.append(processed_connection)
            
            logger.info(f"Conexiones procesadas: {len(processed_connections)} registros")
            return processed_connections
            
        except Exception as e:
            logger.error(f"Error procesando conexiones: {e}")
            return []
    
    def update_supabase_with_new_connections(self, connections: List[Dict]) -> bool:
        """
        Actualizar Supabase con nuevas conexiones detectadas (lógica original)
        """
        try:
            logger.info(f"Actualizando Supabase con {len(connections)} conexiones")
            
            # Obtener todos los leads de LinkedIn
            response = self.supabase.table('linkedin_leads').select('*').execute()
            leads = response.data
            logger.info(f"Encontrados {len(leads)} leads en Supabase")
            
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
                        normalized_lead_url = self._normalize_linkedin_url(lead_url)
                        normalized_connection_url = self._normalize_linkedin_url(linkedin_url)
                        
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
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando Supabase: {e}")
            return False
    
    def process_organic_connections(self, connections: List[Dict]) -> List[Dict]:
        """
        Procesar conexiones orgánicas (que no están en linkedin_leads)
        """
        try:
            logger.info("=== PROCESANDO CONEXIONES ORGÁNICAS ===")
            
            # Obtener todos los leads de Supabase
            response = self.supabase.table('linkedin_leads').select('*').execute()
            leads = response.data
            logger.info(f"Encontrados {len(leads)} leads en linkedin_leads")
            
            # Crear set de URLs de leads existentes
            existing_lead_urls = set()
            for lead in leads:
                lead_url = lead.get('linkedin_profile_url', '')
                if lead_url:
                    normalized_url = self._normalize_linkedin_url(lead_url)
                    existing_lead_urls.add(normalized_url)
            
            # Identificar conexiones orgánicas
            organic_connections = []
            for connection in connections:
                connection_url = connection.get('linkedin_url', '')
                if connection_url:
                    normalized_connection_url = self._normalize_linkedin_url(connection_url)
                    
                    # Si no está en leads existentes, es orgánica
                    if normalized_connection_url not in existing_lead_urls:
                        organic_connections.append(connection)
                        logger.info(f"🔍 Conexión orgánica detectada: {connection.get('full_name', 'N/A')}")
            
            logger.info(f"📊 Total conexiones orgánicas: {len(organic_connections)}")
            return organic_connections
            
        except Exception as e:
            logger.error(f"Error procesando conexiones orgánicas: {e}")
            return []
    
    def add_organic_connections_to_active_contacts(self, organic_connections: List[Dict]) -> int:
        """
        Agregar conexiones orgánicas a active_contacts
        
        Args:
            organic_connections: Lista de conexiones orgánicas
            
        Returns:
            Número de conexiones agregadas
        """
        try:
            logger.info(f"=== AGREGANDO {len(organic_connections)} CONEXIONES ORGÁNICAS A ACTIVE_CONTACTS ===")
            
            # Obtener contactos existentes en active_contacts
            response = self.supabase.table('active_contacts').select('*').execute()
            existing_contacts = response.data
            logger.info(f"Encontrados {len(existing_contacts)} contactos en active_contacts")
            
            # Crear set de URLs existentes
            existing_urls = set()
            for contact in existing_contacts:
                url = contact.get('linkedin_url', '')
                if url:
                    existing_urls.add(self._normalize_linkedin_url(url))
            
            # Preparar registros para insertar
            records_to_insert = []
            for connection in organic_connections:
                connection_url = connection.get('linkedin_url', '')
                normalized_url = self._normalize_linkedin_url(connection_url)
                
                # Solo agregar si no existe en active_contacts
                if normalized_url not in existing_urls:
                    record = {
                        'full_name': connection.get('full_name', ''),
                        'email': None,  # No disponible en conexiones
                        'company_name': '',  # No disponible en conexiones
                        'region': None,  # No disponible en conexiones
                        'source': 'prospecto',  # Conexiones orgánicas son prospectos
                        'notes': f"Conexión orgánica - {connection.get('title', '')}",
                        'tags': ['linkedin_organic', 'connection'],
                        'can_receive_communications': True,
                        'last_communication_sent_at': None,
                        'linkedin_url': connection_url,
                        'phone': None,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    records_to_insert.append(record)
                    logger.info(f"📝 Preparando para agregar: {connection.get('full_name', 'N/A')}")
            
            # Insertar en active_contacts
            if records_to_insert:
                logger.info(f"📤 Insertando {len(records_to_insert)} conexiones orgánicas en active_contacts...")
                response = self.supabase.table('active_contacts').insert(records_to_insert).execute()
                
                if response.data:
                    logger.info(f"✅ {len(response.data)} conexiones orgánicas agregadas a active_contacts")
                    return len(response.data)
                else:
                    logger.error(f"❌ Error insertando conexiones orgánicas: {response.error}")
                    return 0
            else:
                logger.info("ℹ️  No hay conexiones orgánicas nuevas para agregar")
                return 0
                
        except Exception as e:
            logger.error(f"Error agregando conexiones orgánicas a active_contacts: {e}")
            return 0
    
    def _normalize_linkedin_url(self, url: str) -> str:
        """Normalizar URL de LinkedIn para comparación"""
        if not url:
            return ''
        # Remover www. y trailing slash
        url = url.replace('https://www.', 'https://').replace('https://', '').rstrip('/')
        return url
    
    def run_supabase_only_monitoring(self) -> Dict:
        """
        Ejecutar monitoreo que usa solo Supabase
        
        Returns:
            Resultado del monitoreo
        """
        try:
            logger.info("=== INICIANDO MONITOREO SOLO SUPABASE ===")
            
            # 1. Obtener CSV de conexiones
            logger.info("1. Obteniendo CSV de conexiones...")
            connections = self.get_connections_csv_from_s3()
            
            if not connections:
                return {
                    "status": "error",
                    "message": "No se obtuvieron conexiones del CSV",
                    "connections_processed": 0,
                    "organic_connections_added": 0
                }
            
            # 2. Procesar conexiones
            logger.info("2. Procesando conexiones...")
            processed_connections = self.parse_connections_data(connections)
            
            if not processed_connections:
                return {
                    "status": "error",
                    "message": "Error procesando conexiones",
                    "connections_processed": 0,
                    "organic_connections_added": 0
                }
            
            # 3. Actualizar conexiones existentes (lógica original)
            logger.info("3. Actualizando conexiones existentes en linkedin_leads...")
            update_success = self.update_supabase_with_new_connections(processed_connections)
            
            # 4. Procesar conexiones orgánicas
            logger.info("4. Procesando conexiones orgánicas...")
            organic_connections = self.process_organic_connections(processed_connections)
            
            organic_added = 0
            if organic_connections:
                # 5. Agregar conexiones orgánicas a active_contacts
                logger.info("5. Agregando conexiones orgánicas a active_contacts...")
                organic_added = self.add_organic_connections_to_active_contacts(organic_connections)
            
            # Resultado final
            result = {
                "status": "success",
                "message": "Monitoreo solo Supabase completado exitosamente",
                "connections_processed": len(processed_connections),
                "organic_connections_detected": len(organic_connections),
                "organic_connections_added": organic_added
            }
            
            logger.info("=== MONITOREO SOLO SUPABASE COMPLETADO EXITOSAMENTE ===")
            return result
            
        except Exception as e:
            logger.error(f"Error en monitoreo solo Supabase: {e}")
            return {
                "status": "error",
                "message": f"Error en monitoreo solo Supabase: {e}",
                "connections_processed": 0,
                "organic_connections_added": 0
            }

if __name__ == "__main__":
    print("🔗 SUPABASE ONLY CONNECTIONS MONITOR")
    print("=" * 50)
    
    monitor = SupabaseOnlyConnectionsMonitor()
    result = monitor.run_supabase_only_monitoring()
    
    print(f"\n📊 RESULTADO: {result['status'].upper()}")
    print(f"📋 Mensaje: {result['message']}")
    print(f"📈 Conexiones procesadas: {result.get('connections_processed', 0)}")
    print(f"🔍 Conexiones orgánicas detectadas: {result.get('organic_connections_detected', 0)}")
    print(f"📤 Conexiones orgánicas agregadas a active_contacts: {result.get('organic_connections_added', 0)}")
    
    if result['status'] == 'success':
        print("\n✅ MONITOREO SOLO SUPABASE COMPLETADO EXITOSAMENTE!")
        print("🔄 Todas las conexiones (incluyendo orgánicas) ahora están en contactos activos")
    else:
        print(f"\n❌ ERROR: {result['message']}")
        print("🔧 Revisar logs para más detalles")

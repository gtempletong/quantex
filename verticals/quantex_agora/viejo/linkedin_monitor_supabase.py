#!/usr/bin/env python3
"""
LinkedIn Monitor - Supabase Version
Actualiza estados en Supabase en vez de Airtable
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Importar clase base
from verticals.quantex_agora.linkedin_monitor import LinkedInMonitor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_monitor_supabase.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class LinkedInMonitorSupabase(LinkedInMonitor):
    """Monitor de LinkedIn que actualiza Supabase en vez de Airtable"""
    
    def __init__(self):
        """Inicializar monitor con conexión a Supabase"""
        super().__init__()
        
        # Inicializar cliente Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_KEY son requeridas")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("LinkedIn Monitor Supabase inicializado correctamente")
    
    def update_supabase_with_results(self, processed_results: list) -> bool:
        """
        Actualizar Supabase con los resultados procesados
        
        Args:
            processed_results: Resultados procesados del CSV de PhantomBuster
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando Supabase con {len(processed_results)} resultados")
            
            updated_count = 0
            matched_count = 0
            
            for result in processed_results:
                try:
                    # Buscar match por LinkedIn URL
                    linkedin_url = result.get('linkedin_url', '')
                    if not linkedin_url:
                        logger.warning(f"Resultado sin LinkedIn URL: {result}")
                        continue
                    
                    # Normalizar URL
                    norm_result_url = self._normalize_linkedin_url(linkedin_url)
                    
                    # Buscar en Supabase por LinkedIn URL
                    response = self.supabase.table('linkedin_leads').select('*').eq('linkedin_profile_url', linkedin_url).execute()
                    
                    if not response.data:
                        # Intentar con URL normalizada
                        response = self.supabase.table('linkedin_leads').select('*').ilike('linkedin_profile_url', f'%{norm_result_url}%').execute()
                    
                    if response.data and len(response.data) > 0:
                        matched_count += 1
                        lead = response.data[0]
                        lead_id = lead['id']
                        lead_name = lead.get('full_name', 'N/A')
                        
                        # Determinar estado basado en error
                        err = (result.get('error', '') or '').strip()
                        sent = False
                        
                        if not err:
                            sent = True
                        else:
                            # Algunos mensajes implican ya estar conectado
                            low = err.lower()
                            if any(k in low for k in ['accepted', 'connected', 'already in network']):
                                sent = True
                        
                        # Preparar actualización
                        update_data = {
                            'phantom_status': 'Solicitud Enviada' if sent else 'En Cola',
                            'last_activity_at': datetime.now().isoformat()
                        }
                        
                        # Si fue enviado, registrar timestamp
                        if sent:
                            update_data['dm_sent_at'] = datetime.now().isoformat()
                        
                        # Actualizar en Supabase
                        update_response = self.supabase.table('linkedin_leads').update(update_data).eq('id', lead_id).execute()
                        
                        if update_response.data:
                            updated_count += 1
                            logger.info(
                                f"✅ Actualizado {lead_name}: "
                                f"phantom_status = {'Solicitud Enviada' if sent else 'En Cola'} "
                                f"(error: {result.get('error', 'N/A')})"
                            )
                        else:
                            logger.error(f"❌ Error actualizando {lead_name}")
                    else:
                        # No hay match
                        logger.info(f"ℹ️  No se encontró match para {linkedin_url}")
                
                except Exception as e:
                    logger.error(f"❌ Error procesando resultado: {e}")
                    continue
            
            logger.info(f"📊 RESUMEN: {matched_count} matches encontrados, {updated_count} actualizados en Supabase")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error actualizando Supabase con resultados: {e}")
            return False
    
    def run_monitoring_cycle(self) -> dict:
        """
        Ejecutar ciclo de monitoreo con Supabase
        
        Returns:
            Resultado del monitoreo
        """
        try:
            logger.info("=== INICIANDO CICLO DE MONITOREO (SUPABASE) ===")
            
            # 1. Buscar último Container ID
            logger.info("1. Buscando último Container ID...")
            container_id = self.get_latest_container_id()
            
            if not container_id:
                return {
                    "status": "error",
                    "message": "No se pudo obtener Container ID",
                    "results_processed": 0
                }
            
            # 2. Verificar status del phantom
            logger.info("2. Verificando status del phantom...")
            status = self.check_container_status(container_id)
            logger.info(f"Status del phantom: {status}")
            
            # 3. Obtener resultados del phantom desde S3
            logger.info("3. Obteniendo resultados del phantom desde S3...")
            csv_results = self.get_phantom_results_from_s3(container_id)
            
            if not csv_results:
                return {
                    "status": "info",
                    "message": "No hay resultados disponibles del phantom",
                    "results_processed": 0,
                    "container_id": container_id,
                    "phantom_status": status
                }
            
            # 4. Procesar resultados
            logger.info("4. Procesando resultados del CSV...")
            processed_results = self.parse_csv_results_real(csv_results)
            
            if not processed_results:
                return {
                    "status": "error",
                    "message": "Error procesando resultados del CSV",
                    "results_processed": 0,
                    "container_id": container_id,
                    "phantom_status": status
                }
            
            # 5. Actualizar Supabase (en vez de Airtable)
            logger.info("5. Actualizando Supabase...")
            update_success = self.update_supabase_with_results(processed_results)
            
            if update_success:
                logger.info("=== ✅ CICLO DE MONITOREO COMPLETADO EXITOSAMENTE ===")
                return {
                    "status": "success",
                    "message": "Ciclo de monitoreo completado exitosamente",
                    "results_processed": len(processed_results),
                    "container_id": container_id,
                    "phantom_status": status
                }
            else:
                logger.warning("=== ⚠️  CICLO DE MONITOREO COMPLETADO CON ADVERTENCIAS ===")
                return {
                    "status": "warning",
                    "message": "Ciclo completado pero con errores en actualizaciones",
                    "results_processed": len(processed_results),
                    "container_id": container_id,
                    "phantom_status": status
                }
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo de monitoreo: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results_processed": 0
            }


if __name__ == "__main__":
    print("📊 LINKEDIN MONITOR - SUPABASE VERSION")
    print("=" * 50)
    
    try:
        monitor = LinkedInMonitorSupabase()
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
            print("🔄 Supabase actualizado con resultados del phantom")
        elif result['status'] == 'warning':
            print("\n⚠️  MONITOREO COMPLETADO CON ADVERTENCIAS!")
            print("🔧 Revisar logs para más detalles")
        else:
            print(f"\n❌ ERROR: {result['message']}")
            print("🔧 Revisar logs para más detalles")
    
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        print("🔧 Revisar configuración de Supabase y variables de entorno")





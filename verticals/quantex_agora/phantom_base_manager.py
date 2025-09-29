"""
Phantom Base Manager - Clase base común para todos los managers de phantoms
Contiene funcionalidades comunes para todos los phantoms de Phantombuster
"""

import requests
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phantom_base_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PhantomBaseManager:
    """Clase base para todos los managers de phantoms de Phantombuster"""
    
    def __init__(self, phantom_id: str, phantom_name: str):
        """
        Inicializar el manager base
        
        Args:
            phantom_id: ID del phantom en Phantombuster
            phantom_name: Nombre descriptivo del phantom
        """
        self.api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.phantom_id = phantom_id
        self.phantom_name = phantom_name
        self.base_url = "https://phantombuster.com/api/v1"
        self.results_url = "https://api.phantombuster.com/api/v2/containers/fetch-result-object"
        
        if not self.api_key:
            raise ValueError("PHANTOMBUSTER_API_KEY no encontrada en variables de entorno")
        
        logger.info(f"{self.phantom_name} Manager inicializado - Phantom ID: {self.phantom_id}")
    
    def get_phantom_config(self) -> Optional[Dict]:
        """
        Obtener configuración del phantom
        
        Returns:
            Diccionario con la configuración del phantom o None si hay error
        """
        try:
            url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}"
            headers = {"X-Phantombuster-Key-1": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            phantom_data = result.get('data', {})
            
            logger.info(f"Configuración obtenida para {self.phantom_name}")
            return phantom_data
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración de {self.phantom_name}: {e}")
            return None
    
    def check_phantom_status(self) -> Dict:
        """
        Verificar estado del phantom
        
        Returns:
            Diccionario con el estado del phantom
        """
        try:
            config = self.get_phantom_config()
            if not config:
                return {"status": "error", "message": "No se pudo obtener configuración"}
            
            status_info = {
                "phantom_id": self.phantom_id,
                "phantom_name": self.phantom_name,
                "name": config.get('name', 'N/A'),
                "auto_launch": config.get('autoLaunch', 'N/A'),
                "arguments_count": len(config.get('arguments', {})),
                "has_configuration": bool(config.get('arguments')),
                "status": "success"
            }
            
            logger.info(f"Estado de {self.phantom_name}: {status_info}")
            return status_info
            
        except Exception as e:
            logger.error(f"Error verificando estado de {self.phantom_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    def launch_phantom(self, payload: Dict) -> Optional[Dict]:
        """
        Lanzar el phantom con los parámetros especificados
        
        Args:
            payload: Parámetros para el phantom
            
        Returns:
            Respuesta de la API o None si hay error
        """
        try:
            # Usar endpoint correcto de Phantombuster
            url = f"https://api.phantombuster.com/api/v2/phantoms/{self.phantom_id}/launch"
            headers = {
                "X-Phantombuster-Key-1": self.api_key,  # Header correcto según documentación oficial
                "Content-Type": "application/json"
            }
            
            logger.info(f"Lanzando {self.phantom_name} con payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, headers=headers, json=payload)
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"{self.phantom_name} lanzado exitosamente: {result}")
                return result
            else:
                logger.error(f"Error lanzando {self.phantom_name}: {response.status_code}")
                logger.error(f"Respuesta: {response.text}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error lanzando {self.phantom_name}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Respuesta del servidor: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado lanzando {self.phantom_name}: {e}")
            return None
    
    def monitor_phantom_execution(self, container_id: str, max_wait_minutes: int = 60) -> Optional[Dict]:
        """
        Monitorear la ejecución del phantom
        
        Args:
            container_id: ID del container a monitorear
            max_wait_minutes: Tiempo máximo de espera en minutos
            
        Returns:
            Resultados del phantom o None si hay error
        """
        try:
            logger.info(f"Monitoreando ejecución de {self.phantom_name} - Container: {container_id}")
            
            start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            
            while time.time() - start_time < max_wait_seconds:
                # Obtener output del phantom
                output_result = self.get_phantom_output()
                
                if output_result and 'data' in output_result:
                    data = output_result['data']
                    container_status = data.get('containerStatus', 'unknown')
                    agent_status = data.get('agentStatus', 'unknown')
                    
                    logger.info(f"Estado del container: {container_status}, Agente: {agent_status}")
                    
                    # Si el phantom terminó, obtener resultados
                    if container_status == 'not running' and agent_status == 'not running':
                        logger.info(f"{self.phantom_name} completado exitosamente")
                        return output_result
                    
                    # Si hay error
                    if container_status == 'error' or agent_status == 'error':
                        logger.error(f"{self.phantom_name} terminó con error")
                        return output_result
                
                # Esperar antes del siguiente check
                time.sleep(30)
            
            logger.warning(f"Timeout monitoreando {self.phantom_name} después de {max_wait_minutes} minutos")
            return None
            
        except Exception as e:
            logger.error(f"Error monitoreando {self.phantom_name}: {e}")
            return None
    
    def get_phantom_output(self) -> Optional[Dict]:
        """
        Obtener output del phantom
        
        Returns:
            Output del phantom o None si hay error
        """
        try:
            url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/output"
            headers = {"X-Phantombuster-Key-1": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo output de {self.phantom_name}: {e}")
            return None
    
    def get_phantom_results(self, container_id: str = None) -> Optional[Dict]:
        """
        Obtener resultados del phantom
        
        Args:
            container_id: ID del container (opcional)
            
        Returns:
            Resultados del phantom o None si hay error
        """
        try:
            output_result = self.get_phantom_output()
            
            if not output_result or 'data' not in output_result:
                logger.warning(f"No hay output disponible para {self.phantom_name}")
                return None
            
            data = output_result['data']
            
            # Extraer resultObject si existe
            if 'resultObject' in data and data['resultObject']:
                try:
                    # Parsear resultObject si es string
                    if isinstance(data['resultObject'], str):
                        parsed_results = json.loads(data['resultObject'])
                    else:
                        parsed_results = data['resultObject']
                    
                    logger.info(f"Resultados obtenidos para {self.phantom_name}: {len(parsed_results) if isinstance(parsed_results, list) else '1'} registro(s)")
                    return parsed_results
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando resultObject de {self.phantom_name}: {e}")
                    return None
            
            logger.warning(f"No hay resultObject disponible para {self.phantom_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo resultados de {self.phantom_name}: {e}")
            return None
    
    def get_phantom_containers(self) -> Optional[List[Dict]]:
        """
        Obtener lista de containers del phantom
        
        Returns:
            Lista de containers o None si hay error
        """
        try:
            url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/containers"
            headers = {"X-Phantombuster-Key-1": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            containers = result.get('data', [])
            
            logger.info(f"Encontrados {len(containers)} containers para {self.phantom_name}")
            return containers
            
        except Exception as e:
            logger.error(f"Error obteniendo containers de {self.phantom_name}: {e}")
            return None
    
    def format_timestamp(self, timestamp: int) -> str:
        """
        Formatear timestamp a string legible
        
        Args:
            timestamp: Timestamp en milisegundos
            
        Returns:
            String con fecha y hora formateada
        """
        try:
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)
    
    def log_phantom_info(self):
        """Log información básica del phantom"""
        logger.info(f"=== INFORMACIÓN DE {self.phantom_name.upper()} ===")
        logger.info(f"Phantom ID: {self.phantom_id}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key configurada: {'SI' if self.api_key else 'NO'}")


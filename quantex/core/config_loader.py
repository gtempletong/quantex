#!/usr/bin/env python3
"""
Config Loader para Source Monitor
Carga configuración desde archivos YAML en lugar de Supabase
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceConfigLoader:
    """Cargador de configuración de fuentes desde YAML"""
    
    def __init__(self, config_path: str = None):
        """
        Inicializa el cargador de configuración
        
        Args:
            config_path: Ruta al archivo YAML de configuración
        """
        if config_path is None:
            # Ruta por defecto
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, 'config', 'source_targets.yaml')
        
        self.config_path = config_path
        self.config = None
        self._load_config()
    
    def _load_config(self):
        """Carga la configuración desde el archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            logger.info(f"✅ Configuración cargada desde: {self.config_path}")
        except FileNotFoundError:
            logger.error(f"❌ Archivo de configuración no encontrado: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"❌ Error al parsear YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado al cargar configuración: {e}")
            raise
    
    def get_rss_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene las fuentes RSS configuradas
        
        Args:
            active_only: Si True, solo retorna fuentes activas
            
        Returns:
            Lista de diccionarios con la configuración de fuentes RSS
        """
        if not self.config or 'rss_sources' not in self.config:
            return []
        
        sources = self.config['rss_sources']
        
        if active_only:
            sources = [source for source in sources if source.get('is_active', False)]
        
        # filter_keywords ya está en formato lista en el YAML limpio
        
        return sources
    
    def get_web_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene las fuentes web configuradas
        
        Args:
            active_only: Si True, solo retorna fuentes activas
            
        Returns:
            Lista de diccionarios con la configuración de fuentes web
        """
        if not self.config or 'web_sources' not in self.config:
            return []
        
        sources = self.config['web_sources']
        
        if active_only:
            sources = [source for source in sources if source.get('is_active', False)]
        
        return sources
    
    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una fuente específica por su ID
        
        Args:
            source_id: ID de la fuente
            
        Returns:
            Diccionario con la configuración de la fuente o None si no se encuentra
        """
        # Buscar en fuentes RSS
        rss_sources = self.get_rss_sources(active_only=False)
        for source in rss_sources:
            if source.get('id') == source_id:
                return source
        
        # Buscar en fuentes web
        web_sources = self.get_web_sources(active_only=False)
        for source in web_sources:
            if source.get('id') == source_id:
                return source
        
        return None
    
    def get_sources_by_category(self, category: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene fuentes filtradas por categoría
        
        Args:
            category: Categoría a filtrar
            active_only: Si True, solo retorna fuentes activas
            
        Returns:
            Lista de fuentes de la categoría especificada
        """
        all_sources = self.get_rss_sources(active_only=False) + self.get_web_sources(active_only=False)
        
        filtered_sources = [source for source in all_sources if source.get('category') == category]
        
        if active_only:
            filtered_sources = [source for source in filtered_sources if source.get('is_active', False)]
        
        return filtered_sources
    
    def get_global_settings(self) -> Dict[str, Any]:
        """
        Obtiene la configuración global
        
        Returns:
            Diccionario con la configuración global
        """
        return self.config.get('global_settings', {}) if self.config else {}
    
    def get_processing_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de procesamiento
        
        Returns:
            Diccionario con la configuración de procesamiento
        """
        return self.config.get('processing', {}) if self.config else {}
    
    def get_categories(self) -> Dict[str, Any]:
        """
        Obtiene las categorías definidas
        
        Returns:
            Diccionario con las categorías
        """
        return self.config.get('categories', {}) if self.config else {}
    
    # FUNCIÓN ELIMINADA: update_source_last_checked
    # Los timestamps se eliminaron del YAML para simplificar el sistema
    
    def _save_config(self):
        """Guarda la configuración actualizada al archivo YAML"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True, indent=2)
            logger.info(f"✅ Configuración guardada en: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ Error al guardar configuración: {e}")
            raise
    
    def reload_config(self):
        """Recarga la configuración desde el archivo"""
        self._load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de la configuración
        
        Returns:
            Diccionario con estadísticas de la configuración
        """
        if not self.config:
            return {}
        
        rss_sources = self.get_rss_sources(active_only=False)
        web_sources = self.get_web_sources(active_only=False)
        
        active_rss = len([s for s in rss_sources if s.get('is_active', False)])
        active_web = len([s for s in web_sources if s.get('is_active', False)])
        
        categories = self.get_categories()
        
        return {
            'total_rss_sources': len(rss_sources),
            'active_rss_sources': active_rss,
            'total_web_sources': len(web_sources),
            'active_web_sources': active_web,
            'total_categories': len(categories),
            'config_version': self.config.get('version', 'unknown'),
            'last_updated': self.config.get('last_updated', 'unknown')
        }

# Función de conveniencia para obtener el cargador global
_global_loader = None

def get_config_loader() -> SourceConfigLoader:
    """Obtiene la instancia global del cargador de configuración"""
    global _global_loader
    if _global_loader is None:
        _global_loader = SourceConfigLoader()
    return _global_loader

# Función de conveniencia para obtener fuentes RSS activas
def get_active_rss_sources() -> List[Dict[str, Any]]:
    """Obtiene todas las fuentes RSS activas"""
    return get_config_loader().get_rss_sources(active_only=True)

# Función de conveniencia para obtener fuentes web activas
def get_active_web_sources() -> List[Dict[str, Any]]:
    """Obtiene todas las fuentes web activas"""
    return get_config_loader().get_web_sources(active_only=True)

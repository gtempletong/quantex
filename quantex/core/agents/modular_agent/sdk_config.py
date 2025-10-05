"""
Configuración de SDKs para el agente modular.
Centraliza la configuración de APIs externas.
"""

import os
from typing import Optional


class SDKConfig:
    """Configuración centralizada para SDKs externos."""
    
    @staticmethod
    def get_brevo_config() -> dict:
        """Configuración para Brevo SDK."""
        api_key = os.getenv('BREVO_API_KEY')
        if not api_key:
            raise ValueError("BREVO_API_KEY no configurada en variables de entorno")
        
        return {
            'api_key': api_key,
            'sender_email': 'gavintempleton@gavintempleton.net',
            'sender_name': 'Gavin Templeton',
            'reply_to_email': 'gavintempleton@gavintempleton.net',
            'reply_to_name': 'Gavin Templeton'
        }
    
    @staticmethod
    def get_airtable_config() -> dict:
        """Configuración para Airtable SDK."""
        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        if not api_key:
            raise ValueError("AIRTABLE_API_KEY no configurada en variables de entorno")
        if not base_id:
            raise ValueError("AIRTABLE_BASE_ID no configurada en variables de entorno")
        
        return {
            'api_key': api_key,
            'base_id': base_id
        }
    
    @staticmethod
    def get_supabase_config() -> dict:
        """Configuración para Supabase SDK."""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url:
            raise ValueError("SUPABASE_URL no configurada en variables de entorno")
        if not key:
            raise ValueError("SUPABASE_SERVICE_KEY no configurada en variables de entorno")
        
        return {
            'url': url,
            'key': key
        }

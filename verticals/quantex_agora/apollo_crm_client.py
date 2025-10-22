#!/usr/bin/env python3
"""
Apollo.io CRM Client
Cliente para extraer contactos del CRM de Apollo.io (disponible en free trial)
"""

import os
import sys
import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from verticals.quantex_agora.apollo_client import ApolloClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApolloCRMClient(ApolloClient):
    """Cliente para trabajar con el CRM de Apollo.io (endpoints gratuitos)"""
    
    def search_contacts(
        self,
        q: Optional[str] = None,
        contact_stage_ids: Optional[List[str]] = None,
        sort_by_field: str = "contact_last_activity_date",
        sort_ascending: bool = False,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """
        Buscar contactos en tu CRM de Apollo.io
        
        Este endpoint SÍ está disponible en el free trial.
        
        Args:
            q: Búsqueda por texto
            contact_stage_ids: IDs de etapas de contacto
            sort_by_field: Campo por el cual ordenar
            sort_ascending: Orden ascendente o descendente
            page: Número de página
            per_page: Resultados por página
            
        Returns:
            Diccionario con contactos del CRM
        """
        data = {
            "page": page,
            "per_page": min(per_page, 100),
            "sort_by_field": sort_by_field,
            "sort_ascending": sort_ascending
        }
        
        if q:
            data["q"] = q
        if contact_stage_ids:
            data["contact_stage_ids"] = contact_stage_ids
        
        logger.info(f"Buscando contactos en CRM de Apollo.io: {data}")
        
        result = self._make_request("POST", "contacts/search", data=data)
        
        total = result.get('pagination', {}).get('total_entries', 0)
        logger.info(f"Contactos encontrados en CRM: {total}")
        
        return result
    
    def search_accounts(
        self,
        q: Optional[str] = None,
        sort_by_field: str = "account_last_activity_date",
        sort_ascending: bool = False,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """
        Buscar cuentas (empresas) en tu CRM de Apollo.io
        
        Este endpoint SÍ está disponible en el free trial.
        
        Args:
            q: Búsqueda por texto
            sort_by_field: Campo por el cual ordenar
            sort_ascending: Orden ascendente o descendente
            page: Número de página
            per_page: Resultados por página
            
        Returns:
            Diccionario con cuentas del CRM
        """
        data = {
            "page": page,
            "per_page": min(per_page, 100),
            "sort_by_field": sort_by_field,
            "sort_ascending": sort_ascending
        }
        
        if q:
            data["q"] = q
        
        logger.info(f"Buscando cuentas en CRM de Apollo.io: {data}")
        
        result = self._make_request("POST", "accounts/search", data=data)
        
        total = result.get('pagination', {}).get('total_entries', 0)
        logger.info(f"Cuentas encontradas en CRM: {total}")
        
        return result
    
    def get_all_contacts(self) -> List[Dict]:
        """
        Obtener TODOS los contactos del CRM de Apollo.io (con paginación)
        
        Returns:
            Lista completa de contactos
        """
        all_contacts = []
        page = 1
        per_page = 100
        
        logger.info("Obteniendo todos los contactos del CRM...")
        
        while True:
            result = self.search_contacts(page=page, per_page=per_page)
            
            contacts = result.get('contacts', [])
            all_contacts.extend(contacts)
            
            pagination = result.get('pagination', {})
            total_pages = pagination.get('total_pages', 0)
            
            logger.info(f"Página {page}/{total_pages}: {len(contacts)} contactos")
            
            if page >= total_pages:
                break
            
            page += 1
        
        logger.info(f"Total de contactos obtenidos: {len(all_contacts)}")
        
        return all_contacts
    
    def get_all_accounts(self) -> List[Dict]:
        """
        Obtener TODAS las cuentas del CRM de Apollo.io (con paginación)
        
        Returns:
            Lista completa de cuentas
        """
        all_accounts = []
        page = 1
        per_page = 100
        
        logger.info("Obteniendo todas las cuentas del CRM...")
        
        while True:
            result = self.search_accounts(page=page, per_page=per_page)
            
            accounts = result.get('accounts', [])
            all_accounts.extend(accounts)
            
            pagination = result.get('pagination', {})
            total_pages = pagination.get('total_pages', 0)
            
            logger.info(f"Página {page}/{total_pages}: {len(accounts)} cuentas")
            
            if page >= total_pages:
                break
            
            page += 1
        
        logger.info(f"Total de cuentas obtenidas: {len(all_accounts)}")
        
        return all_accounts


def test_crm_access():
    """Probar acceso al CRM de Apollo.io"""
    print("=" * 60)
    print("🔍 PROBANDO ACCESO AL CRM DE APOLLO.IO")
    print("=" * 60)
    
    try:
        client = ApolloCRMClient()
        print("✅ Cliente CRM inicializado correctamente")
        
        # Buscar contactos en el CRM
        print("\n📊 Buscando contactos en tu CRM...")
        result = client.search_contacts(per_page=5)
        
        total = result.get('pagination', {}).get('total_entries', 0)
        contacts = result.get('contacts', [])
        
        print(f"✅ Búsqueda exitosa!")
        print(f"Total de contactos en CRM: {total}")
        print(f"Mostrando primeros {len(contacts)} contactos:")
        
        for i, contact in enumerate(contacts, 1):
            print(f"\n{i}. {contact.get('name', 'N/A')}")
            print(f"   Email: {contact.get('email', 'N/A')}")
            print(f"   Título: {contact.get('title', 'N/A')}")
            print(f"   Empresa: {contact.get('account_name', 'N/A')}")
            print(f"   LinkedIn: {contact.get('linkedin_url', 'N/A')}")
        
        # Buscar cuentas en el CRM
        print(f"\n{'=' * 60}")
        print("🏢 Buscando cuentas en tu CRM...")
        result = client.search_accounts(per_page=5)
        
        total = result.get('pagination', {}).get('total_entries', 0)
        accounts = result.get('accounts', [])
        
        print(f"✅ Búsqueda exitosa!")
        print(f"Total de cuentas en CRM: {total}")
        print(f"Mostrando primeras {len(accounts)} cuentas:")
        
        for i, account in enumerate(accounts, 1):
            print(f"\n{i}. {account.get('name', 'N/A')}")
            print(f"   Dominio: {account.get('domain', 'N/A')}")
            print(f"   Industria: {account.get('industry', 'N/A')}")
            print(f"   Empleados: {account.get('employee_count', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("✅ ACCESO AL CRM FUNCIONANDO CORRECTAMENTE")
        print("=" * 60)
        print("\n💡 FLUJO RECOMENDADO:")
        print("1. Hacer búsquedas en la web de Apollo.io")
        print("2. Agregar contactos interesantes a tu CRM (botón 'Add to CRM')")
        print("3. Usar este script para extraer todos los contactos del CRM")
        print("4. Importar a Supabase active_contacts")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_crm_access()


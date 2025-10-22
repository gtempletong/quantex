#!/usr/bin/env python3
"""
Apollo.io API Client
Cliente para interactuar con la API de Apollo.io
"""

import os
import sys
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApolloClient:
    """Cliente para interactuar con Apollo.io API"""
    
    BASE_URL = "https://api.apollo.io/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializar cliente de Apollo.io
        
        Args:
            api_key: API key de Apollo.io (si no se proporciona, se busca en env)
        """
        # Buscar API key (soporta APOLLO_API_KEY o APOLO_API_KEY)
        self.api_key = api_key or os.getenv("APOLLO_API_KEY") or os.getenv("APOLO_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key de Apollo.io no configurada. Usa APOLLO_API_KEY o APOLO_API_KEY en .env")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
            "Cache-Control": "no-cache"
        }
        
        logger.info("Apollo.io Client inicializado correctamente")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Hacer request a la API de Apollo.io
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            data: Datos para enviar en el body (POST/PUT)
            params: Parámetros para la URL (GET)
            
        Returns:
            Respuesta JSON de la API
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP en Apollo.io API: {e}")
            logger.error(f"Response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Error en Apollo.io API: {e}")
            raise
    
    # ========================================
    # PEOPLE SEARCH
    # ========================================
    
    def search_people(
        self,
        person_titles: Optional[List[str]] = None,
        person_locations: Optional[List[str]] = None,
        person_seniorities: Optional[List[str]] = None,
        organization_locations: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        organization_industry_tag_ids: Optional[List[str]] = None,
        q_keywords: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """
        Buscar personas en Apollo.io
        
        Args:
            person_titles: Títulos de trabajo (ej: ["CEO", "CFO", "Director"])
            person_locations: Ubicaciones (ej: ["Chile", "Santiago, Chile"])
            person_seniorities: Niveles de seniority (ej: ["senior", "executive", "director"])
            organization_locations: Ubicaciones de organizaciones
            organization_num_employees_ranges: Rangos de empleados (ej: ["1,10", "11,50", "51,200"])
            organization_industry_tag_ids: IDs de industrias
            q_keywords: Palabras clave de búsqueda
            page: Número de página
            per_page: Resultados por página (máx 100)
            
        Returns:
            Diccionario con resultados de búsqueda
        """
        data = {
            "page": page,
            "per_page": min(per_page, 100)  # Máximo 100 por página
        }
        
        if person_titles:
            data["person_titles"] = person_titles
        if person_locations:
            data["person_locations"] = person_locations
        if person_seniorities:
            data["person_seniorities"] = person_seniorities
        if organization_locations:
            data["organization_locations"] = organization_locations
        if organization_num_employees_ranges:
            data["organization_num_employees_ranges"] = organization_num_employees_ranges
        if organization_industry_tag_ids:
            data["organization_industry_tag_ids"] = organization_industry_tag_ids
        if q_keywords:
            data["q_keywords"] = q_keywords
        
        logger.info(f"Buscando personas en Apollo.io con filtros: {data}")
        
        result = self._make_request("POST", "mixed_people/search", data=data)
        
        logger.info(f"Resultados encontrados: {result.get('pagination', {}).get('total_entries', 0)}")
        
        return result
    
    # ========================================
    # PEOPLE ENRICHMENT
    # ========================================
    
    def enrich_person(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Dict:
        """
        Enriquecer datos de una persona
        
        Args:
            email: Email de la persona
            first_name: Nombre
            last_name: Apellido
            organization_name: Nombre de la organización
            domain: Dominio de la empresa
            linkedin_url: URL de LinkedIn
            
        Returns:
            Datos enriquecidos de la persona
        """
        data = {}
        
        if email:
            data["email"] = email
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if organization_name:
            data["organization_name"] = organization_name
        if domain:
            data["domain"] = domain
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        
        logger.info(f"Enriqueciendo persona: {data}")
        
        result = self._make_request("POST", "people/match", data=data)
        
        return result
    
    # ========================================
    # ORGANIZATION SEARCH
    # ========================================
    
    def search_organizations(
        self,
        organization_locations: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        organization_industry_tag_ids: Optional[List[str]] = None,
        q_organization_name: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """
        Buscar organizaciones en Apollo.io
        
        Args:
            organization_locations: Ubicaciones
            organization_num_employees_ranges: Rangos de empleados
            organization_industry_tag_ids: IDs de industrias
            q_organization_name: Nombre de organización
            page: Número de página
            per_page: Resultados por página
            
        Returns:
            Diccionario con resultados de búsqueda
        """
        data = {
            "page": page,
            "per_page": min(per_page, 100)
        }
        
        if organization_locations:
            data["organization_locations"] = organization_locations
        if organization_num_employees_ranges:
            data["organization_num_employees_ranges"] = organization_num_employees_ranges
        if organization_industry_tag_ids:
            data["organization_industry_tag_ids"] = organization_industry_tag_ids
        if q_organization_name:
            data["q_organization_name"] = q_organization_name
        
        logger.info(f"Buscando organizaciones en Apollo.io: {data}")
        
        result = self._make_request("POST", "mixed_companies/search", data=data)
        
        return result
    
    # ========================================
    # API USAGE STATS
    # ========================================
    
    def get_usage_stats(self) -> Dict:
        """
        Obtener estadísticas de uso de la API
        
        Returns:
            Estadísticas de uso (créditos, rate limits, etc.)
        """
        logger.info("Obteniendo estadísticas de uso de Apollo.io")
        
        result = self._make_request("GET", "auth/health")
        
        return result


def test_apollo_connection():
    """Probar conexión con Apollo.io"""
    print("=" * 60)
    print("🚀 PROBANDO CONEXIÓN CON APOLLO.IO")
    print("=" * 60)
    
    try:
        # Inicializar cliente
        client = ApolloClient()
        print("✅ Cliente inicializado correctamente")
        
        # Probar obtener estadísticas de uso
        print("\n📊 Obteniendo estadísticas de uso...")
        stats = client.get_usage_stats()
        print(f"✅ Conexión exitosa!")
        print(f"\nEstadísticas de uso:")
        print(json.dumps(stats, indent=2))
        
        # Probar búsqueda simple
        print("\n🔍 Probando búsqueda de personas...")
        print("Búsqueda: CEOs en Chile")
        
        results = client.search_people(
            person_titles=["CEO", "Chief Executive Officer"],
            person_locations=["Chile"],
            per_page=5
        )
        
        total = results.get('pagination', {}).get('total_entries', 0)
        people = results.get('people', [])
        
        print(f"✅ Búsqueda exitosa!")
        print(f"Total de resultados disponibles: {total}")
        print(f"Mostrando primeros {len(people)} resultados:")
        
        for i, person in enumerate(people, 1):
            print(f"\n{i}. {person.get('name', 'N/A')}")
            print(f"   Título: {person.get('title', 'N/A')}")
            print(f"   Empresa: {person.get('organization', {}).get('name', 'N/A')}")
            print(f"   Email: {person.get('email', 'N/A')}")
            print(f"   LinkedIn: {person.get('linkedin_url', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS EXITOSAS")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_apollo_connection()


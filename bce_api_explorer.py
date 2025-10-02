#!/usr/bin/env python3
"""
BCE Data Portal API Explorer
Script para investigar sistemáticamente la nueva API del BCE y encontrar yield curves
"""

import requests
import json
import time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

class BCEExplorer:
    def __init__(self):
        self.base_url = "https://data-api.ecb.europa.eu"
        self.session = requests.Session()
        
        # Headers específicos según la documentación SDMX del BCE
        self.headers = {
            'Accept': 'application/vnd.sdmx.genericdata+xml;version=2.1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def explore_endpoint(self, endpoint, description=""):
        """Explora un endpoint específico y documenta la respuesta"""
        url = urljoin(self.base_url, endpoint)
        print(f"\n--- Explorando {description or endpoint} ---")
        print(f"URL: {url}")
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            if response.status_code == 200:
                content_preview = response.text[:500] if len(response.text) > 500 else response.text
                print(f"Content Preview:\n{content_preview}")
                
                # Si es XML, intentar parsearlo para estructura
                if 'xml' in response.headers.get('Content-Type', ''):
                    try:
                        root = self.parse_xml(response.text)
                        if root is not None:
                            print(f"XML Structure: <{root.tag}> with {len(root)} children")
                    except Exception as e:
                        print(f"XML Parse Error: {e}")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Request Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    def parse_xml(self, xml_content):
        """Parsea XML y extrae estructura"""
        try:
            root = ET.fromstring(xml_content)
            return root
        except ET.ParseError:
            return None
    
    def explore_structure(self):
        """Exploración sistemática de endpoints según SDMX"""
        
        endpoints_to_explore = [
            # Endpoints principales según SDMX
            ("/service/data/dataflow", "Dataflow Catalog"),
            ("/service/metadata/dataflow", "Dataflow Metadata"),
            ("/service/metadata/datastructure", "Data Structure Definitions"),
            ("/service/metadata/conceptscheme", "Concept Schemes"),
            ("/service/metadata/codescheme", "Code Schemes"),
            ("/service/data/dataflow/YCB", "Yield Curve Bundle (YCB)"),
            ("/service/data/dataflow/MFI", "Monetary Financial Institutions"),
            ("/service/data/dataflow/QSA", "Quarterly Sector Accounts"),
            ("/service/data/YCB", "Direct Yield Curve Data"),
            ("/service/data/YCB/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y", "YCB Specific Curve"),
            
            # Intentar otros identificadores comunes del BCE
            ("/service/data/YIELD", "Yield Data"),
            ("/service/data/GOVBU", "Government Bonds"),
            ("/service/data/RATES", "Interest Rates"),
            ("/service/data/CURVE", "Yield Curves"),
            
            # Explorar categorías
            ("/service/metadata/categoryscheme", "Category Scheme"),
            ("/service/data/categoryscheme", "Data Category Scheme"),
        ]
        
        print("=== EXPLORACIÓN SISTEMÁTICA DE LA API BCE ===\n")
        
        for endpoint, description in endpoints_to_explore:
            self.explore_endpoint(endpoint, description)
            time.sleep(1)
    
    def search_yield_curves(self):
        """Búsqueda específica para yield curves"""
        print("\n=== BÚSQUEDA ESPECÍFICA DE YIELD CURVES ===")
        
        # Intentar diferentes estructuras posibles
        yield_structures = [
            "/service/data/dataflow/YCB/data/{}",
            "/service/data/YCB/{}",
            "/service/data/yield/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y",
            "/service/data/dataflow/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y/data",
            "/service/data/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y"
        ]
        
        # Nuestro ticker específico que usábamos
        ticker = "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y"
        
        for template in yield_structures:
            endpoint = template.format(ticker)
            self.explore_endpoint(endpoint, f"Yield Curve Template: {template}")
    
    def analyze_errors(self):
        """Analiza errores comunes y sugiere soluciones"""
        print("\n=== ANÁLISIS DE ERRORES COMUNES ===")
        
        common_endpoints = ["/service/data", "/service/metadata"]
        
        for endpoint in common_endpoints:
            print(f"\nProbando headers alternativos para {endpoint}:")
            
            alternative_headers = [
                {'Accept': 'application/xml'},
                {'Accept': 'text/xml'},
                {'Accept': 'application/vnd.sdmx.structurespecificdata+xml;version=2.1'},
                {'Accept': 'application/vnd.ecb.data+csv;version=1.0.0'},
                {'Accept': 'text/csv'},
            ]
            
            for headers in alternative_headers:
                try:
                    url = urljoin(self.base_url, endpoint)
                    response = self.session.get(url, headers=headers, timeout=5)
                    print(f"  {headers['Accept']}: {response.status_code}")
                    if response.status_code != 404:
                        print(f"    Possible success! Content: {response.text[:200]}")
                except Exception as e:
                    print(f"  {headers['Accept']}: Error - {e}")

def main():
    print("🚀 BCE Data Portal API Explorer")
    print("=" * 50)
    
    explorer = BCEExplorer()
    
    # Exploración sistemática
    explorer.explore_structure()
    
    # Búsqueda específica de yield curves  
    explorer.search_yield_curves()
    
    # Análisis de headers y errores
    explorer.analyze_errors()
    
    print("\n✅ Exploración completada")
    print("\n📝 Próximos pasos:")
    print("1. Analizar los endpoints que devuelven 200/estructura XML")
    print("2. Identificar la estructura correcta de yield curves")
    print("3. Mapear identificadores antiguos a nuevos")
    print("4. Actualizar bce_client.py con la nueva estructura")

if __name__ == "__main__":
    main()



















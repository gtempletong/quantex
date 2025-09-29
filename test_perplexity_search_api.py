#!/usr/bin/env python3
"""
Script para probar la nueva Perplexity Search API
Compara resultados con la API tradicional y evalúa costos
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from perplexity import Perplexity

# Cargar variables de entorno
load_dotenv()

class PerplexitySearchTester:
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY no encontrada en variables de entorno")
        
        # URLs de las APIs
        self.chat_url = "https://api.perplexity.ai/chat/completions"
        
        # Inicializar cliente de Perplexity para Search API
        self.perplexity_client = Perplexity(api_key=self.api_key)
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Queries de prueba para comparar
        self.test_queries = [
            "¿Cuáles son las últimas noticias sobre el mercado de cobre hoy?",
            "¿Qué está pasando con el peso chileno en las últimas 24 horas?",
            "Análisis del DXY y su impacto en monedas emergentes",
            "Tendencias del mercado de commodities en septiembre 2025"
        ]

    def test_traditional_api(self, query: str) -> Dict:
        """Prueba la API tradicional de Perplexity (chat completions)"""
        print(f"Probando API tradicional: {query[:50]}...")
        
        payload = {
            "model": "sonar-pro",
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1000,
            "temperature": 0.3,
            "return_citations": True
        }
        
        try:
            start_time = time.time()
            response = requests.post(self.chat_url, headers=self.headers, json=payload)
            response.raise_for_status()
            end_time = time.time()
            
            result = response.json()
            return {
                "api_type": "traditional",
                "query": query,
                "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": result.get("citations", []),
                "usage": result.get("usage", {}),
                "latency": end_time - start_time,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"api_type": "traditional", "query": query, "error": str(e)}

    def test_search_api(self, query: str) -> Dict:
        """Prueba la nueva Search API de Perplexity usando el SDK oficial"""
        print(f"Probando Search API: {query[:50]}...")
        
        try:
            start_time = time.time()
            
            # Usar el SDK oficial de Perplexity
            search = self.perplexity_client.search.create(
                query=query,
                max_results=10,
                max_tokens_per_page=1024
            )
            
            end_time = time.time()
            
            # Convertir resultados a formato estándar
            results = []
            if hasattr(search, 'results'):
                for result in search.results:
                    results.append({
                        "title": getattr(result, 'title', ''),
                        "url": getattr(result, 'url', ''),
                        "snippet": getattr(result, 'snippet', ''),
                        "published_date": getattr(result, 'published_date', '')
                    })
            
            return {
                "api_type": "search",
                "query": query,
                "results": results,
                "latency": end_time - start_time,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"api_type": "search", "query": query, "error": str(e)}

    def compare_apis(self, query: str) -> Dict:
        """Compara ambas APIs con la misma consulta"""
        print(f"\nComparando APIs para: {query}")
        print("=" * 60)
        
        # Probar API tradicional
        traditional_result = self.test_traditional_api(query)
        
        # Probar Search API
        search_result = self.test_search_api(query)
        
        # Análisis comparativo
        comparison = {
            "query": query,
            "traditional": traditional_result,
            "search": search_result,
            "comparison": {
                "traditional_latency": traditional_result.get("latency", 0),
                "search_latency": search_result.get("latency", 0),
                "traditional_tokens": traditional_result.get("usage", {}).get("total_tokens", 0),
                "traditional_cost": traditional_result.get("usage", {}).get("cost", {}).get("total_cost", 0),
                "search_cost": 0.005  # $5 per 1K requests = $0.005 per request
            }
        }
        
        return comparison

    def analyze_search_results(self, search_result: Dict) -> Dict:
        """Analiza la calidad de los resultados de la Search API"""
        if "error" in search_result:
            return {"error": "No se pudieron obtener resultados"}
        
        results = search_result.get("results", [])
        
        analysis = {
            "total_results": len(results),
            "domains": list(set([r.get("url", "").split("/")[2] for r in results if r.get("url")])),
            "avg_snippet_length": sum([len(r.get("snippet", "")) for r in results]) / len(results) if results else 0,
            "recent_results": len([r for r in results if self.is_recent(r.get("published_date", ""))]),
            "quality_score": self.calculate_quality_score(results)
        }
        
        return analysis

    def is_recent(self, date_str: str) -> bool:
        """Verifica si un resultado es reciente (últimos 7 días)"""
        if not date_str:
            return False
        try:
            # Asumir formato ISO o similar
            from datetime import datetime, timedelta
            result_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return result_date > datetime.now() - timedelta(days=7)
        except:
            return False

    def calculate_quality_score(self, results: List[Dict]) -> float:
        """Calcula un score de calidad basado en varios factores"""
        if not results:
            return 0.0
        
        score = 0.0
        
        for result in results:
            # Factor 1: Longitud del snippet (más largo = más informativo)
            snippet_len = len(result.get("snippet", ""))
            if snippet_len > 200:
                score += 1.0
            elif snippet_len > 100:
                score += 0.5
            
            # Factor 2: Presencia de título
            if result.get("title"):
                score += 0.5
            
            # Factor 3: URL confiable
            url = result.get("url", "")
            if any(domain in url for domain in ["reuters.com", "bloomberg.com", "wsj.com", "ft.com"]):
                score += 1.0
            elif any(domain in url for domain in ["cnn.com", "bbc.com", "nytimes.com"]):
                score += 0.8
        
        return min(score / len(results), 5.0)  # Normalizar a 0-5

    def run_comprehensive_test(self):
        """Ejecuta una prueba comprensiva de ambas APIs"""
        print("INICIANDO PRUEBA COMPRENSIVA DE PERPLEXITY APIs")
        print("=" * 70)
        
        all_results = []
        
        for i, query in enumerate(self.test_queries, 1):
            print(f"\n📋 Prueba {i}/{len(self.test_queries)}")
            comparison = self.compare_apis(query)
            all_results.append(comparison)
            
            # Análisis de resultados
            if "search" in comparison and "error" not in comparison["search"]:
                analysis = self.analyze_search_results(comparison["search"])
                comparison["search_analysis"] = analysis
            
            time.sleep(2)  # Rate limiting
        
        # Resumen final
        self.generate_summary(all_results)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"perplexity_api_comparison_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Resultados guardados en: {filename}")
        return all_results

    def generate_summary(self, results: List[Dict]):
        """Genera un resumen de la comparación"""
        print("\nRESUMEN DE COMPARACION")
        print("=" * 40)
        
        traditional_latencies = []
        search_latencies = []
        traditional_costs = []
        search_costs = []
        
        for result in results:
            if "traditional" in result and "latency" in result["traditional"]:
                traditional_latencies.append(result["traditional"]["latency"])
            if "search" in result and "latency" in result["search"]:
                search_latencies.append(result["search"]["latency"])
            if "traditional" in result and "usage" in result["traditional"]:
                cost = result["traditional"]["usage"].get("cost", {}).get("total_cost", 0)
                traditional_costs.append(cost)
            search_costs.append(0.005)  # $5 per 1K requests
        
        print(f"Latencia promedio:")
        print(f"  API Tradicional: {sum(traditional_latencies)/len(traditional_latencies):.2f}s")
        print(f"  Search API: {sum(search_latencies)/len(search_latencies):.2f}s")
        
        print(f"\nCosto promedio por consulta:")
        print(f"  API Tradicional: ${sum(traditional_costs)/len(traditional_costs):.4f}")
        print(f"  Search API: ${sum(search_costs)/len(search_costs):.4f}")
        
        print(f"\nAhorro de costo: {((sum(traditional_costs)/len(traditional_costs)) - (sum(search_costs)/len(search_costs))):.4f} por consulta")

def main():
    """Función principal con menú interactivo"""
    try:
        tester = PerplexitySearchTester()
        
        print("COMPARADOR DE PERPLEXITY APIs")
        print("=" * 40)
        print("1. Probar API tradicional")
        print("2. Probar Search API")
        print("3. Comparar ambas APIs")
        print("4. Prueba comprensiva")
        print("5. Salir")
        
        while True:
            choice = input("\nSelecciona una opción (1-5): ").strip()
            
            if choice == "1":
                query = input("Ingresa tu consulta: ")
                result = tester.test_traditional_api(query)
                print(f"\nResultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "2":
                query = input("Ingresa tu consulta: ")
                result = tester.test_search_api(query)
                print(f"\nResultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "3":
                query = input("Ingresa tu consulta: ")
                comparison = tester.compare_apis(query)
                print(f"\nComparación: {json.dumps(comparison, indent=2, ensure_ascii=False)}")
                
            elif choice == "4":
                tester.run_comprehensive_test()
                
            elif choice == "5":
                print("Hasta luego!")
                break
                
            else:
                print("Opcion invalida")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

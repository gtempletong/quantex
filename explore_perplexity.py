#!/usr/bin/env python3
"""
Script de exploración de capacidades de Perplexity API
Permite experimentar con diferentes modelos, parámetros y casos de uso
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class PerplexityExplorer:
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY no encontrada en variables de entorno")
        
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Modelos disponibles
        self.models = {
            "sonar-pro": "Modelo más potente para análisis complejos",
            "sonar-medium": "Modelo balanceado para uso general",
            "sonar-small": "Modelo rápido para consultas simples"
        }
        
        # Parámetros experimentales
        self.advanced_params = {
            "temperature": [0.1, 0.3, 0.7, 1.0],
            "top_p": [0.1, 0.5, 0.9, 1.0],
            "max_tokens": [100, 500, 1000, 2000],
            "return_citations": [True, False],
            "search_recency_days": [1, 7, 30, 365],
            "top_k": [1, 3, 5, 10],
            "stream": [True, False]
        }

    def test_basic_query(self, query: str, model: str = "sonar-pro") -> Dict:
        """Prueba básica de una consulta"""
        print(f"\nProbando consulta basica con {model}")
        print(f"Query: {query}")
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 500,
            "temperature": 0.3,
            "return_citations": True
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return {
                "model": model,
                "query": query,
                "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": result.get("citations", []),
                "usage": result.get("usage", {}),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "query": query, "model": model}

    def test_advanced_parameters(self, query: str, model: str = "sonar-pro") -> List[Dict]:
        """Prueba diferentes combinaciones de parámetros avanzados"""
        print(f"\n⚙️ Probando parámetros avanzados con {model}")
        
        results = []
        
        # Combinaciones interesantes para probar
        test_configs = [
            {"temperature": 0.1, "top_p": 0.9, "max_tokens": 1000, "return_citations": True, "search_recency_days": 7},
            {"temperature": 0.7, "top_p": 0.5, "max_tokens": 500, "return_citations": True, "search_recency_days": 30},
            {"temperature": 1.0, "top_p": 0.1, "max_tokens": 2000, "return_citations": False, "search_recency_days": 1},
            {"temperature": 0.3, "top_p": 1.0, "max_tokens": 1000, "return_citations": True, "search_recency_days": 365}
        ]
        
        for i, config in enumerate(test_configs):
            print(f"  Configuración {i+1}: {config}")
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": query}],
                **config
            }
            
            try:
                response = requests.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                results.append({
                    "config": config,
                    "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "citations": result.get("citations", []),
                    "usage": result.get("usage", {}),
                    "timestamp": datetime.now().isoformat()
                })
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                results.append({"config": config, "error": str(e)})
        
        return results

    def test_different_models(self, query: str) -> List[Dict]:
        """Prueba la misma consulta con diferentes modelos"""
        print(f"\n🤖 Probando diferentes modelos")
        print(f"Query: {query}")
        
        results = []
        
        for model, description in self.models.items():
            print(f"  Probando {model}: {description}")
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1000,
                "temperature": 0.3,
                "return_citations": True
            }
            
            try:
                response = requests.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                results.append({
                    "model": model,
                    "description": description,
                    "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "citations": result.get("citations", []),
                    "usage": result.get("usage", {}),
                    "timestamp": datetime.now().isoformat()
                })
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                results.append({"model": model, "error": str(e)})
        
        return results

    def test_specialized_queries(self, model: str = "sonar-pro") -> List[Dict]:
        """Prueba consultas especializadas para diferentes casos de uso"""
        print(f"\n🎯 Probando consultas especializadas")
        
        queries = [
            {
                "category": "Análisis Financiero",
                "query": "¿Cuáles son las principales tendencias del mercado de cobre en 2025? Incluye datos recientes de inventarios LME y SHFE."
            },
            {
                "category": "Noticias Recientes",
                "query": "¿Qué ha pasado con el peso chileno en las últimas 48 horas? Incluye factores macroeconómicos relevantes."
            },
            {
                "category": "Análisis Técnico",
                "query": "Analiza el gráfico técnico del USD/CLP y proporciona niveles de soporte y resistencia clave."
            },
            {
                "category": "Investigación Profunda",
                "query": "Investiga el impacto de la política monetaria de la Fed en las monedas emergentes, especialmente en América Latina."
            }
        ]
        
        results = []
        
        for query_info in queries:
            print(f"  {query_info['category']}: {query_info['query'][:50]}...")
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": query_info['query']}],
                "max_tokens": 1500,
                "temperature": 0.3,
                "return_citations": True,
                "search_recency_days": 7
            }
            
            try:
                response = requests.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                results.append({
                    "category": query_info['category'],
                    "query": query_info['query'],
                    "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "citations": result.get("citations", []),
                    "usage": result.get("usage", {}),
                    "timestamp": datetime.now().isoformat()
                })
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                results.append({"category": query_info['category'], "error": str(e)})
        
        return results

    def test_streaming(self, query: str, model: str = "sonar-pro") -> Dict:
        """Prueba el modo streaming"""
        print(f"\n🌊 Probando modo streaming")
        print(f"Query: {query}")
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1000,
            "temperature": 0.3,
            "stream": True
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, stream=True)
            response.raise_for_status()
            
            print("  Respuesta streaming:")
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    print(content, end='', flush=True)
                                    full_response += content
                        except json.JSONDecodeError:
                            continue
            
            print("\n")
            return {
                "streaming": True,
                "response": full_response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"streaming": True, "error": str(e)}

    def save_results(self, results: List[Dict], filename: str = None):
        """Guarda los resultados en un archivo JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"perplexity_exploration_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Resultados guardados en: {filename}")

    def run_full_exploration(self):
        """Ejecuta una exploración completa de las capacidades"""
        print("Iniciando exploracion completa de Perplexity API")
        print("=" * 60)
        
        all_results = []
        
        # 1. Prueba básica con sonar-pro
        basic_query = "¿Cuál es el precio actual del cobre y qué factores lo están afectando?"
        basic_result = self.test_basic_query(basic_query, "sonar-pro")
        all_results.append({"test_type": "basic", "result": basic_result})
        
        # 2. Parámetros avanzados con sonar-pro
        advanced_results = self.test_advanced_parameters(basic_query, "sonar-pro")
        all_results.append({"test_type": "advanced_params", "results": advanced_results})
        
        # 3. Consultas especializadas con sonar-pro
        specialized_results = self.test_specialized_queries("sonar-pro")
        all_results.append({"test_type": "specialized", "results": specialized_results})
        
        # 4. Streaming con sonar-pro
        streaming_result = self.test_streaming("Explica brevemente las tendencias del mercado de commodities", "sonar-pro")
        all_results.append({"test_type": "streaming", "result": streaming_result})
        
        # Guardar resultados
        self.save_results(all_results)
        
        print("\nExploracion completa finalizada")
        print("Revisa el archivo JSON generado para analizar los resultados")

def main():
    """Función principal con menú interactivo"""
    try:
        explorer = PerplexityExplorer()
        
        print("EXPLORADOR DE PERPLEXITY API")
        print("=" * 40)
        print("1. Prueba básica")
        print("2. Diferentes modelos")
        print("3. Parámetros avanzados")
        print("4. Consultas especializadas")
        print("5. Modo streaming")
        print("6. Exploración completa")
        print("7. Salir")
        
        while True:
            choice = input("\nSelecciona una opción (1-7): ").strip()
            
            if choice == "1":
                query = input("Ingresa tu consulta: ")
                result = explorer.test_basic_query(query)
                print(f"\nResultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "2":
                query = input("Ingresa tu consulta: ")
                results = explorer.test_different_models(query)
                explorer.save_results(results, "model_comparison.json")
                
            elif choice == "3":
                query = input("Ingresa tu consulta: ")
                results = explorer.test_advanced_parameters(query)
                explorer.save_results(results, "advanced_params.json")
                
            elif choice == "4":
                results = explorer.test_specialized_queries()
                explorer.save_results(results, "specialized_queries.json")
                
            elif choice == "5":
                query = input("Ingresa tu consulta: ")
                result = explorer.test_streaming(query)
                print(f"\nResultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "6":
                explorer.run_full_exploration()
                
            elif choice == "7":
                print("Hasta luego!")
                break
                
            else:
                print("Opcion invalida")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

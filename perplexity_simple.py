#!/usr/bin/env python3
"""
Script simple para hacer fine-tuning con Perplexity sonar-pro
Solo pregunta, respuesta y parámetros ajustables
"""

import os
import json
import requests
import textwrap
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def ask_perplexity(question, temperature=0.3, max_tokens=1000, return_citations=True, search_recency_days=7):
    """Hace una pregunta simple a Perplexity sonar-pro"""
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("Error: PERPLEXITY_API_KEY no encontrada")
        return None
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": question}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "return_citations": return_citations,
        "search_recency_days": search_recency_days
    }
    
    try:
        print(f"\nPREGUNTA:")
        print(f"{'-' * 60}")
        # Hacer wrap de la pregunta también
        wrapped_question = textwrap.fill(question, width=80, initial_indent="", subsequent_indent="")
        print(wrapped_question)
        print(f"\nPARAMETROS:")
        print(f"  Temperature: {temperature}")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Citations: {return_citations}")
        print(f"  Recency days: {search_recency_days}")
        print(f"\nConsultando a Perplexity...")
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = result.get("citations", [])
        usage = result.get("usage", {})
        
        print(f"\nRESPUESTA:")
        print(f"{'-' * 60}")
        # Hacer wrap del texto para mejor legibilidad
        wrapped_content = textwrap.fill(content, width=80, initial_indent="", subsequent_indent="")
        print(wrapped_content)
        
        if citations:
            print(f"\nCITAS ({len(citations)}):")
            print(f"{'-' * 60}")
            for i, citation in enumerate(citations, 1):
                print(f"{i}. {citation}")
        
        print(f"\nUSO:")
        print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")
        print(f"  Prompt: {usage.get('prompt_tokens', 'N/A')}")
        print(f"  Completion: {usage.get('completion_tokens', 'N/A')}")
        
        return {
            "question": question,
            "answer": content,
            "citations": citations,
            "usage": usage,
            "params": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "return_citations": return_citations,
                "search_recency_days": search_recency_days
            }
        }
        
    except Exception as e:
        print(f"\nError: {e}")
        return None

def main():
    """Función principal con menú simple"""
    print("PERPLEXITY FINE-TUNING - SONAR PRO")
    print("=" * 50)
    
    # Pregunta por defecto
    default_question = "¿Cuál es el precio actual del cobre y qué factores lo están afectando?"
    
    while True:
        print(f"\nOPCIONES:")
        print("1. Hacer pregunta con parámetros por defecto")
        print("2. Hacer pregunta personalizada")
        print("3. Probar diferentes parámetros")
        print("4. Salir")
        
        choice = input("\nSelecciona (1-4): ").strip()
        
        if choice == "1":
            # Parámetros por defecto
            result = ask_perplexity(default_question)
            
        elif choice == "2":
            # Pregunta personalizada
            question = input("\nIngresa tu pregunta: ").strip()
            if question:
                result = ask_perplexity(question)
            else:
                print("Pregunta vacía, usando pregunta por defecto")
                result = ask_perplexity(default_question)
                
        elif choice == "3":
            # Diferentes parámetros
            question = input("\nPregunta (Enter para usar por defecto): ").strip()
            if not question:
                question = default_question
            
            print(f"\nAJUSTAR PARAMETROS:")
            try:
                temp = float(input("Temperature (0.1-1.0, default 0.3): ") or "0.3")
                tokens = int(input("Max tokens (100-2000, default 1000): ") or "1000")
                recency = int(input("Recency days (1-365, default 7): ") or "7")
                citations = input("Return citations? (y/n, default y): ").strip().lower()
                citations = citations != "n"
                
                result = ask_perplexity(question, temp, tokens, citations, recency)
                
            except ValueError:
                print("Parámetros inválidos, usando valores por defecto")
                result = ask_perplexity(question)
                
        elif choice == "4":
            print("Hasta luego!")
            break
            
        else:
            print("Opcion invalida")

if __name__ == "__main__":
    main()

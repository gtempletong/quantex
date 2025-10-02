#!/usr/bin/env python3
"""
Script de prueba simple para diagnosticar el filtro de FXStreet
"""

def test_filter(title, summary, filter_config):
    text = f"{title} {summary}".lower()
    
    print(f"\n=== ANALISIS DE FILTRO ===")
    print(f"Texto: '{text}'")
    
    # Obtener configuración del filtro
    specific_keywords = [kw.lower() for kw in filter_config.get('specific_keywords', [])]
    general_keywords = [kw.lower() for kw in filter_config.get('general_keywords', [])]
    exclude_keywords = [kw.lower() for kw in filter_config.get('exclude_keywords', [])]
    target_pairs = [pair.lower() for pair in filter_config.get('target_pairs', [])]
    filter_logic = filter_config.get('filter_logic', 'any_keyword')
    
    print(f"Specific keywords: {specific_keywords}")
    print(f"General keywords: {general_keywords}")
    print(f"Exclude keywords: {exclude_keywords}")
    print(f"Target pairs: {target_pairs}")
    print(f"Filter logic: {filter_logic}")
    
    # 1. Verificar exclusiones primero
    if exclude_keywords:
        for exclude in exclude_keywords:
            if exclude in text:
                print(f">>> EXCLUIDO por keyword: {exclude}")
                return False
        print(f">>> Sin exclusiones encontradas")
    
    # 2. Verificar pares de divisas específicos
    if target_pairs:
        for pair in target_pairs:
            if pair in text:
                print(f">>> APROBADO por par específico: {pair}")
                return True
        print(f">>> Ningun par específico encontrado")
    
    # 3. Aplicar lógica del filtro
    if filter_logic == "specific_or_general":
        has_specific = any(currency in text for currency in specific_keywords)
        has_general = any(general in text for general in general_keywords)
        
        print(f">>> Specific keywords encontradas: {has_specific}")
        if has_specific:
            matched_specific = [kw for kw in specific_keywords if kw in text]
            print(f"    Matches specific: {matched_specific}")
            
        print(f">>> General keywords encontradas: {has_general}")
        if has_general:
            matched_general = [kw for kw in general_keywords if kw in text]
            print(f"    Matches general: {matched_general}")
        
        result = has_specific or has_general
        print(f">>> RESULTADO: {'APROBADO' if result else 'RECHAZADO'} por filtro específico/general")
        return result

if __name__ == "__main__":
    # Test con la noticia real
    title = "EUR/USD gains above 1.1700 due to rising Fed rate cut bets"
    summary = ""
    
    # Configuración de FXStreet del YAML
    filter_config = {
        "filter_logic": "specific_or_general",
        "general_keywords": ["forex", "divisas"],
        "specific_keywords": ["CLP", "EUR/USD", "DXY"],
        "exclude_keywords": ["CHF", "JPY", "AUD", "CAD", "GBP", "NZD"],
        "target_pairs": ["EUR/USD", "USD/CLP", "CLP/USD"]
    }
    
    print("=" * 80)
    print("EVALUACION: EUR/USD gains above 1.1700 due to rising Fed rate cut bets")
    print("=" * 80)
    
    result = test_filter(title, summary, filter_config)
    print(f"\nRESULTADO FINAL: {'APROBADO' if result else 'RECHAZADO'}")






























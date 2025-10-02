#!/usr/bin/env python3
"""
Script de prueba para diagnosticar el filtro de FXStreet
"""

def enhanced_prefilter(title: str, summary: str, keywords: list, filter_config: dict = None) -> bool:
    """
    Prefiltro mejorado con configuración desde YAML (copy del source_monitor.py)
    """
    text = f"{title} {summary}".lower()
    
    print(f"\nANALISIS DE FILTRO:")
    print(f"Texto a analizar: '{text}'")
    
    # Si no hay configuración, usar filtro básico
    if not filter_config:
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in text)
        print(f"Filtro básico: {keyword_matches} matches de {len(keywords)} keywords")
        return keyword_matches > 0
    
    # Obtener configuración del filtro
    specific_keywords = [kw.lower() for kw in filter_config.get('specific_keywords', [])]
    general_keywords = [kw.lower() for kw in filter_config.get('general_keywords', [])]
    exclude_keywords = [kw.lower() for kw in filter_config.get('exclude_keywords', [])]
    target_pairs = [pair.lower() for pair in filter_config.get('target_pairs', [])]
    filter_logic = filter_config.get('filter_logic', 'any_keyword')
    
    print(f"🏷️ Specific keywords: {specific_keywords}")
    print(f"🏷️ General keywords: {general_keywords}")
    print(f"❌ Exclude keywords: {exclude_keywords}")
    print(f"💱 Target pairs: {target_pairs}")
    print(f"⚙️ Filter logic: {filter_logic}")
    
    # 1. Verificar exclusiones primero
    if exclude_keywords:
        for exclude in exclude_keywords:
            if exclude in text:
                print(f"      ❌ EXCLUIDO por keyword: {exclude}")
                return False
        print(f"      ✅ Sin exclusiones encontradas")
    
    # 2. Verificar pares de divisas específicos
    if target_pairs:
        for pair in target_pairs:
            if pair in text:
                print(f"      ✅ APROBADO por par específico: {pair}")
                return True
        print(f"      ⏭️ Ningún par específico encontrado")
    
    # 3. Aplicar lógica del filtro
    if filter_logic == "specific_or_general":
        # Debe tener al menos una divisa específica O ser forex general
        has_specific = any(currency in text for currency in specific_keywords)
        has_general = any(general in text for general in general_keywords)
        
        print(f"      🔍 Specific keywords encontradas: {has_specific}")
        if has_specific:
            matched_specific = [kw for kw in specific_keywords if kw in text]
            print(f"         Matches: {matched_specific}")
            
        print(f"      🔍 General keywords encontradas: {has_general}")
        if has_general:
            matched_general = [kw for kw in general_keywords if kw in text]
            print(f"         Matches: {matched_general}")
        
        result = has_specific or has_general
        if result:
            print(f"      ✅ APROBADO por filtro específico/general")
        else:
            print(f"      ❌ RECHAZADO por filtro específico/general")
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
    
    keywords = ["forex", "divisas", "CLP", "EUR", "DXY"]
    
    print("=" * 80)
    print("EVALUACIÓN DE: EUR/USD gains above 1.1700 due to rising Fed rate cut bets")
    print("=" * 80)
    
    result = enhanced_prefilter(title, summary, keywords, filter_config)
    
    print(f"\n🎯 RESULTADO FINAL: {'✅ APROBADO' if result else '❌ RECHAZADO'}")

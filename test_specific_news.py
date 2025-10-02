#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para la noticia de FXStreet que no se está procesando
"""

import os
import sys

# Configurar encoding para emojis en Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar path del proyecto
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.config_loader import get_config_loader

def test_specific_news():
    """Test específico para la noticia EUR/USD que no se procesa"""
    
    # Datos de la noticia específica
    title = "EUR/USD gains above 1.1700 due to rising Fed rate cut bets"
    url = "https://www.fxstreet.com/news/eur-usd-gains-above-11700-due-to-rising-fed-rate-cut-bets-202509290125"
    summary = "EUR/USD gains ground as the US Dollar weakens on increasing odds of further Fed rate cuts. US Personal Consumption Expenditures inflation rose to 2.7% YoY in August, compared to 2.6% prior."
    
    print("🎯 TEST PARA NOTICIA ESPECÍFICA FXSTREET")
    print("=" * 60)
    print(f"📰 TÍTULO: {title}")
    print(f"🔗 URL: {url}")
    print(f"📝 SUMMARY: {summary[:100]}...")
    print()
    
    # PASO 1: Verificar configuración FXStreet
    print("🔍 PASO 1: Verificando configuración FXStreet...")
    
    config_loader = get_config_loader()
    sources = config_loader.get_rss_sources(active_only=True)
    
    fxstreet_source = None
    for source in sources:
        if source.get('id') == 'fxstreet_forex_news':
            fxstreet_source = source
            break
    
    if not fxstreet_source:
        print("❌ ERROR: Configuración FXStreet no encontrada")
        return
    
    print("✅ Configuración FXStreet encontrada")
    
    # Mostrar configuración relevante
    filter_config = fxstreet_source.get('filter_config', {})
    filter_keywords = fxstreet_source.get('filter_keywords', [])
    
    print(f"🎯 Filter Logic: {filter_config.get('filter_logic')}")
    print(f"🔑 Keywords específicas: {filter_config.get('specific_keywords', [])}")
    print(f"🔑 Keywords generales: {filter_config.get('general_keywords', [])}")
    print(f"❌ Keywords excluidas: {filter_config.get('exclude_keywords', [])}")
    print()
    
    # PASO 2: Probar prefiltro directamente
    print("🔍 PASO 2: Probando prefiltro enhanced_prefilter...")
    
    from quantex.core.autoconocimiento.source_monitor import enhanced_prefilter
    
    # Vamos a probar paso a paso el prefiltro
    text = f"{title} {summary}".lower()
    
    # Verificar exclusiones primero
    exclude_keywords = [kw.lower() for kw in filter_config.get('exclude_keywords', [])]
    print(f"🔍 Verificando exclusiones: {exclude_keywords}")
    for exclude in exclude_keywords:
        if exclude in text:
            print(f"❌ EXCLUIDO por keyword: {exclude}")
            return
    
    # Verificar pares específicos
    target_pairs = [pair.lower() for pair in filter_config.get('target_pairs', [])]
    print(f"🔍 Verificando pares específicos: {target_pairs}")
    for pair in target_pairs:
        if pair in text:
            print(f"✅ APROBADO por par específico: {pair}")
            break
    else:
        # Verificar lógica del filtro
        filter_logic = filter_config.get('filter_logic', 'any_keyword')
        print(f"🔍 Aplicando lógica: {filter_logic}")
        
        if filter_logic == "specific_or_general":
            specific_keywords = [kw.lower() for kw in filter_config.get('specific_keywords', [])]
            general_keywords = [kw.lower() for kw in filter_config.get('general_keywords', [])]
            
            has_specific = any(currency in text for currency in specific_keywords)
            has_general = any(general in text for general in general_keywords)
            
            print(f"   Specific matches: {[kw for kw in specific_keywords if kw in text]}")
            print(f"   General matches: {[kw for kw in general_keywords if kw in text]}")
            print(f"   Has specific: {has_specific}")
            print(f"   Has general: {has_general}")
            
            passes = has_specific or has_general
            print(f"✅ Resultado: {'PASA' if passes else 'NO PASA'}")
        else:
            # Fallback
            print("❓ Lógica no reconocida, usando fallback")
    
    # PASO 3: Probar función completa
    print("\n🔍 PASO 3: Probando enhanced_prefilter completo...")
    
    passes_prefilter = enhanced_prefilter(title, summary, filter_keywords, filter_config)
    print(f"✅ Prefiltro completo: {'PASA' if passes_prefilter else 'NO PASA'}")
    
    if not passes_prefilter:
        print("🚨 PROBLEMA ENCONTRADO: La noticia NO pasa el prefiltro")
        return
    
    # PASO 4: Verificar URLs en DB
    print("\n🔍 PASO 4: Verificando si URL existe en base de datos...")
    
    from quantex.core.autoconocimiento.source_monitor import does_url_exist_in_db
    
    url_exists = does_url_exist_in_db(url)
    print(f"🔍 URL existe en DB: {'SÍ' if url_exists else 'NO'}")
    
    if url_exists:
        print("🚨 PROBLEMA: URL ya existe en base de datos")
        return
    else:
        print("✅ URL está libre, puede procesarse")
    
    # PASO 5: Test de scraping (opcional, puede tardar)
    print("\n🔍 PASO 5: ¿Probar scraping del contenido? (puede tardar)")
    print("💡 Para probar scraping ejecuta manualmente:")
    print("   from quantex.core.web_tools import get_firecrawl_scrape")
    print(f"   content = get_firecrawl_scrape('{url}')")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL")
    print("=" * 60)
    print(f"✅ Configuración FXStreet: OK")
    print(f"✅ Prefiltro: {'PASA' if passes_prefilter else 'NO PASA'}")
    print(f"✅ URL en DB: {'EXISTE' if url_exists else 'LIBRE'}")
    
    if passes_prefilter and not url_exists:
        print("\n🎯 CONCLUSIÓN: Esta noticia DEBERÍA procesarse")
        print("🔧 Próximo paso: Ejecutar Source Monitor completo para ver qué pasa")
    else:
        print("\n❌ CONCLUSIÓN: Esta noticia NO debería procesarse")
        print("🔧 Verificar configuración de filtros")

if __name__ == "__main__":
    test_specific_news()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script para diagnosticar problemas con FXStreet en Source Monitor
"""

import os
import sys
import feedparser
from datetime import datetime

# Configurar encoding para evitar problemas con emojis en Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar path del proyecto
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.config_loader import get_config_loader
from quantex.core import database_manager as db

def test_fxstreet_rss():
    """Probar si el feed RSS de FXStreet funciona"""
    print("🔍 PASO 1: Probando feed RSS de FXStreet...")
    
    rss_url = "https://www.fxstreet.com/rss/news"
    
    try:
        feed = feedparser.parse(rss_url)
        print(f"✅ Feed RSS cargado exitosamente")
        print(f"📊 Total entradas en el feed: {len(feed.entries)}")
        
        if feed.entries:
            print(f"\n📰 Últimas 5 noticias:")
            for i, entry in enumerate(feed.entries[:5]):
                print(f"    {i+1}. {entry.get('title', 'Sin título')}")
                print(f"       📅 PubDate: {entry.get('published', 'No disponible')}")
                print(f"       🔗 URL: {entry.get('link', 'No disponible')}")
                print()
        
        return feed.entries
    except Exception as e:
        print(f"❌ Error cargando RSS feed: {e}")
        return []

def test_fxstreet_config():
    """Probar configuración de FXStreet"""
    print("\n🔍 PASO 2: Verificando configuración FXStreet...")
    
    try:
        config_loader = get_config_loader()
        sources = config_loader.get_rss_sources(active_only=True)
        
        fxstreet_source = None
        for source in sources:
            if source.get('id') == 'fxstreet_forex_news':
                fxstreet_source = source
                break
        
        if fxstreet_source:
            print("✅ Configuración FXStreet encontrada:")
            print(f"   📝 ID: {fxstreet_source.get('id')}")
            print(f"   🏢 Publisher: {fxstreet_source.get('publisher')}")
            print(f"   🌐 URL: {fxstreet_source.get('source_url')}")
            print(f"   ✅ Active: {fxstreet_source.get('is_active')}")
            print(f"   🔑 Keywords: {fxstreet_source.get('filter_keywords', [])}")
            
            # Mostrar config avanzada
            filter_config = fxstreet_source.get('filter_config', {})
            if filter_config:
                print(f"   🎯 Filter Logic: {filter_config.get('filter_logic')}")
                print(f"   ➕ Include Keywords: {filter_config.get('specific_keywords', [])}")
                print(f"   ➖ Exclude Keywords: {filter_config.get('exclude_keywords', [])}")
                print(f"   💱 Target Pairs: {filter_config.get('target_pairs', [])}")
            
            return fxstreet_source
        else:
            print("❌ Configuración FXStreet no encontrada")
            return None
            
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return None

def test_prefilter_logic(entries, config):
    """Probar lógica de prefiltrado"""
    print("\n🔍 PASO 3: Probando lógica de prefiltros...")
    
    if not entries or not config:
        print("❌ No hay entradas RSS o configuración para probar")
        return []
    
    # Importar función de prefiltro
    from quantex.core.autoconocimiento.source_monitor import enhanced_prefilter
    
    filtered_entries = []
    
    print("🔍 Aplicando prefiltros a las últimas 3 noticias...")
    
    for i, entry in enumerate(entries[:3]):
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        
        print(f"\n   📰 Noticia {i+1}: {title[:60]}...")
        print(f"   📝 Summary: {summary[:100]}...")
        
        # Probar prefiltro
        filter_config = config.get('filter_config', {})
        filter_keywords = config.get('filter_keywords', [])
        
        passes = enhanced_prefilter(title, summary, filter_keywords, filter_config)
        
        print(f"   ✅ Pasa prefiltro: {passes}")
        
        if passes:
            filtered_entries.append(entry)
    
    print(f"\n📊 Resultado del prefiltrado: {len(filtered_entries)} de {min(3, len(entries))} noticias pasaron")
    
    return filtered_entries

def test_url_exists_in_db():
    """Probar si URLs de FXStreet ya existen en la DB usando MCP Supabase"""
    print("\n🔍 PASO 4: Verificando URLs existentes usando MCP Supabase...")
    print("⚡ NUEVO: Usando MCP en lugar de código interno!")
    
    try:
        # Obtener unas pocas URLs recientes de FXStreet
        feed = feedparser.parse("https://www.fxstreet.com/rss/news")
        if not feed.entries:
            print("❌ No se puede obtener feed para verificar URLs")
            return []
        
        test_urls = [entry.get('link') for entry in feed.entries[:3] if entry.get('link')]
        
        print(f"🔍 Obteniendo {len(test_urls)} URLs recientes...")
        for i, url in enumerate(test_urls, 1):
            print(f"   {i}. {url[:60]}...")
        
        print("\n" + "="*60)
        print("🎯 PRUEBA DEL MCP SUPABASE")
        print("="*60)
        print("Ahora puedes usar Cursor para consultar directamente:")
        print("📝 Copiar estas URLs y preguntar en Cursor:")
        print('   "¿Existe esta URL en mi base de datos? https://www.fxstreet.com/news/..."')
        print("  O también puedes probar:")
        print('   "Muéstrame las últimas noticias de FXStreet en mi base de datos"')
        print('   "¿Cuántas URLs de FXStreet tengo almacenadas?"')
        print('   "Lista las 5 URLs más recientes de Forex en mi DB"')
        print("\n💡 Esto demuestra el cambio de paradigma:")
        print("   ❌ ANTES: Código Python → Supabase → Resultado")
        print("   ✅ AHORA: Pregunta → MCP → Respuesta instantánea")
        
        return test_urls  # Devuelve las URLs para consulta manual
        
    except Exception as e:
        print(f"❌ Error obteniendo URLs para prueba: {e}")
        return []

def run_diagnostic():
    """Ejecutar diagnóstico completo"""
    print("🚀 INICIANDO DIAGNÓSTICO FXSTREET")
    print("=" * 50)
    
    # Paso 1: Probar RSS
    entries = test_fxstreet_rss()
    if not entries:
        print("❌ CRÍTICO: Feed RSS no funciona. Diagnóstico terminado.")
        return
    
    # Paso 2: Verificar configuración
    config = test_fxstreet_config()
    if not config:
        print("❌ CRÍTICO: Configuración no encontrada. Diagnóstico terminado.")
        return
    
    # Paso 3: Probar prefiltros
    filtered = test_prefilter_logic(entries, config)
    
    # Paso 4: Mostrar URLs para consulta MCP
    test_urls = test_url_exists_in_db()
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📋 RESUMEN DEL DIAGNÓSTICO CON MCP")
    print("=" * 50)
    print(f"📰 Total noticias en feed: {len(entries)}")
    print(f"✅ Configuración FXStreet: OK") 
    print(f"🔍 Noticias que pasaron prefiltro: {len(filtered)}")
    print(f"🔗 URLs disponibles para consulta MCP: {len(test_urls)}")
    
    print("\n🚀 PRÓXIMO PASO:")
    print("   Usa Cursor con MCP Supabase para:")
    print("   1. Consultar URLs específicas")
    print("   2. Ver noticias existentes")
    print("   3. Analizar patrones de datos")
    print("   4. Generar insights automáticamente")
    
    print("\n💡 EJEMPLOS DE CONSULTAS MCP:")
    print('   "¿Cuántas noticias de Forex tengo en mi DB?"')
    print('   "Muéstrame las últimas 5 URLs de FXStreet almacenadas"')
    print('   "¿Hay duplicados de URLs de Forex en mi base de datos?"')
    print('   "Analiza el contenido de noticias financieras de la última semana"')

if __name__ == "__main__":
    run_diagnostic()
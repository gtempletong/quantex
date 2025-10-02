#!/usr/bin/env python3
import feedparser

# Verificar el feed RSS de FXStreet
print("=== VERIFICANDO FEED RSS DE FXSTREET ===")
feed_url = "https://www.fxstreet.com/rss/news"
feed = feedparser.parse(feed_url)

print(f"Status: {feed.status}")
print(f"Entradas encontradas: {len(feed.entries)}")

# Buscar la noticia específica del EUR/USD
title_search = "EUR/USD"
found = False

print(f"\n=== BUSCANDO NOTICIAS CON '{title_search}' ===")
for i, entry in enumerate(feed.entries[:10]):  # Solo las primeras 10
    title = entry.get('title', '')
    summary = entry.get('summary', '')
    published = entry.get('published', '')
    
    print(f"\n{i+1}. {title}")
    print(f"   Published: {published}")
    print(f"   Summary: {summary[:100]}...")
    
    if title_search.lower() in title.lower() or title_search.lower() in summary.lower():
        print(f"   *** ENCONTRADA LA NOTICIA EUR/USD ***")
        found = True

if not found:
    print(f"\n❌ No se encontró ninguna noticia con '{title_search}' en las primeras {min(10, len(feed.entries))} noticias")

print(f"\n=== TOTAL DE NOTICIAS DISPONIBLES: {len(feed.entries)} ===")






























import os
import re
import hashlib
from datetime import datetime

from env_loader import load_env_with_fallback
from quantex_integration import MktNewsQuantexIntegration

load_env_with_fallback()

EXPORTS_DIR = os.path.join(os.path.dirname(__file__), 'exports')


def parse_markdown(md_text: str) -> list[dict]:
	items = []
	blocks = re.split(r"\n## ", md_text)
	for block in blocks:
		if not block.strip() or block.startswith('#'):
			continue
		lines = block.strip().splitlines()
		title_line = lines[0]
		title = title_line.split('.', 1)[-1].strip()
		time_text = ''
		content_lines = []
		for ln in lines[1:]:
			if ln.strip().startswith('- Time:'):
				time_text = ln.split('`')[-2] if '`' in ln else ln.split(':',1)[-1].strip()
			else:
				content_lines.append(ln)
		content = '\n'.join([l for l in content_lines if l.strip()])
		# Stable item hash at SOURCE level (before LLM): title + time + content snippet (normalized)
		snippet = re.sub(r"\s+", " ", (content or '')[:200]).strip().lower()
		key = f"{(title or '').strip().lower()}|{(time_text or '').strip()}|{snippet}"
		item_hash = hashlib.sha256(key.encode('utf-8')).hexdigest()
		items.append({"title": title, "time": time_text, "content": content, "item_hash": item_hash})
	return items


def ingest_latest_md():
	latest = os.path.join(EXPORTS_DIR, 'mktnews_latest.md')
	if not os.path.exists(latest):
		print('No se encontró mktnews_latest.md')
		return
	
	with open(latest, 'r', encoding='utf-8') as f:
		md = f.read()
	
	news = parse_markdown(md)
	print(f"🚀 Iniciando ingesta de {len(news)} items con motor unificado de Quantex...")
	
	# Inicializar integración con Quantex
	integration = MktNewsQuantexIntegration()
	
	# Procesar todos los items
	for i, it in enumerate(news, 1):
		print(f"📰 [{i}/{len(news)}] Procesando: {it.get('title', 'Sin título')[:50]}...")
		
		# Preparar item para el motor unificado
		news_item = {
			"title": it.get("title", ""),
			"content": it["content"],
			"time": it.get("time", ""),
			# Usamos un pseudo-URL basado en el hash para deduplicación robusta
			"url": f"mktnews://{it.get('item_hash', '')}",
			"item_hash": it.get("item_hash", ""),
			"category": "MktNews"
		}
		
		# Usar el motor unificado
		result = integration.process_news_item(news_item)
		
		if not result.get("success"):
			print(f"    -> ⚠️ Item no procesado: {result.get('reason', 'Error desconocido')}")
	
	print("✅ Ingesta completada con motor unificado de Quantex")


if __name__ == '__main__':
	ingest_latest_md()



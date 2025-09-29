import math
from datetime import datetime, timezone

import hashlib
from llm_destiller import distill_and_classify_text
from graph_client import insert_document_node, upsert_entity_nodes, insert_edges_menciona, node_exists_by_hash


def _compute_item_hash(title: str, time_text: str | None, precomputed: str | None = None) -> str:
	# Prefer precomputed stable hash if provided by source
	if precomputed:
		return precomputed
	key = (title or '').strip().lower() + '|' + (time_text or '')
	return hashlib.sha256(key.encode('utf-8')).hexdigest()


def process_and_store_knowledge(raw_text: str, source_context: dict):
	"""Replicates Quantex assembly line: LLM destillation -> nodes -> entities/edges."""
	atomic_nodes = distill_and_classify_text(raw_text)
	if not atomic_nodes:
		print("  -> 🔴 Destilador no devolvió nodos.", flush=True)
		return

	total = len(atomic_nodes)
	created_count = 0
	skipped_dupes = 0
	print(f"  -> 💾 Guardando {total} nodo(s) al grafo...", flush=True)
	for idx, node_obj in enumerate(atomic_nodes, start=1):
		node_content = node_obj.get('content')
		if not node_content:
			print(f"    [{idx}/{total}] ⚠️ Nodo vacío, saltando.", flush=True)
			continue
		word_count = len(node_content.split())
		reading_time_minutes = math.ceil(word_count / 200)
		title_for_hash = node_obj.get('title') or ''
		item_hash = _compute_item_hash(title_for_hash, source_context.get('time_text'), source_context.get('item_hash'))
		if node_exists_by_hash(item_hash):
			print(f"    [{idx}/{total}] ⏭️ Duplicado por hash {item_hash[:8]}… Saltando.", flush=True)
			skipped_dupes += 1
			continue

		properties = {
			"source": source_context.get('source','MktNews'),
			"source_type": source_context.get('source_type','financial_news'),
			"topic": source_context.get('topic','market_news'),
			"original_url": source_context.get('original_url','https://mktnews.net/index.html'),
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"hash": item_hash,
			"time_text": source_context.get('time_text'),
			"ai_summary": node_obj.get('ai_summary'),
			"categories": node_obj.get('categories'),
			"word_count": word_count,
			"reading_time_minutes": reading_time_minutes,
		}
		document_title = node_obj.get('title') or f"Artículo de {properties['source']}"
		doc_id = insert_document_node(node_content, document_title, properties)
		created_count += 1
		entities = node_obj.get('key_entities') or []
		entity_map = upsert_entity_nodes(entities)
		insert_edges_menciona(doc_id, entity_map)
		print(f"    [{idx}/{total}] ✅ Creado doc {doc_id[:8]} con {len(entities)} entidad(es).", flush=True)

	print(f"  -> 📊 Resumen ingesta: nuevos={created_count}, duplicados={skipped_dupes}, total={total}.", flush=True)



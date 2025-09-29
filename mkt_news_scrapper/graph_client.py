import os
import uuid
from datetime import datetime, timezone

from env_loader import load_env_with_fallback

load_env_with_fallback()

try:
	from supabase import create_client
except Exception as e:
	raise RuntimeError("Supabase client not installed. Add 'supabase' to requirements.txt")


SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def node_exists_by_original_url(original_url: str) -> bool:
	if not original_url:
		return False
	res = supabase.table('nodes') \
		.select('id', count='exact') \
		.eq('type', 'Documento') \
		.eq('properties->>original_url', original_url.strip()) \
		.execute()
	return (res.count or 0) > 0


def node_exists_by_hash(item_hash: str) -> bool:
	"""Check if a Documento with the same logical hash already exists."""
	if not item_hash:
		return False
	res = supabase.table('nodes') \
		.select('id', count='exact') \
		.eq('type', 'Documento') \
		.eq('properties->>hash', item_hash) \
		.execute()
	return (res.count or 0) > 0


def upsert_entity_nodes(entity_labels: list[str]) -> dict[str, str]:
	if not entity_labels:
		return {}
	# Upsert by (label,type)
	supabase.table('nodes').upsert(
		[{"type": "Entidad", "label": label} for label in entity_labels], on_conflict='label,type'
	).execute()
	rows = supabase.table('nodes').select('id,label').eq('type','Entidad').in_('label', entity_labels).execute().data
	return {row['label']: row['id'] for row in rows}


def insert_document_node(node_content: str, document_title: str, properties: dict) -> str:
	document_id = str(uuid.uuid4())
	document_label = f"{document_title} - {document_id[:8]}"
	props = dict(properties or {})
	props.setdefault('timestamp', datetime.now(timezone.utc).isoformat())

	supabase.table('nodes').insert({
		"id": document_id,
		"type": "Documento",
		"label": document_label,
		"content": node_content,
		"properties": props
	}).execute()
	return document_id


def insert_edges_menciona(source_document_id: str, entity_map: dict[str,str]):
	if not entity_map:
		return
	edges = [{
		"source_id": source_document_id,
		"target_id": eid,
		"relationship_type": "menciona"
	} for eid in entity_map.values()]
	if edges:
		supabase.table('edges').upsert(edges).execute()



import os
import json
import re
from env_loader import load_env_with_fallback

load_env_with_fallback()

DESTILLER_PROMPT = """
Tu rol es actuar como un analista de inteligencia experto. Lee el texto fuente y destílalo en nodos atómicos.
Reglas:
- Cada nodo debe ser una idea única y textual del texto.
- Genera un title corto, ai_summary (1-2 frases), doc_type, categories (lista), key_entities (lista).

Texto fuente:
---
{source_data}
---

Devuelve SOLO JSON:
{
  "classified_nodes": [
    {"title":"...","content":"...","ai_summary":"...","doc_type":"...","categories":["..."],"key_entities":["..."]}
  ]
}
"""


def distill_and_classify_text(raw_text: str) -> list:
	"""Produce nodos estructurados usando Anthropic Claude 3 Haiku."""
	try:
		import anthropic
	except Exception:
		return []

	api_key = os.getenv('ANTHROPIC_API_KEY')
	if not api_key:
		return []

	client = anthropic.Anthropic(api_key=api_key)
	system_prompt = DESTILLER_PROMPT.replace('{source_data}', raw_text)
	try:
		msg = client.messages.create(
			model=os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
			max_tokens=2000,
			temperature=0.2,
			system=system_prompt,
			messages=[{"role": "user", "content": "Devuelve exclusivamente el JSON solicitado."}]
		)
		text = ''.join([b.text for b in msg.content if getattr(b, 'type', '') == 'text']) if hasattr(msg, 'content') else str(msg)
		match = re.search(r"\{[\s\S]*\}$", text.strip())
		data = json.loads(match.group(0)) if match else json.loads(text)
		return data.get('classified_nodes', [])
	except Exception:
		return []



from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


NEWS_TERMS = {
    "keywords": ["noticia", "noticias", "titular", "headline", "última", "hoy", "reciente", "breaking"],
}


@dataclass
class GraphPlan:
    action: str  # "query" | "synthesis"
    filters: dict
    top_k: int = 20


def _infer_since(user_lower: str) -> str | None:
    now = datetime.now(timezone.utc)
    if "hoy" in user_lower or "hoy día" in user_lower or "hoy dia" in user_lower or "últimas 24" in user_lower:
        return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if "últimas 48" in user_lower or "ultimas 48" in user_lower:
        return (now - timedelta(days=2)).isoformat()
    if "últimos 7" in user_lower or "ultimos 7" in user_lower:
        return (now - timedelta(days=7)).isoformat()
    return None


def plan_graph_query(user_message: str) -> GraphPlan:
    """Deriva filtros/top_k y la acción para consultas del grafo.
    Simple heuristic planner: detecta 'noticias recientes' y ajusta filtros.
    """
    user_lower = (user_message or "").lower()

    # Default plan: búsqueda general
    default = GraphPlan(action="query", filters={}, top_k=8)

    # Modo noticias recientes
    if any(t in user_lower for t in NEWS_TERMS["keywords"]):
        since_iso = _infer_since(user_lower) or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return GraphPlan(
            action="query",
            filters={
                "source": "MktNews",
                "node_type": "Documento",
                "since": since_iso,
            },
            top_k=20,
        )

    # Solicitudes explícitas de síntesis
    if any(t in user_lower for t in ["síntesis", "sintesis", "analiza", "analizar", "resumen inteligente"]):
        # Nota: la acción la consumirá el handler correspondiente
        return GraphPlan(action="synthesis", filters={}, top_k=20)

    return default







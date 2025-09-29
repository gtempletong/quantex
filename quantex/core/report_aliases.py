import re

# Mapa de aliases legibles a keywords canónicos en DB
ALIAS_MAP = {
    # Comité Técnico CLP (aliases explícitos)
    "comite_tecnico_clp": "comite_tecnico_clp",
    "comite tecnico clp": "comite_tecnico_clp",
    "comite-tecnico-clp": "comite_tecnico_clp",

    # Comité Técnico Cobre (aliases explícitos)
    "comite_tecnico_cobre": "comite_tecnico_cobre",
    "comite tecnico cobre": "comite_tecnico_cobre",
    "comite-tecnico-cobre": "comite_tecnico_cobre",
}


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    # Reemplaza cualquier secuencia no alfanumérica por un solo underscore
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def resolve_report_keyword(raw_keyword: str | None) -> str | None:
    """
    Devuelve el keyword canónico dado un alias humano.
    - Primero normaliza (lower, separadores a underscore)
    - Luego consulta ALIAS_MAP
    - Si no hay match, retorna el normalizado
    """
    if raw_keyword is None:
        return None
    normalized = _normalize(raw_keyword)

    # Solo resolvemos a keywords del Comité Técnico si el alias contiene la palabra 'comite'
    if "comite" in normalized:
        return ALIAS_MAP.get(normalized, normalized)

    # Si no contiene 'comite', no forzamos resolución para evitar confusión con otros informes
    return normalized



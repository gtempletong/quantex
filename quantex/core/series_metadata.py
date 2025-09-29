#!/usr/bin/env python3
"""
Gestor de metadatos para series BCCH específicas.
Lee la configuración desde sync_bcentral.py como fuente de la verdad.
"""

def get_bcch_series_metadata(ticker: str) -> dict | None:
    """
    Obtiene metadatos para series BCCH desde la configuración de sync_bcentral.py.
    Lee directamente la configuración como fuente de la verdad.
    """
    try:
        # Importar directamente la configuración desde sync_bcentral.py
        from quantex.pipelines.price_ingestor.sync_bcentral import get_bcentral_series_config
        
        # Obtener la configuración completa
        bcentral_series = get_bcentral_series_config()
        
        # Buscar el ticker en la configuración
        for serie_id, config in bcentral_series.items():
            if config['ticker'] == ticker:
                return {
                    'context_for_ai': config['context_for_ai'],
                    'display_name': config['display_name'],
                    'description': config['description']
                }
        
        return None
        
    except Exception as e:
        print(f"   -> ⚠️ Error obteniendo metadatos BCCH para {ticker}: {e}")
        return None

def enrich_series_with_metadata(ticker: str, data: list) -> dict:
    """
    Enriquece datos de serie con metadatos si es una serie BCCH.
    
    Args:
        ticker: Identificador de la serie
        data: Lista de registros de datos
        
    Returns:
        dict: Datos enriquecidos con metadatos (si aplica)
    """
    result = {
        'ticker': ticker,
        'data': data
    }
    
    # Enriquecer si es una serie BCCH con metadatos
    metadata = get_bcch_series_metadata(ticker)
    if metadata:
        result.update(metadata)
        print(f"  -> ✅ Metadatos BCCH encontrados para {ticker}: {metadata['display_name']}")
    
    return result


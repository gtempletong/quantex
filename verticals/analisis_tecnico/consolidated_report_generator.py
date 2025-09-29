# quantex/verticals/analisis_tecnico/consolidated_report_generator.py

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from flask import jsonify

# --- Importaciones de Servicios Centrales ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db

def get_today_committee_artifacts(report_keyword: str = "comite_tecnico_mercado") -> list:
    """
    Obtiene el ÚLTIMO artifact por ticker del comité técnico de hoy.
    """
    print(f"🔍 [Consolidado] Buscando ÚLTIMO artifact por ticker para '{report_keyword}'...")
    
    try:
        # Calcular fecha de hoy y ayer en UTC (incluir datos de ayer para fines de semana)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        search_start = datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=timezone.utc)
        search_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Buscar TODOS los artifacts de hoy y ayer
        response = db.supabase.table('generated_artifacts').select('*').eq('report_keyword', report_keyword).eq('artifact_type', f'report_{report_keyword}_final').gte('created_at', search_start.isoformat()).lte('created_at', search_end.isoformat()).order('created_at', desc=True).execute()
        
        if not response.data:
            print(f"  -> ⚠️ No se encontraron artifacts de hoy/ayer para '{report_keyword}'")
            return []
        
        # Filtrar para obtener solo el ÚLTIMO artifact por ticker
        latest_by_ticker = {}
        for artifact in response.data:
            ticker = artifact.get('ticker')
            if ticker and ticker not in latest_by_ticker:
                latest_by_ticker[ticker] = artifact
        
        filtered_artifacts = list(latest_by_ticker.values())
        print(f"  -> ✅ Encontrados {len(filtered_artifacts)} artifacts únicos por ticker")
        return filtered_artifacts
            
    except Exception as e:
        print(f"  -> ❌ Error obteniendo artifacts de hoy: {e}")
        return []

def _get_instrument_name(ticker: str) -> str:
    """
    Obtiene el instrument_name desde instrument_definitions usando el ticker.
    """
    try:
        from quantex.core import database_manager as db
        
        response = db.supabase.table('instrument_definitions').select('instrument_name').eq('ticker', ticker).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0].get('instrument_name', ticker)
        else:
            print(f"  -> ⚠️ No se encontró instrument_name para {ticker}, usando ticker")
            return ticker
            
    except Exception as e:
        print(f"  -> ⚠️ Error obteniendo instrument_name para {ticker}: {e}")
        return ticker

def extract_committee_data(artifacts: list) -> list:
    """
    Extrae los datos del comité (Chartista, Quant, CIO) de cada artifact.
    """
    print(f"📊 [Consolidado] Extrayendo datos del comité de {len(artifacts)} artifacts...")
    
    committee_data = []
    
    for artifact in artifacts:
        try:
            ticker = artifact.get('ticker', 'N/A')
            content_dossier = artifact.get('content_dossier', {})
            
            if not content_dossier:
                print(f"  -> ⚠️ No hay content_dossier para {ticker}")
                continue
            
            # Obtener instrument_name desde instrument_definitions
            instrument_name = _get_instrument_name(ticker)
            
            # Extraer datos del comité
            chartista_data = content_dossier.get('analisis_chartista', {})
            quant_data = content_dossier.get('analisis_quant', {})
            cio_data = {
                'recomendacion_final': content_dossier.get('recomendacion_final', 'N/A'),
                'confianza_final': content_dossier.get('confianza_final', 'N/A'),
                'resumen_cio': content_dossier.get('resumen_cio', 'N/A'),
                'niveles_operativos': content_dossier.get('niveles_operativos', {})
            }
            
            # Extraer convicción (asumiendo que está en el análisis del CIO)
            conviccion = _extract_conviction_level(cio_data)
            
            committee_data.append({
                'ticker': ticker,
                'instrument_name': instrument_name,
                'chartista': {
                    'situacion_actual': chartista_data.get('situacion_actual', 'N/A'),
                    'patrones_y_niveles': chartista_data.get('patrones_y_niveles', 'N/A'),
                    'puntos_de_inflexion': chartista_data.get('puntos_de_inflexion', 'N/A'),
                    'sintesis_y_perspectiva': chartista_data.get('sintesis_y_perspectiva', 'N/A')
                },
                'quant': {
                    'analisis_momento': quant_data.get('analisis_momento', 'N/A'),
                    'analisis_tendencia': quant_data.get('analisis_tendencia', 'N/A'),
                    'senal_tecnica_final': quant_data.get('senal_tecnica_final', 'N/A'),
                    'confianza': quant_data.get('confianza', 'N/A'),
                    'sintesis_cuantitativa': quant_data.get('sintesis_cuantitativa', 'N/A')
                },
                'cio': cio_data,
                'conviccion': conviccion
            })
            
            print(f"  -> ✅ Datos extraídos para {ticker}")
            
        except Exception as e:
            print(f"  -> ❌ Error extrayendo datos para {artifact.get('ticker', 'N/A')}: {e}")
            continue
    
    # Ordenar con IPSA primero
    committee_data = _sort_with_ipsa_first(committee_data)
    
    return committee_data

def _calculate_trend_strength(committee_data: list) -> float:
    """
    Calcula el Indicador de Fuerza de Tendencia (IFT) usando lógica de casos.
    Escala 1-10: 1=Super bajista, 5=Neutral, 10=Super alcista
    """
    if not committee_data:
        return 5.0  # Neutral por defecto
    
    scores = []
    
    for ticker in committee_data:
        recomendacion = ticker['cio'].get('recomendacion_final', 'NEUTRAL')
        conviccion = ticker['conviccion']
        
        # DEBUG: Ver qué valores está recibiendo
        print(f"  -> 🔍 [DEBUG] Ticker: {ticker.get('ticker', 'N/A')}")
        print(f"  -> 🔍 [DEBUG] Recomendación: '{recomendacion}'")
        print(f"  -> 🔍 [DEBUG] Convicción: {conviccion}")
        
        # Lógica de casos
        if recomendacion in ['ALCISTA', 'COMPRAR', 'BUY']:
            score = conviccion
            print(f"  -> 🔍 [DEBUG] ALCISTA/COMPRAR → Score: {score}")
            scores.append(score)  # 1-10
        elif recomendacion in ['NEUTRAL', 'MANTENER', 'HOLD']:
            score = 5
            print(f"  -> 🔍 [DEBUG] NEUTRAL → Score: {score}")
            scores.append(score)  # Siempre 5
        elif recomendacion in ['BAJISTA', 'VENDER', 'SELL']:
            score = 10 - conviccion
            print(f"  -> 🔍 [DEBUG] BAJISTA/VENDER → Score: {score} (10 - {conviccion})")
            scores.append(score)  # Invertir escala (1-10)
        else:
            score = 5
            print(f"  -> 🔍 [DEBUG] FALLBACK → Score: {score}")
            scores.append(score)  # Fallback neutral
    
    # Promedio simple
    trend_strength = sum(scores) / len(scores)
    print(f"  -> 🔍 [DEBUG] Scores finales: {scores}")
    print(f"  -> 🔍 [DEBUG] Promedio: {trend_strength}")
    return round(trend_strength, 1)

def _get_trend_strength_label(trend_strength: float) -> str:
    """
    Convierte el score numérico en etiqueta descriptiva.
    """
    if trend_strength >= 8.5:
        return "SUPER ALCISTA"
    elif trend_strength >= 7.0:
        return "ALCISTA FUERTE"
    elif trend_strength >= 5.5:
        return "ALCISTA MODERADO"
    elif trend_strength >= 4.5:
        return "NEUTRAL"
    elif trend_strength >= 3.0:
        return "BAJISTA MODERADO"
    elif trend_strength >= 1.5:
        return "BAJISTA FUERTE"
    else:
        return "SUPER BAJISTA"

def _get_needle_rotation(trend_strength: float) -> float:
    """
    Calcula la rotación de la aguja del speedometer.
    Escala 1-10 mapeada a -90° (izquierda) a +90° (derecha).
    """
    print(f"  -> 🔍 [Debug] IFT recibido: {trend_strength}")
    
    # Mapeo por tramos para asegurar puntos exactos:
    # 1 → -90°, 5 → 0°, 10 → +90°
    if trend_strength <= 5:
        # [1..5] → [-90..0]  (4 pasos → 90° ⇒ 22.5° por punto)
        rotation = -90 + (trend_strength - 1) * (90 / 4)
    else:
        # [5..10] → [0..+90] (5 pasos → 90° ⇒ 18° por punto)
        rotation = 0 + (trend_strength - 5) * (90 / 5)

    print(f"  -> 🎯 [Debug] IFT: {trend_strength} → Rotación FINAL: {rotation}°")
    return round(rotation, 1)

def _get_trend_strength_color(trend_strength: float) -> str:
    """
    Obtiene el color CSS basado en el score.
    """
    if trend_strength >= 7.0:
        return "#00C851"  # Verde fuerte
    elif trend_strength >= 5.5:
        return "#8BC34A"  # Verde moderado
    elif trend_strength >= 4.5:
        return "#FFC107"  # Amarillo
    elif trend_strength >= 3.0:
        return "#FF9800"  # Naranja
    else:
        return "#F44336"  # Rojo

def _sort_with_ipsa_first(committee_data: list) -> list:
    """
    Ordena los datos del comité con IPSA primero.
    """
    def sort_key(data):
        ticker = data.get('ticker', '')
        if 'IPSA' in ticker.upper() or 'SPIPSA' in ticker.upper():
            return (0, ticker)  # IPSA primero
        else:
            return (1, ticker)  # Resto después
    
    return sorted(committee_data, key=sort_key)

def _get_previous_session_data(report_keyword: str) -> dict:
    """
    Obtiene los datos de la sesión anterior para comparar cambios.
    """
    try:
        from quantex.core import database_manager as db
        from datetime import datetime, timezone, timedelta
        
        # Buscar artifacts de ayer (o último día hábil)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        # Buscar artifacts de ayer
        response = db.supabase.table('generated_artifacts').select('*').eq('report_keyword', report_keyword).eq('artifact_type', f'report_{report_keyword}_final').gte('created_at', yesterday.isoformat()).lt('created_at', today.isoformat()).order('created_at', desc=True).execute()
        
        if not response.data:
            print(f"  -> ⚠️ No se encontraron datos de ayer para comparar")
            return {}
        
        # Filtrar para obtener solo el último artifact por ticker de ayer
        previous_data = {}
        for artifact in response.data:
            ticker = artifact.get('ticker')
            if ticker and ticker not in previous_data:
                content_dossier = artifact.get('content_dossier', {})
                previous_data[ticker] = {
                    'recomendacion_final': content_dossier.get('recomendacion_final', 'N/A'),
                    'confianza_final': content_dossier.get('confianza_final', 'N/A'),
                    'conviccion': _extract_conviction_level({
                        'confianza_final': content_dossier.get('confianza_final', 'N/A')
                    })
                }
        
        print(f"  -> ✅ Datos de sesión anterior obtenidos para {len(previous_data)} tickers")
        return previous_data
        
    except Exception as e:
        print(f"  -> ❌ Error obteniendo datos de sesión anterior: {e}")
        return {}

def _detect_changes(current_data: list, previous_data: dict) -> tuple:
    """
    Detecta cambios entre la sesión actual y la anterior.
    Retorna: (cambios_tendencia, cambios_conviccion)
    """
    cambios_tendencia = []
    cambios_conviccion = []
    
    for data in current_data:
        ticker = data['ticker']
        instrument_name = data['instrument_name']
        
        # Obtener datos actuales
        recomendacion_actual = data['cio'].get('recomendacion_final', 'N/A')
        conviccion_actual = data['conviccion']
        
        # Obtener datos anteriores
        if ticker in previous_data:
            recomendacion_anterior = previous_data[ticker]['recomendacion_final']
            conviccion_anterior = previous_data[ticker]['conviccion']
            
            # Detectar cambio de tendencia
            if recomendacion_actual != recomendacion_anterior:
                cambio_tendencia = f"<li class='change-tendencia'>{instrument_name}: {recomendacion_anterior} → {recomendacion_actual}</li>"
                cambios_tendencia.append(cambio_tendencia)
            
            # Detectar cambio de convicción (diferencia >= 2 puntos)
            if abs(conviccion_actual - conviccion_anterior) >= 2:
                cambio_conviccion = f"<li class='change-conviccion'>{instrument_name}: {conviccion_anterior}/10 → {conviccion_actual}/10</li>"
                cambios_conviccion.append(cambio_conviccion)
    
    # Si no hay cambios, mostrar mensaje
    if not cambios_tendencia:
        cambios_tendencia = ["<li class='change-tendencia'>No hay cambios de tendencia</li>"]
    
    if not cambios_conviccion:
        cambios_conviccion = ["<li class='change-conviccion'>No hay cambios de convicción</li>"]
    
    return cambios_tendencia, cambios_conviccion

def _extract_conviction_level(cio_data: dict) -> int:
    """
    Extrae el nivel de convicción del CIO (1-10).
    """
    try:
        confianza = cio_data.get('confianza_final', '').lower()
        
        # DEBUG: Ver qué valor está recibiendo
        print(f"  -> 🔍 [DEBUG] confianza_final recibido: '{cio_data.get('confianza_final', 'N/A')}'")
        print(f"  -> 🔍 [DEBUG] confianza procesado: '{confianza}'")
        
        # Primero intentar extraer número de formato "9/10" o "9"
        import re
        number_match = re.search(r'(\d+)(?:/\d+)?', confianza)
        if number_match:
            number = int(number_match.group(1))
            if 1 <= number <= 10:
                print(f"  -> 🔍 [DEBUG] Número extraído: {number}")
                return number
        
        # Si no hay número, usar mapeo de palabras
        if 'alta' in confianza or 'high' in confianza:
            print(f"  -> 🔍 [DEBUG] Usando mapeo 'alta': 9")
            return 9
        elif 'media' in confianza or 'medium' in confianza:
            print(f"  -> 🔍 [DEBUG] Usando mapeo 'media': 6")
            return 6
        elif 'baja' in confianza or 'low' in confianza:
            print(f"  -> 🔍 [DEBUG] Usando mapeo 'baja': 3")
            return 3
        else:
            print(f"  -> 🔍 [DEBUG] Usando valor por defecto: 5")
            return 5  # Default medio
            
    except Exception as e:
        print(f"  -> 🔍 [DEBUG] Error en _extract_conviction_level: {e}")
        return 5

def generate_consolidated_html(committee_data: list, report_keyword: str = "comite_tecnico_mercado") -> str:
    """
    Genera el HTML consolidado usando el template horizontal optimizado para PDF.
    """
    print(f"🎨 [Consolidado] Generando HTML consolidado para {len(committee_data)} tickers...")
    
    # Calcular métricas del mercado
    market_metrics = _calculate_market_metrics(committee_data)
    
    # Generar panorama general del mercado
    panorama_general = _generate_market_overview(committee_data, market_metrics)
    
    # Generar tabla del comité
    tabla_comite = _generate_committee_table(committee_data)
    
    # Obtener datos de sesión anterior para Monitor de Cambio
    previous_data = _get_previous_session_data(report_keyword)
    cambios_tendencia, cambios_conviccion = _detect_changes(committee_data, previous_data)
    
    # Generar análisis detallado por ticker
    analisis_detallado = ""  # Sección eliminada
    
    # Leer el template horizontal
    template_path = os.path.join(os.path.dirname(__file__), 'template_consolidated_horizontal.html')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Reemplazar placeholders
        html = template.replace('{{ fecha_actual }}', datetime.now().strftime('%Y-%m-%d %H:%M'))
        html = html.replace('{{ panorama_general }}', panorama_general)
        html = html.replace('{{ tabla_comite }}', tabla_comite)
        html = html.replace('{{ sentiment_score }}', market_metrics['sentiment_score'])
        html = html.replace('{{ total_tickers }}', str(market_metrics['total_tickers']))
        html = html.replace('{{ trend_strength }}', str(market_metrics['trend_strength']))
        html = html.replace('{{ trend_label }}', market_metrics['trend_label'])
        html = html.replace('{{ trend_color }}', market_metrics['trend_color'])
        html = html.replace('{{ needle_rotation }}', str(market_metrics['needle_rotation']))
        html = html.replace('{{ cambios_tendencia }}', '\n'.join(cambios_tendencia))
        html = html.replace('{{ cambios_conviccion }}', '\n'.join(cambios_conviccion))
        html = html.replace('{{ analisis_detallado }}', analisis_detallado)
        
        return html
        
    except Exception as e:
        print(f"❌ [Consolidado] Error leyendo template: {e}")
        # Fallback al template anterior si hay error
        return _generate_fallback_html(committee_data, market_metrics)

def _generate_market_overview(committee_data: list, market_metrics: dict) -> str:
    """
    Genera el panorama general del mercado basado en los análisis del comité.
    """
    if not committee_data:
        return "No hay datos disponibles para generar el panorama del mercado."
    
    # Analizar tendencias generales
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    high_conviction_count = 0
    
    for data in committee_data:
        cio_rec = data['cio']['recomendacion_final'].upper()
        conviction = data['conviccion']
        
        if conviction >= 7:
            high_conviction_count += 1
            
        if any(word in cio_rec for word in ['COMPRAR', 'BUY', 'ALCISTA']):
            bullish_count += 1
        elif any(word in cio_rec for word in ['VENDER', 'SELL', 'BAJISTA']):
            bearish_count += 1
        else:
            neutral_count += 1
    
    # Generar panorama basado en los datos
    total_tickers = len(committee_data)
    bullish_pct = (bullish_count / total_tickers) * 100
    bearish_pct = (bearish_count / total_tickers) * 100
    
    if bullish_pct > 60:
        sentiment = "ALCISTA"
        color = "positivo"
    elif bearish_pct > 60:
        sentiment = "BAJISTA"
        color = "negativo"
    else:
        sentiment = "NEUTRAL"
        color = "cauteloso"
    
    panorama = f"""
    El mercado presenta un sesgo {sentiment.lower()} con {bullish_count} señales alcistas ({bullish_pct:.1f}%) 
    y {bearish_count} señales bajistas ({bearish_pct:.1f}%) de un total de {total_tickers} tickers analizados. 
    Se identifican {high_conviction_count} señales de alta convicción (≥7/10), indicando oportunidades 
    de trading con mayor probabilidad de éxito. La distribución sugiere un mercado {color} 
    con oportunidades selectivas en ambos sentidos.
    """.strip()
    
    return panorama

def _generate_committee_table(committee_data: list) -> str:
    """
    Genera la tabla principal del comité con resúmenes de máximo 20 palabras.
    """
    table_rows = ""
    
    for data in committee_data:
        ticker = data['ticker']
        instrument_name = data['instrument_name']
        conviccion = data['conviccion']
        
        # Determinar clase de convicción
        if conviccion >= 8:
            conv_class = "conviction-high"
        elif conviccion >= 5:
            conv_class = "conviction-medium"
        else:
            conv_class = "conviction-low"
        
        # Obtener recomendación final del CIO
        recomendacion_final = data['cio'].get('recomendacion_final', 'N/A')
        
        # Generar resúmenes de máximo 30 palabras usando IA
        # print(f"  -> 🕵️ ESPÍA Texto Chartista original: '{data['chartista']['sintesis_y_perspectiva'][:100]}...'")
        # print(f"  -> 🕵️ ESPÍA Texto Quant original: '{data['quant']['sintesis_cuantitativa'][:100]}...'")
        # print(f"  -> 🕵️ ESPÍA Texto CIO original: '{data['cio']['resumen_cio'][:100]}...'")
        
        chartista_resumen = _summarize_with_ai(data['chartista']['sintesis_y_perspectiva'], 30)
        quant_resumen = _summarize_with_ai(data['quant']['sintesis_cuantitativa'], 30)
        cio_resumen = _summarize_with_ai(data['cio']['resumen_cio'], 30)
        
        # Convertir recomendación a términos regulatorios
        recomendacion_regulatoria = _convert_to_regulatory_terms(recomendacion_final)
        
        table_rows += f"""
                        <tr>
                            <td class="ticker-cell">{instrument_name}</td>
                            <td class="analysis-cell">{chartista_resumen}</td>
                            <td class="analysis-cell">{quant_resumen}</td>
                            <td class="analysis-cell">{cio_resumen}</td>
                            <td class="conviction-cell {conv_class}">{conviccion}/10</td>
                            <td class="analysis-cell" style="font-size: 11px;">{recomendacion_regulatoria}</td>
                        </tr>
        """
    
    return table_rows

def _smart_cut_summary(text: str, max_words: int) -> str:
    """
    Corta el texto de manera inteligente buscando puntos, comas o punto y coma.
    """
    words = text.split()
    
    if len(words) <= max_words:
        return text
    
    # Buscar puntos (.) primero
    sentences = text.split('. ')
    current_length = 0
    result_sentences = []
    
    for sentence in sentences:
        sentence_words = sentence.split()
        if current_length + len(sentence_words) <= max_words:
            result_sentences.append(sentence)
            current_length += len(sentence_words)
        else:
            break
    
    if result_sentences:
        result = '. '.join(result_sentences)
        if not result.endswith('.'):
            result += '.'
        return result
    
    # Si no hay puntos, buscar comas (,)
    phrases = text.split(', ')
    current_length = 0
    result_phrases = []
    
    for phrase in phrases:
        phrase_words = phrase.split()
        if current_length + len(phrase_words) <= max_words:
            result_phrases.append(phrase)
            current_length += len(phrase_words)
        else:
            break
    
    if result_phrases:
        result = ', '.join(result_phrases)
        return result
    
    # Si no hay comas, buscar punto y coma (;)
    clauses = text.split('; ')
    current_length = 0
    result_clauses = []
    
    for clause in clauses:
        clause_words = clause.split()
        if current_length + len(clause_words) <= max_words:
            result_clauses.append(clause)
            current_length += len(clause_words)
        else:
            break
    
    if result_clauses:
        result = '; '.join(result_clauses)
        return result
    
    # Fallback: cortar en palabras si no hay separadores
    return ' '.join(words[:max_words])


def _summarize_with_ai(text: str, max_words: int) -> str:
    """
    Usa IA para resumir el texto a máximo X palabras manteniendo el sentido.
    """
    if not text or text == 'N/A':
        return 'N/A'
    
    try:
        # Importar llm_manager
        from quantex.core import llm_manager
        
        prompt = f"""
        Resume el siguiente análisis técnico en entre {max_words-5} y {max_words+5} palabras completas.
        
        REGLAS:
        - Usa entre {max_words-5} y {max_words+5} palabras
        - NO uses puntos suspensivos (...)
        - Completa cada frase con sentido
        - Mantén el contexto técnico clave
        - Prioriza la coherencia sobre el conteo exacto
        
        Texto original:
        {text}
        
        Resumen coherente de {max_words-5} a {max_words+5} palabras:
        """
        
        response = llm_manager.generate_completion(
            task_complexity='simple',
            system_prompt="Eres un experto en análisis técnico. Resume de manera concisa y precisa, manteniendo el contexto clave. Usa entre 25-35 palabras. NO uses puntos suspensivos (...). Completa cada frase con sentido. Prioriza la coherencia sobre el conteo exacto.",
            user_prompt=prompt,
            model_preference='haiku'  # Usar Haiku para resúmenes simples y baratos
        )
        
        summary = response.get('raw_text', text)
        
        # ESPÍA: Ver qué está generando Haiku
        # print(f"  -> 🕵️ ESPÍA Haiku: '{summary}'")
        # print(f"  -> 🕵️ ESPÍA Palabras generadas: {len(summary.split())}")
        
        # Verificar que esté en el rango aceptable (25-35 palabras)
        words = summary.split()
        word_count = len(words)
        
        if word_count < max_words-5 or word_count > max_words+5:
            print(f"  -> ⚠️ Haiku generó {word_count} palabras, rango aceptable: {max_words-5}-{max_words+5}. Ajustando...")
            if word_count > max_words+5:
                # Corte inteligente: buscar puntos, comas o punto y coma
                summary = _smart_cut_summary(summary, max_words+5)
                # print(f"  -> 🕵️ ESPÍA Después del corte inteligente: '{summary}'")
            else:
                # Si es muy corto, usar resumen simple
                summary = "Análisis técnico muestra indicadores mixtos y tendencia variable en el activo"
                # print(f"  -> 🕵️ ESPÍA Después del ajuste: '{summary}'")
        else:
            print(f"  -> ✅ Haiku generó {word_count} palabras, dentro del rango aceptable")
        
        # print(f"  -> 🕵️ ESPÍA Final: '{summary}' ({len(summary.split())} palabras)")
        return summary
        
    except Exception as e:
        print(f"  -> ⚠️ Error resumiendo con IA: {e}")
        # Fallback al truncado simple
        return _truncate_to_words(text, max_words)

def _convert_to_regulatory_terms(recomendacion: str) -> str:
    """
    Convierte términos de trading a términos regulatorios.
    """
    if not recomendacion or recomendacion == 'N/A':
        return 'N/A'
    
    recomendacion_upper = recomendacion.upper()
    
    # Mapeo de términos
    if any(word in recomendacion_upper for word in ['COMPRAR', 'BUY', 'ALCISTA', 'BULLISH']):
        return 'ALCISTA'
    elif any(word in recomendacion_upper for word in ['VENDER', 'SELL', 'BAJISTA', 'BEARISH']):
        return 'BAJISTA'
    elif any(word in recomendacion_upper for word in ['NEUTRAL', 'HOLD', 'MANTENER']):
        return 'NEUTRAL'
    else:
        return 'NEUTRAL'  # Default

def _truncate_to_words(text: str, max_words: int) -> str:
    """
    Trunca un texto a un máximo de palabras específicas.
    """
    if not text or text == 'N/A':
        return 'N/A'
    
    words = text.split()
    if len(words) <= max_words:
        return text
    
    truncated = ' '.join(words[:max_words])
    return truncated + '...'

def _generate_top_picks(committee_data: list) -> tuple:
    """
    Genera las listas de top buy y sell picks.
    """
    # Top buy picks (CIO = ALCISTA + alta convicción)
    buy_picks = []
    for data in committee_data:
        cio_rec = data['cio']['recomendacion_final'].upper()
        if any(word in cio_rec for word in ['COMPRAR', 'BUY', 'ALCISTA', 'BULLISH']) and data['conviccion'] >= 7:
            buy_picks.append(data)
    
    # Ordenar por convicción descendente
    buy_picks = sorted(buy_picks, key=lambda x: x['conviccion'], reverse=True)[:3]
    
    buy_html = ""
    for pick in buy_picks:
        buy_html += f'<li class="buy-pick">{pick["ticker"]} - Conv: {pick["conviccion"]}/10</li>\n'
    
    if not buy_html:
        buy_html = '<li style="color: #AAAAAA; font-style: italic;">No hay picks alcistas de alta convicción</li>'
    
    # Top sell picks (CIO = BAJISTA + alta convicción)
    sell_picks = []
    for data in committee_data:
        cio_rec = data['cio']['recomendacion_final'].upper()
        if any(word in cio_rec for word in ['VENDER', 'SELL', 'BAJISTA', 'BEARISH']) and data['conviccion'] >= 7:
            sell_picks.append(data)
    
    # Ordenar por convicción descendente
    sell_picks = sorted(sell_picks, key=lambda x: x['conviccion'], reverse=True)[:2]
    
    sell_html = ""
    for pick in sell_picks:
        sell_html += f'<li class="sell-pick">{pick["ticker"]} - Conv: {pick["conviccion"]}/10</li>\n'
    
    if not sell_html:
        sell_html = '<li style="color: #AAAAAA; font-style: italic;">No hay picks bajistas de alta convicción</li>'
    
    return buy_html, sell_html

def _generate_detailed_analysis(committee_data: list) -> str:
    """
    Genera el análisis detallado por ticker con comentarios completos.
    """
    detailed_html = ""
    
    for data in committee_data:
        ticker = data['ticker']
        
        detailed_html += f"""
                <div class="ticker-analysis">
                    <h3>📊 {ticker} - Análisis Completo</h3>
                    <div class="analysis-grid">
                        <div class="analysis-box">
                            <h4>🎯 Chartista</h4>
                            <p><strong>Situación:</strong> {data['chartista']['situacion_actual']}</p>
                            <p><strong>Patrones:</strong> {data['chartista']['patrones_y_niveles']}</p>
                            <p><strong>Perspectiva:</strong> {data['chartista']['sintesis_y_perspectiva']}</p>
                        </div>
                        <div class="analysis-box">
                            <h4>📈 Quant</h4>
                            <p><strong>Momento:</strong> {data['quant']['analisis_momento']}</p>
                            <p><strong>Tendencia:</strong> {data['quant']['analisis_tendencia']}</p>
                            <p><strong>Señal:</strong> {data['quant']['senal_tecnica_final']}</p>
                        </div>
                        <div class="analysis-box">
                            <h4>🎖️ CIO</h4>
                            <p><strong>Recomendación:</strong> {data['cio']['recomendacion_final']}</p>
                            <p><strong>Convicción:</strong> {data['conviccion']}/10</p>
                            <p><strong>Resumen:</strong> {data['cio']['resumen_cio']}</p>
                        </div>
                    </div>
                </div>
        """
    
    return detailed_html

def _generate_fallback_html(committee_data: list, market_metrics: dict) -> str:
    """
    Genera HTML de fallback si hay error con el template.
    """
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Comité Técnico Consolidado - Fallback</title>
</head>
<body>
    <h1>Comité Técnico Consolidado</h1>
    <p>Error cargando template. Datos disponibles: {len(committee_data)} tickers</p>
    <p>Sentiment: {market_metrics.get('sentiment_score', 'N/A')}</p>
</body>
</html>
    """

def _calculate_market_metrics(committee_data: list) -> dict:
    """
    Calcula métricas del mercado basadas en los datos del comité.
    """
    if not committee_data:
        return {
            'total_tickers': 0,
            'avg_conviction': 0,
            'sentiment_score': 'N/A',
            'trend_strength': 5.0,
            'trend_label': 'NEUTRAL',
            'trend_color': '#FFC107',
            'needle_rotation': 90.0
        }
    
    total_tickers = len(committee_data)
    avg_conviction = sum(data['conviccion'] for data in committee_data) / total_tickers
    
    # Calcular Indicador de Fuerza de Tendencia (IFT)
    trend_strength = _calculate_trend_strength(committee_data)
    trend_label = _get_trend_strength_label(trend_strength)
    trend_color = _get_trend_strength_color(trend_strength)
    needle_rotation = _get_needle_rotation(trend_strength)
    
    # Calcular sentiment score basado en CIO + convicción
    bullish_count = 0
    bearish_count = 0
    
    for data in committee_data:
        cio_recommendation = data['cio']['recomendacion_final'].upper()
        conviction = data['conviccion']
        
        # Lógica mejorada: CIO + convicción alta = más peso
        if any(word in cio_recommendation for word in ['COMPRAR', 'BUY', 'ALCISTA', 'BULLISH']) and conviction >= 7:
            bullish_count += 2  # Doble peso si CIO + alta convicción
        elif any(word in cio_recommendation for word in ['COMPRAR', 'BUY', 'ALCISTA', 'BULLISH']):
            bullish_count += 1
        elif any(word in cio_recommendation for word in ['VENDER', 'SELL', 'BAJISTA', 'BEARISH']) and conviction >= 7:
            bearish_count += 2
        elif any(word in cio_recommendation for word in ['VENDER', 'SELL', 'BAJISTA', 'BEARISH']):
            bearish_count += 1
    
    # Determinar sentiment
    if bullish_count > bearish_count:
        sentiment_score = 'BULLISH'
    elif bearish_count > bullish_count:
        sentiment_score = 'BEARISH'
    else:
        sentiment_score = 'NEUTRAL'
    
    return {
        'total_tickers': total_tickers,
        'avg_conviction': round(avg_conviction, 1),
        'sentiment_score': sentiment_score,
        'bullish_signals': bullish_count,
        'bearish_signals': bearish_count,
        'trend_strength': trend_strength,
        'trend_label': trend_label,
        'trend_color': trend_color,
        'needle_rotation': needle_rotation
    }

def generate_consolidated_report(report_keyword: str = "comite_tecnico_mercado") -> dict:
    """
    Función principal para generar el reporte consolidado.
    """
    print(f"🚀 [Consolidado] Iniciando generación del reporte consolidado para '{report_keyword}'...")
    
    try:
        # 1. Obtener artifacts de hoy
        artifacts = get_today_committee_artifacts(report_keyword)
        if not artifacts:
            return {
                "error": f"No se encontraron artifacts de hoy para '{report_keyword}'"
            }
        
        # 2. Extraer datos del comité
        committee_data = extract_committee_data(artifacts)
        if not committee_data:
            return {
                "error": "No se pudieron extraer datos del comité"
            }
        
        # 3. Generar HTML consolidado
        html_report = generate_consolidated_html(committee_data)
        
        # 4. Guardar artifact consolidado
        consolidated_artifact = db.insert_generated_artifact(
            report_keyword=report_keyword,
            artifact_content=html_report,
            artifact_type=f"report_{report_keyword}_consolidated",
            results_packet={
                "consolidated_data": committee_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_tickers": len(committee_data)
            },
            ticker="CONSOLIDATED"
        )
        
        print(f"✅ [Consolidado] Reporte consolidado generado exitosamente")
        
        return {
            "success": True,
            "html_report": html_report,
            "artifact_id": consolidated_artifact.get('id') if consolidated_artifact else None,
            "total_tickers": len(committee_data)
        }
        
    except Exception as e:
        print(f"❌ [Consolidado] Error generando reporte consolidado: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"Error generando reporte consolidado: {e}"
        }

def run_advanced_technical_analysis(tickers: list) -> dict:
    print(f"🛠️  [Herramienta Avanzada] Ejecutando análisis para: {tickers}")
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
    except Exception as e:
        return {"error": f"Error configurando Gemini: {e}"}
        
    eodhd_api_key = os.getenv("EODHD_API_KEY")
    prompt_template = get_file_content("verticals/analisis_tecnico/prompt_technical_analyst.txt") 
    if not prompt_template: return {"error": "No se pudo cargar 'verticals/analisis_tecnico/prompt_technical_analyst.txt'"}
    
    all_results = []
    for ticker in tickers:
        print(f"  -> Analizando {ticker}...")
        df_raw = fetch_stock_data(ticker, eodhd_api_key)
        if df_raw is None:
            all_results.append({"ticker": ticker, "error": "No se pudieron obtener datos."})
            continue
            
        df_indicators = calculate_all_indicators(df_raw)
        
        chart_recipes = [
            {
                "tool_name": "generate_chart",
                "parameters": {
                    "chart_type": "candlestick",
                    "html_title": f"Precio y Medias Móviles para {ticker}"
                }
            },
            # Podríamos añadir más recetas para RSI y MACD si fuera necesario
        ]
        
        chart_images = []
        for recipe in chart_recipes:
            # Creamos un dossier temporal para la herramienta de gráficos
            temp_dossier = {'data_ohlc': df_indicators.to_dict('records')}
            recipe['parameters']['source_series_key'] = 'data_ohlc' # Le decimos dónde encontrar los datos
            
            # Llamamos a nuestra nueva fábrica de gráficos
            chart_result = generate_chart(evidence_workspace=temp_dossier, params=recipe['parameters'])
            
            if chart_result and 'html' in chart_result:
                # Extraemos la URL de la imagen del HTML generado
                match = re.search(r'src="([^"]+)"', chart_result['html'])
                if match:
                    # Aquí obtendríamos los bytes de la imagen para pasarlos a Gemini
                    # (Lógica para descargar la URL y convertir a objeto de imagen iría aquí)
                    pass

        # --- FIN DE LA CORRECCIÓN ---

        prompt_text = prompt_template.replace("{{TICKER}}", ticker).replace("{{ANALYSIS_DATE}}", datetime.now().strftime('%Y-%m-%d'))
        prompt_parts = [prompt_text] # + chart_images si se implementa la descarga
        
        try:
            response = model.generate_content(prompt_parts)
            # ... (el resto de la lógica de procesamiento de respuesta no cambia) ...
            
        except Exception as e:
            all_results.append({"ticker": ticker, "error": f"Error en llamada a Gemini: {e}"})
            
    return {"analysis_results": all_results}


def _handle_technical_analysis(parameters, **kwargs):
    """
    Manejador principal para el flujo de análisis técnico en lote.
    (Versión Robusta con Manejo de Errores Completo)
    """
    try:
        user_message = parameters.get("query", "")
        print(f"-> ⚙️  Iniciando flujo 'Análisis en Lote' para: '{user_message}'")
        
        # 1. Extraer la lista de tickers (con su propio manejo de error específico)
        try:
            tickers_str = user_message.lower().split('en lote')[1]
            if not tickers_str.strip(): raise IndexError
            tickers = [ticker.strip().upper() for ticker in tickers_str.split(',')]
        except IndexError:
            return jsonify({"response_blocks": [{"type": "text", "content": "Formato incorrecto. Usa: 'analiza en lote TICKER1, TICKER2'", "display_target": "chat"}]})

        # 2. Cargar la "receta" del informe
        report_def_res = db.supabase.table('report_definitions').select('*').eq('report_keyword', 'analisis tecnico').single().execute()
        if not report_def_res.data:
            raise Exception("No se encontró la definición para 'analisis tecnico'.")
        report_config = report_def_res.data
        
        # 3. Bucle de análisis por ticker
        all_results = []
        for ticker in tickers:
            dossier = _prepare_technical_dossier(ticker, report_config)
            if dossier:
                cio_decision = _run_investment_committee(dossier, report_config)
                all_results.append(cio_decision)
            else:
                all_results.append({"ticker": ticker, "recomendacion_final": "Error en preparación de datos", "resumen_cio": "No se pudo generar el dossier técnico."})

        # 4. Formatear el resumen para el panel de chat
        response_text = "### ✅ Resumen del Comité de Inversión\n\n"
        for result in all_results:
            ticker = result.get('ticker', 'Desconocido')
            recommendation = result.get('recomendacion_final', 'Análisis no concluyente')
            summary = result.get('resumen_cio', 'Sin resumen disponible.')
            response_text += f"**Ticker: {ticker}**\n- **Veredicto Final:** {recommendation}\n- **Resumen del CIO:** {summary}\n---\n"
        
        # 5. Preparar el HTML para el panel
        full_dossier_to_display = all_results[-1] if all_results else {}
        clean_chart_url = full_dossier_to_display.get('chart_url_clean')
        indicator_chart_url = full_dossier_to_display.get('chart_url_indicators')
        
        dossier_html = f"<h3>Análisis para: {full_dossier_to_display.get('ticker', 'N/A')}</h3>"
        if clean_chart_url:
            dossier_html += '<h4>Gráfico Chartista (Acción del Precio)</h4>'
            dossier_html += f'<img src="{clean_chart_url}" alt="Gráfico Chartista" style="width: 100%; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px;">'
        if indicator_chart_url:
            dossier_html += '<h4>Gráfico Quant (Indicadores)</h4>'
            dossier_html += f'<img src="{indicator_chart_url}" alt="Gráfico de Indicadores" style="width: 100%; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px;">'
        dossier_html += "<h4>Dossier Técnico Completo</h4>"
        dossier_html += _format_dossier_to_html(full_dossier_to_display)

        # 6. Devolver la respuesta completa
        return jsonify({
            "response_blocks": [
                {"type": "markdown", "content": response_text, "display_target": "chat"},
                {"type": "html", "content": dossier_html, "display_target": "panel"}
            ]
        })

    except Exception as e:
        # Este bloque capturará cualquier otro error inesperado en el flujo
        traceback.print_exc()
        return jsonify({"response_blocks": [{"type": "text", "content": f"Ocurrió un error inesperado en el análisis técnico: {e}"}]})


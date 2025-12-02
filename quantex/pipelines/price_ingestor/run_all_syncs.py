# El Orquestador Principal. Es el script más importante que ejecuta todas las sincronizaciones automáticas diarias (Yahoo, EODHD, BCE).

import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import traceback

# --- Configuración de Rutas y Conexión ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from quantex.core.database_manager import supabase

# --- Configuración de Logging ---
# Logging solo a consola, sin archivos

# --- Sistema de Reporte Final ---
class SyncReport:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.results = {}
        self.errors = {}
        self.summary = {}
        
    def add_result(self, source, success, details=None, error=None):
        """Agrega un resultado de sincronización"""
        self.results[source] = {
            'success': success,
            'details': details or {},
            'error': error,
            'timestamp': datetime.now()
        }
        
        if not success and error:
            self.errors[source] = error
            
    def finalize(self):
        """Finaliza el reporte y genera estadísticas"""
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time
        
        # Calcular estadísticas
        total_sources = len(self.results)
        successful_sources = sum(1 for r in self.results.values() if r['success'])
        failed_sources = total_sources - successful_sources
        
        self.summary = {
            'total_sources': total_sources,
            'successful_sources': successful_sources,
            'failed_sources': failed_sources,
            'success_rate': (successful_sources / total_sources * 100) if total_sources > 0 else 0,
            'duration': self.duration
        }
        
    def generate_report(self):
        """Genera el reporte final completo"""
        self.finalize()
        
        report = f"""
{'='*80}
📊 REPORTE FINAL DE SINCRONIZACIÓN AUTOMÁTICA
{'='*80}

🕐 INFORMACIÓN GENERAL:
   📅 Fecha de ejecución: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
   ⏱️  Duración total: {self.duration}
   🎯 Fuentes procesadas: {self.summary['total_sources']}
   ✅ Exitosas: {self.summary['successful_sources']}
   ❌ Fallidas: {self.summary['failed_sources']}
   📈 Tasa de éxito: {self.summary['success_rate']:.1f}%

{'='*80}
📋 DETALLE POR FUENTE:
{'='*80}
"""
        
        for source, result in self.results.items():
            status = "✅ ÉXITO" if result['success'] else "❌ FALLO"
            report += f"""
🔸 {source.upper()}
   Status: {status}
   Timestamp: {result['timestamp'].strftime('%H:%M:%S')}
"""
            
            if result['success'] and result['details']:
                for key, value in result['details'].items():
                    report += f"   {key}: {value}\n"
                    
            if not result['success'] and result['error']:
                report += f"   Error: {result['error']}\n"
        
        if self.errors:
            report += f"""
{'='*80}
❌ ERRORES DETALLADOS:
{'='*80}
"""
            for source, error in self.errors.items():
                report += f"""
🔸 {source.upper()}
   Error: {error}
"""
        
        report += f"""
{'='*80}
🎯 RESUMEN EJECUTIVO:
{'='*80}
"""
        
        if self.summary['success_rate'] == 100:
            report += "🎉 PERFECTO: 100% de las fuentes sincronizadas exitosamente\n"
        elif self.summary['success_rate'] >= 90:
            report += "🎉 EXCELENTE: Más del 90% de las fuentes sincronizadas exitosamente\n"
        elif self.summary['success_rate'] >= 70:
            report += "✅ BUENO: Más del 70% de las fuentes sincronizadas exitosamente\n"
        elif self.summary['success_rate'] >= 50:
            report += "⚠️  REGULAR: Más del 50% de las fuentes sincronizadas exitosamente\n"
        else:
            report += "❌ CRÍTICO: Menos del 50% de las fuentes sincronizadas exitosamente\n"
        
        report += f"""
📊 Estadísticas:
   • Total de fuentes: {self.summary['total_sources']}
   • Exitosas: {self.summary['successful_sources']}
   • Fallidas: {self.summary['failed_sources']}
   • Tasa de éxito: {self.summary['success_rate']:.1f}%
   • Duración: {self.duration}

{'='*80}
📝 LOG COMPLETO DISPONIBLE EN: {os.path.join(PROJECT_ROOT, 'logs')}
{'='*80}
"""
        
        return report

# --- Importamos a todos nuestros especialistas automáticos ---
from quantex.pipelines.price_ingestor.yahoo_finance import sync_yfinance_data_to_supabase
from quantex.pipelines.price_ingestor.eodhd_client import sync_eodhd_data_to_supabase, sync_us_treasuries_yields
from quantex.pipelines.price_ingestor.bce_client import sync_bce_rates
from quantex.pipelines.price_ingestor.sync_bcentral import sync_all_bcentral_series
from quantex.pipelines.price_ingestor.cochilco_final_bot import FinalCochilcoBot
from quantex.pipelines.price_ingestor.smm_playwright_bot import SMMPlaywrightBot
from quantex.pipelines.price_ingestor.benchmarks import sync_btp_benchmarks, sync_latam_currency_index, sync_latam_currency_index_historical

def sync_cochilco_inventories(report):
    """
    Sincroniza inventarios de cobre desde Cochilco usando el bot Selenium.
    """
    print("🔄 Iniciando sincronización de inventarios de cobre (Cochilco)...")
    logging.info("Iniciando sincronización Cochilco")
    
    try:
        bot = FinalCochilcoBot(headless=False)  # VISIBLE
        success = bot.run_final_workflow()
        
        if success:
            print("✅ Inventarios de cobre sincronizados exitosamente")
            logging.info("Cochilco: Sincronización exitosa")
            
            # Extraer detalles del resultado
            details = {}
            if hasattr(success, 'keys'):
                for key, value in success.items():
                    if hasattr(value, 'shape'):
                        details[f"{key}_registros"] = len(value)
                    else:
                        details[key] = str(value)[:100]  # Limitar longitud
            
            report.add_result("Cochilco", True, details)
        else:
            print("❌ Error en sincronización de inventarios de cobre")
            logging.error("Cochilco: Error en sincronización")
            report.add_result("Cochilco", False, error="Error en sincronización")
            
    except Exception as e:
        error_msg = f"Error crítico en sincronización Cochilco: {e}"
        print(f"❌ {error_msg}")
        logging.error(f"Cochilco: {error_msg}")
        logging.error(traceback.format_exc())
        report.add_result("Cochilco", False, error=error_msg)

def sync_smm_prices(report):
    """
    Sincroniza precios de cobre y litio desde SMM usando el bot Playwright.
    """
    print("🔄 Iniciando sincronización de precios SMM (Cobre + Litio) - Playwright...")
    logging.info("Iniciando sincronización SMM (Playwright)")
    
    try:
        bot = SMMPlaywrightBot(headless=False)  # VISIBLE (requerido para SMM)
        result = bot.run_workflow()
        
        if result.get("success"):
            print("✅ Precios SMM sincronizados exitosamente")
            logging.info("SMM: Sincronización exitosa")
            
            # Extraer detalles del resultado real
            results = result.get("results", {})
            details = {}
            for key, extracted in results.items():
                details[key] = "Extraído" if extracted else "No extraído"
            
            # Determinar si es éxito total o parcial
            success_count = result.get("count", 0)
            if success_count == 3:
                report.add_result("SMM", True, details)
            elif success_count > 0:
                report.add_result("SMM", True, details, partial=True)
            else:
                report.add_result("SMM", False, details, error="Ningún precio extraído")
        else:
            print("❌ Error en sincronización de precios SMM")
            logging.error("SMM: Error en sincronización")
            error_msg = result.get("error", "Error en sincronización")
            report.add_result("SMM", False, error=error_msg)
            
    except Exception as e:
        error_msg = f"Error crítico en sincronización SMM: {e}"
        print(f"❌ {error_msg}")
        logging.error(f"SMM: {error_msg}")
        logging.error(traceback.format_exc())
        report.add_result("SMM", False, error=error_msg)


# --- Forward Fill Centralizado (Business Days) ---
def _get_series_id_by_ticker(ticker: str) -> str | None:
    try:
        res = supabase.table('series_definitions').select('id').eq('ticker', ticker).limit(1).execute()
        if res and res.data:
            return res.data[0]['id']
    except Exception as e:
        logging.error(f"ForwardFill: error obteniendo series_id para {ticker}: {e}")
    return None


def forward_fill_business_days_for_ticker(ticker: str, lag_days: int = 0) -> dict:
    """Rellena días hábiles faltantes desde el último dato REAL disponible hasta hoy.

    Comportamiento:
    - Usa como punto de partida el último dato cuya fecha sea <= hoy - lag_days.
      Esto permite manejar series con desfase natural (ej: Posición Extranjera CLP).
    - A partir de ese último dato real, vuelve a calcular TODOS los forward fill
      hasta hoy, sobrescribiendo cualquier valor forward-filleado anterior.
    - No crea fines de semana.
    - Upsert idempotente (series_id,timestamp).
    """
    try:
        series_id = _get_series_id_by_ticker(ticker)
        if not series_id:
            return {"ticker": ticker, "filled": 0, "status": "series_not_found"}

        today = datetime.now().date()
        # Para series con desfase natural (ej: BCCh), consideramos como "datos reales"
        # solo aquellos con fecha <= effective_today. Los días posteriores se tratan
        # como cola forward-filleada que puede ser recalculada.
        if lag_days > 0:
            effective_today = today - timedelta(days=lag_days)
        else:
            effective_today = today

        # Último dato REAL existente (ignorando la posible cola de forward fill)
        last_res = (
            supabase.table('time_series_data')
            .select('timestamp,value')
            .eq('series_id', series_id)
            .lte('timestamp', effective_today.strftime('%Y-%m-%d'))
            .order('timestamp', desc=True)
            .limit(1)
            .execute()
        )

        if not last_res or not last_res.data:
            return {"ticker": ticker, "filled": 0, "status": "no_existing_data"}

        last_ts_raw = last_res.data[0]['timestamp']
        # Normalizar timestamp a 'YYYY-MM-DD' (algunas filas vienen con 'T00:00:00+00:00')
        last_ts_str = str(last_ts_raw)[:10]
        last_val = last_res.data[0]['value']
        last_date = datetime.strptime(last_ts_str, '%Y-%m-%d').date()

        # Si ya tenemos datos reales de hoy (o posteriores), no hay nada que rellenar.
        # NOTA: la comparación es contra "today", no contra "effective_today".
        #       Queremos siempre rellenar la cola desde el último dato REAL hasta hoy,
        #       incluso cuando exista un desfase natural en la publicación (lag_days).
        if last_date >= today:
            return {"ticker": ticker, "filled": 0, "status": "up_to_date"}

        # Rango de días hábiles desde el día siguiente al último dato REAL hasta hoy
        start_bday = pd.Timestamp(last_date) + pd.tseries.offsets.BDay(1)
        if start_bday.date() > today:
            return {"ticker": ticker, "filled": 0, "status": "no_business_days_to_fill"}

        bdays = pd.bdate_range(start=start_bday.date(), end=today, freq='B')
        records = []
        for d in bdays:
            records.append({
                'series_id': series_id,
                'timestamp': d.strftime('%Y-%m-%d'),
                'value': last_val,
                'ticker': ticker,
            })

        filled = 0
        if records:
            upsert = supabase.table('time_series_data').upsert(records, on_conflict='series_id,timestamp').execute()
            if upsert and upsert.data is not None:
                filled = len(records)

        logging.info(
            f"ForwardFill[{ticker}]: desde {start_bday.date()} (último real {last_date}, lag={lag_days}) "
            f"hasta {today} -> {filled} días hábiles"
        )
        return {
            "ticker": ticker,
            "filled": filled,
            "status": "ok",
            "from": start_bday.strftime('%Y-%m-%d'),
            "to": today.strftime('%Y-%m-%d'),
            "last_real_date": last_date.strftime('%Y-%m-%d'),
            "lag_days": lag_days,
        }

    except Exception as e:
        logging.error(f"ForwardFill[{ticker}] error: {e}")
        return {"ticker": ticker, "filled": 0, "status": f"error: {e}"}


def forward_fill_business_days_for_tickers(
    tickers: list[str],
    lag_days_map: dict | None = None,
) -> dict:
    """Aplica forward fill diario a múltiples tickers.

    - `lag_days_map` permite especificar, por ticker, cuántos días de desfase natural
      tiene la serie (ej: {'Posicion Extranjera CLP': 2}).
    - Los tickers que no aparecen en el mapa usan lag_days = 0 (comportamiento original).
    """
    summary = {}
    lag_days_map = lag_days_map or {}
    for t in tickers:
        lag = lag_days_map.get(t, 0)
        summary[t] = forward_fill_business_days_for_ticker(t, lag_days=lag)
    return summary


def forward_fill_monthly_series_for_ticker(ticker: str) -> dict:
    """Rellena días hábiles con el último valor mensual disponible.
    
    Para series mensuales (como expectativas TPM), toma el último dato
    y lo propaga a todos los días hábiles hasta hoy, para que los agentes
    siempre tengan acceso a las "expectativas vigentes".
    
    - Rellena desde el último dato hasta hoy
    - Solo días hábiles (no fines de semana)
    - Upsert idempotente (series_id,timestamp)
    """
    try:
        series_id = _get_series_id_by_ticker(ticker)
        if not series_id:
            return {"ticker": ticker, "filled": 0, "status": "series_not_found"}

        # Último dato existente
        last_res = supabase.table('time_series_data').select('timestamp,value').eq('series_id', series_id).order('timestamp', desc=True).limit(1).execute()
        if not last_res or not last_res.data:
            return {"ticker": ticker, "filled": 0, "status": "no_existing_data"}

        last_ts_raw = last_res.data[0]['timestamp']
        last_ts_str = str(last_ts_raw)[:10]
        last_val = last_res.data[0]['value']
        last_date = datetime.strptime(last_ts_str, '%Y-%m-%d').date()

        today = datetime.now().date()
        if last_date >= today:
            return {"ticker": ticker, "filled": 0, "status": "up_to_date"}

        # Para series mensuales: rellenar DESDE el último dato hasta hoy
        # (incluye el día del último dato en el rango)
        bdays = pd.bdate_range(start=last_date, end=today, freq='B')
        
        # Excluir el primer día (último dato ya existe)
        if len(bdays) > 1:
            bdays = bdays[1:]
        else:
            return {"ticker": ticker, "filled": 0, "status": "no_business_days_to_fill"}
        
        records = []
        for d in bdays:
            records.append({
                'series_id': series_id,
                'timestamp': d.strftime('%Y-%m-%d'),
                'value': last_val,
                'ticker': ticker,
            })

        filled = 0
        if records:
            upsert = supabase.table('time_series_data').upsert(records, on_conflict='series_id,timestamp').execute()
            if upsert and upsert.data is not None:
                filled = len(records)
        
        logging.info(f"ForwardFillMonthly[{ticker}]: desde {last_date} hasta {today} -> {filled} días hábiles")
        return {"ticker": ticker, "filled": filled, "status": "ok", "last_value": last_val, "from": last_date.strftime('%Y-%m-%d'), "to": today.strftime('%Y-%m-%d')}

    except Exception as e:
        logging.error(f"ForwardFillMonthly[{ticker}] error: {e}")
        return {"ticker": ticker, "filled": 0, "status": f"error: {e}"}


def forward_fill_monthly_series_for_tickers(tickers: list[str]) -> dict:
    """Aplica forward fill mensual a múltiples tickers."""
    summary = {}
    for t in tickers:
        summary[t] = forward_fill_monthly_series_for_ticker(t)
    return summary

def orchestrate_all_syncs():
    """
    Orquesta la sincronización de todas las fuentes de datos AUTOMÁTICAS
    definidas en la base de datos.
    """
    # Configurar logging solo a consola
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]  # Solo consola, sin archivo
    )
    
    # Inicializar reporte
    report = SyncReport()
    
    print("--- 🎼 Iniciando Orquestador de Sincronización Automática ---")
    logging.info("Iniciando orquestador de sincronización automática")

    if not supabase:
        error_msg = "No se pudo conectar con Supabase. Proceso abortado."
        print(f"❌ Error: {error_msg}")
        logging.error(error_msg)
        report.add_result("Supabase", False, error=error_msg)
        print(report.generate_report())
        return

    try:
        # --- Tareas de Renta Variable y Similares (OHLCV) ---
        print("\n--- ▶️  Iniciando sincronización de datos OHLCV... ---")
        logging.info("Iniciando sincronización OHLCV")
        
        try:
            sync_yfinance_data_to_supabase()
            report.add_result("Yahoo Finance", True, {"tipo": "OHLCV"})
            logging.info("Yahoo Finance: Sincronización exitosa")
        except Exception as e:
            error_msg = f"Error en Yahoo Finance: {e}"
            logging.error(error_msg)
            report.add_result("Yahoo Finance", False, error=error_msg)
        
        try:
            sync_eodhd_data_to_supabase() # La parte de OHLCV de EODHD
            report.add_result("EODHD OHLCV", True, {"tipo": "OHLCV"})
            logging.info("EODHD OHLCV: Sincronización exitosa")
        except Exception as e:
            error_msg = f"Error en EODHD OHLCV: {e}"
            logging.error(error_msg)
            report.add_result("EODHD OHLCV", False, error=error_msg)

        # --- Tareas de Renta Fija Internacional ---
        print("\n--- ▶️  Iniciando sincronización de Renta Fija Internacional... ---")
        logging.info("Iniciando sincronización Renta Fija Internacional")
        
        try:
            sync_us_treasuries_yields() # Bonos USA de EODHD
            report.add_result("US Treasuries", True, {"tipo": "Renta Fija"})
            logging.info("US Treasuries: Sincronización exitosa")
        except Exception as e:
            error_msg = f"Error en US Treasuries: {e}"
            logging.error(error_msg)
            report.add_result("US Treasuries", False, error=error_msg)
        
        try:
            sync_bce_rates()            # Curva de rendimientos de BCE
            report.add_result("BCE Rates", True, {"tipo": "Renta Fija"})
            logging.info("BCE Rates: Sincronización exitosa")
        except Exception as e:
            error_msg = f"Error en BCE Rates: {e}"
            logging.error(error_msg)
            report.add_result("BCE Rates", False, error=error_msg)

        # --- Tareas de Indicadores Económicos Chile ---
        print("\n--- ▶️  Iniciando sincronización de Indicadores Económicos Chile... ---")
        logging.info("Iniciando sincronización Indicadores Económicos Chile")
        
        try:
            sync_all_bcentral_series()  # TPM y Posición Forward Extranjeros
            report.add_result("Banco Central Chile", True, {"tipo": "Indicadores Económicos"})
            logging.info("Banco Central Chile: Sincronización exitosa")
        except Exception as e:
            error_msg = f"Error en Banco Central Chile: {e}"
            logging.error(error_msg)
            report.add_result("Banco Central Chile", False, error=error_msg)

        # --- Benchmarks Renta Fija Chile (BTP 2/5/10) ---
        print("\n--- ▶️  Actualizando Benchmarks BTP (CLP) ... ---")
        try:
            bench_res = sync_btp_benchmarks()
            report.add_result("BTP Benchmarks", True, bench_res)
            logging.info(f"BTP Benchmarks: {bench_res}")
        except Exception as e:
            error_msg = f"Error en BTP Benchmarks: {e}"
            logging.error(error_msg)
            report.add_result("BTP Benchmarks", False, error=error_msg)

        # --- Índice de Monedas LATAM ---
        print("\n--- ▶️  Actualizando Índice de Monedas LATAM ... ---")
        try:
            latam_res = sync_latam_currency_index()
            report.add_result("LATAM Currency Index", True, latam_res)
            logging.info(f"LATAM Currency Index: {latam_res}")
        except Exception as e:
            error_msg = f"Error en LATAM Currency Index: {e}"
            logging.error(error_msg)
            report.add_result("LATAM Currency Index", False, error=error_msg)

        # --- Serie Histórica Índice LATAM ---
        print("\n--- ▶️  Generando Serie Histórica Índice LATAM ... ---")
        try:
            historical_res = sync_latam_currency_index_historical(days_back=1000)
            report.add_result("LATAM Historical Series", True, historical_res)
            logging.info(f"LATAM Historical Series: {historical_res}")
        except Exception as e:
            error_msg = f"Error en Serie Histórica LATAM: {e}"
            logging.error(error_msg)
            report.add_result("LATAM Historical Series", False, error=error_msg)

        # --- Tareas de Inventarios de Cobre (Cochilco) ---
        print("\n--- ▶️  Iniciando sincronización de Inventarios de Cobre... ---")
        sync_cochilco_inventories(report)

        # --- Tareas de Precios SMM (Cobre + Litio) ---
        print("\n--- ▶️  Iniciando sincronización de Precios SMM... ---")
        sync_smm_prices(report)

        # --- Forward Fill centralizado para series diarias (Business Days) ---
        print("\n--- ▶️  Forward Fill (Business Days) para series diarias ... ---")
        try:
            # SMM precios diarios
            smm_tickers = ['shfe', 'lme', 'Lithium China']

            # Inventarios Cochilco (según mapeo en cochilco_final_bot)
            cochilco_inventory_tickers = [
                'inventarios_lme',
                'inventarios_comex',
                'inventarios_shfe',
                'inventarios_totales'
            ]

            # Series Banco Central de Chile (según sync_bcentral)
            bcch_tickers = [
                'chile_tpm',
                'Posicion Extranjera CLP',
                'us_tpm'
            ]

            all_ff_tickers = smm_tickers + cochilco_inventory_tickers + bcch_tickers

            # Mapa de desfases naturales por ticker.
            # - Posición Extranjera CLP: serie diaria del BCCh con desfase de ~2 días.
            #   Usamos lag_days=2 para que el último dato REAL siempre sea el punto
            #   de partida del forward fill (evitando arrastrar colas antiguas).
            lag_days_map = {
                'Posicion Extranjera CLP': 2,
            }

            ff_summary = forward_fill_business_days_for_tickers(all_ff_tickers, lag_days_map=lag_days_map)
            report.add_result("ForwardFill Daily", True, ff_summary)
            logging.info(f"ForwardFill Daily resumen: {ff_summary}")
        except Exception as e:
            error_msg = f"Error en ForwardFill centralizado: {e}"
            logging.error(error_msg)
            report.add_result("ForwardFill Daily", False, error=error_msg)

        # --- Forward Fill para series mensuales (Expectativas TPM) ---
        print("\n--- ▶️  Forward Fill (Monthly Series) para expectativas mensuales ... ---")
        try:
            # Series mensuales de expectativas del BCCh
            monthly_bcch_tickers = [
                'bcch_expectativas_tpm_prox_reunion',
                'bcch_expectativas_tpm_subsiguiente_reunion'
            ]

            ff_monthly_summary = forward_fill_monthly_series_for_tickers(monthly_bcch_tickers)
            report.add_result("ForwardFill Monthly", True, ff_monthly_summary)
            logging.info(f"ForwardFill Monthly resumen: {ff_monthly_summary}")
            
            # Log detallado de cada serie mensual
            for ticker, result in ff_monthly_summary.items():
                if result.get('status') == 'ok':
                    print(f"   ✅ {ticker}: {result.get('filled')} días rellenados con valor {result.get('last_value')}")
                else:
                    print(f"   ⚠️ {ticker}: {result.get('status')}")
        except Exception as e:
            error_msg = f"Error en ForwardFill Monthly: {e}"
            logging.error(error_msg)
            report.add_result("ForwardFill Monthly", False, error=error_msg)

        print("\n\n--- ✅ Orquestación Automática Completada Exitosamente ---")
        print("ℹ️  Nota: La ingesta de Renta Fija local (PDF) se ejecuta por separado.")
        logging.info("Orquestación automática completada exitosamente")

    except Exception as e:
        error_msg = f"ERROR CRÍTICO en el Orquestador: {e}"
        print(f"--- 💥 {error_msg} ---")
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        report.add_result("Orquestador", False, error=error_msg)

    finally:
        # Generar y mostrar reporte final
        print("\n" + report.generate_report())
        logging.info("Reporte final generado")


if __name__ == "__main__":
    orchestrate_all_syncs()
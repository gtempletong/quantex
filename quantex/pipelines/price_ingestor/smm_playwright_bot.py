import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
import re
from playwright.sync_api import sync_playwright, Browser, Page

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.config import Config
from quantex.core.database_manager import supabase

class SMMPlaywrightBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.page = None
        # Use the shared Supabase client from database_manager
        self.supabase = supabase
        if not self.supabase:
            print("⚠️ Supabase no disponible - modo prueba sin sincronización")
    
    def setup_browser(self):
        """Setup Playwright browser"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = self.browser.new_page()
            print("✅ Browser configurado correctamente")
            return True
        except Exception as e:
            print(f"❌ Error configurando browser: {e}")
            return False
    
    def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
            print("🔒 Browser cerrado")
        except Exception as e:
            print(f"⚠️ Error cerrando browser: {e}")
    
    def extract_copper_prices(self):
        """Extract SHFE and LME copper prices using Playwright"""
        try:
            print("🔍 Extrayendo precios de cobre (Playwright Simple)...")
            
            # Navigate to copper page
            url = "https://www.metal.com/Copper"
            print(f"🌐 Navegando a: {url}")
            
            self.page.goto(url, wait_until="networkidle")
            time.sleep(5)  # Wait for dynamic content
            
            print("   -> 🔍 Página cargada. Continuando automáticamente...")
            
            # Extract SHFE price
            print("🔄 Extrayendo precio SHFE...")
            shfe_price = self._extract_shfe_price()
            
            # Extract LME price
            print("🔄 Extrayendo precio LME...")
            lme_price = self._extract_lme_price()
            
            return shfe_price, lme_price
            
        except Exception as e:
            print(f"❌ Error extrayendo precios de cobre: {e}")
            return None, None
    
    def _extract_shfe_price(self):
        """Extract SHFE price - first price of first row"""
        try:
            print("💰 Extrayendo precio SHFE (primera fila, primera columna)...")
            
            # Click on SHFE tab
            try:
                shfe_tab = self.page.locator("text=SHFE").first
                if shfe_tab.is_visible():
                    shfe_tab.click()
                    print("   -> ✅ Clic en pestaña SHFE exitoso")
                    time.sleep(3)  # Wait for content to load
                else:
                    print("   -> ⚠️ Pestaña SHFE no encontrada")
            except:
                print("   -> ⚠️ Error haciendo clic en SHFE")
            
            # Extract price using efficient method
            try:
                # Look for elements that contain prices
                price_elements = self.page.locator("text=/\\d{1,3}(,\\d{3})*\\.?\\d*/").all()
                
                for element in price_elements[:10]:  # Check first 10 elements
                    text = element.text_content().strip()
                    if text and ',' in text:
                        # Try to extract price
                        price_match = re.search(r'[\d,]+\.?\d*', text)
                        if price_match:
                            price_str = price_match.group().replace(',', '')
                            try:
                                price = float(price_str)
                                if 50000 < price < 150000:  # Rango razonable para SHFE
                                    print(f"   -> ✅ Precio SHFE extraído: {price}")
                                    return price
                            except:
                                continue
                                
            except Exception as e:
                print(f"   -> ❌ Error extrayendo precio: {e}")
            
            print("   -> ❌ No se encontró precio SHFE")
            return None
            
        except Exception as e:
            print(f"   -> ❌ Error extrayendo SHFE: {e}")
            return None
    
    def _extract_lme_price(self):
        """Extract LME price - first price of first row"""
        try:
            print("💰 Extrayendo precio LME (primera fila, primera columna)...")
            
            # Click on LME tab
            try:
                lme_tab = self.page.locator("text=LME").first
                if lme_tab.is_visible():
                    lme_tab.click()
                    print("   -> ✅ Clic en pestaña LME exitoso")
                    time.sleep(3)  # Wait for content to load
                else:
                    print("   -> ⚠️ Pestaña LME no encontrada")
            except:
                print("   -> ⚠️ Error haciendo clic en LME")
            
            # Extract price using efficient method
            try:
                # Look for elements that contain prices
                price_elements = self.page.locator("text=/\\d{1,3}(,\\d{3})*\\.?\\d*/").all()
                
                for element in price_elements[:10]:  # Check first 10 elements
                    text = element.text_content().strip()
                    if text and ',' in text:
                        # Try to extract price
                        price_match = re.search(r'[\d,]+\.?\d*', text)
                        if price_match:
                            price_str = price_match.group().replace(',', '')
                            try:
                                price = float(price_str)
                                if 8000 < price < 12000:  # Rango razonable para LME
                                    print(f"   -> ✅ Precio LME extraído: {price}")
                                    return price
                            except:
                                continue
                                
            except Exception as e:
                print(f"   -> ❌ Error extrayendo precio: {e}")
            
            print("   -> ❌ No se encontró precio LME")
            return None
            
        except Exception as e:
            print(f"   -> ❌ Error extrayendo LME: {e}")
            return None
    
    def extract_lithium_price(self):
        """Extract lithium price using simple approach"""
        try:
            print("🔍 Extrayendo precio de litio (Playwright Simple)...")
            
            # Navigate to lithium page
            url = "https://www.metal.com/Lithium"
            print(f"🌐 Navegando a: {url}")
            
            self.page.goto(url, wait_until="networkidle")
            time.sleep(5)  # Wait for dynamic content
            
            # Extract lithium price - first price of first row
            print("💰 Extrayendo precio Lithium (primera fila, primera columna)...")
            
            try:
                # Look for elements that contain prices
                price_elements = self.page.locator("text=/\\d{1,3}(,\\d{3})*\\.?\\d*/").all()
                
                for element in price_elements[:10]:  # Check first 10 elements
                    text = element.text_content().strip()
                    if text and ',' in text:
                        # Try to extract price
                        price_match = re.search(r'[\d,]+\.?\d*', text)
                        if price_match:
                            price_str = price_match.group().replace(',', '')
                            try:
                                price = float(price_str)
                                if 50000 < price < 100000:  # Rango razonable para litio
                                    print(f"   -> ✅ Precio litio extraído: {price}")
                                    return price
                            except:
                                continue
                                
            except Exception as e:
                print(f"   -> ❌ Error extrayendo precio: {e}")
            
            print("   -> ❌ No se encontró precio de litio")
            return None
            
        except Exception as e:
            print(f"❌ Error extrayendo precio de litio: {e}")
            return None
    
    def sync_price_to_supabase(self, price, ticker):
        """Sync price data to Supabase (solo upsert del día actual; FF centralizado)."""
        try:
            print(f"📊 Sincronizando precio para {ticker}...")
            
            # Buscar serie existente (siguiendo el patrón de cochilco_final_bot.py)
            series_res = self.supabase.table('series_definitions').select('id').eq('ticker', ticker).execute()
            
            if series_res.data and len(series_res.data) > 0:
                series_id = series_res.data[0]['id']
                print(f"   -> ✅ Serie existente encontrada: {series_id}")
            else:
                print(f"   -> ❌ Serie no encontrada: {ticker}")
                return False
            # Upsert solamente el día actual
            today = datetime.now().strftime('%Y-%m-%d')
            record = {
                'series_id': series_id,
                'timestamp': today,
                'value': price,
                'ticker': ticker
            }
            upsert_res = self.supabase.table('time_series_data').upsert(
                record,
                on_conflict='series_id,timestamp'
            ).execute()
            if upsert_res and upsert_res.data is not None:
                print(f"   -> ✅ Precio actualizado para {ticker} en {today}: {price}")
                return True
            print(f"   -> ❌ Error en upsert para {ticker}")
            return False
                
        except Exception as e:
            print(f"❌ Error sincronizando {ticker}: {e}")
            return False
    
    
    def run_workflow(self):
        """Run the complete SMM extraction workflow"""
        try:
            print("🚀 Iniciando extracción SMM unificada (Playwright Simple)...")
            
            if not self.setup_browser():
                return {"success": False, "error": "No se pudo configurar el browser"}
            
            # Extract copper prices
            shfe_price, lme_price = self.extract_copper_prices()
            
            # Extract lithium price
            lithium_price = self.extract_lithium_price()
            
            # Process and sync data
            success_count = 0
            results = {
                "SHFE": shfe_price is not None,
                "LME": lme_price is not None,
                "Lithium": lithium_price is not None
            }
            
            if shfe_price:
                if self.sync_price_to_supabase(shfe_price, 'shfe'):
                    success_count += 1
            
            if lme_price:
                if self.sync_price_to_supabase(lme_price, 'lme'):
                    success_count += 1
            
            if lithium_price:
                if self.sync_price_to_supabase(lithium_price, 'Lithium China'):
                    success_count += 1
            
            # Generate report
            print("\n" + "="*60)
            print("📊 REPORTE DE EXTRACCIÓN SMM UNIFICADO (PLAYWRIGHT SIMPLE)")
            print("="*60)
            
            if shfe_price:
                print(f"🔶 Precio SHFE: {shfe_price} CNY/mt")
            else:
                print("❌ SHFE: No extraído")
            
            if lme_price:
                print(f"🔶 Precio LME: {lme_price} USD/mt")
            else:
                print("❌ LME: No extraído")
            
            if lithium_price:
                print(f"🔋 Precio Litio GFEX: {lithium_price} CNY/mt")
            else:
                print("❌ Litio: No extraído")
            
            print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("🌐 Fuente: SMM (Shanghai Metals Market) - Playwright Simple")
            print("="*60)
            
            if success_count > 0:
                print(f"\n🎉 ✅ EXTRACCIÓN SMM COMPLETADA ({success_count}/3 precios)")
                return {"success": True, "results": results, "count": success_count}
            else:
                print("\n❌ EXTRACCIÓN SMM FALLIDA")
                return {"success": False, "results": results, "count": 0}
            
        except Exception as e:
            print(f"❌ Error en workflow: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            self.close_browser()


if __name__ == "__main__":
    bot = SMMPlaywrightBot(headless=False)
    result = bot.run_workflow()
    print(f"\n🎉 ✅ EXTRACCIÓN EXITOSA")
    print(f"📊 Precios extraídos: {result.get('count', 0)}/3")
    print(f"📋 Detalles: {result.get('results', {})}")

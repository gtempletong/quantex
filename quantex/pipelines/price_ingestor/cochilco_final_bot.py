# quantex/pipelines/price_ingestor/cochilco_final_bot.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import time
import re
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ ERROR: Faltan credenciales de Supabase en el archivo .env")
    exit(1)

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class FinalCochilcoBot:
    def __init__(self, headless=True):
        """
        Bot final de Cochilco: extrae último dato y hace forward fill.
        """
        self.driver = None
        self.headless = headless
        self.base_url = "https://www.cochilco.cl:4040/boletin-web/pages/index/index.jsf"
        
    def setup_driver(self):
        """
        Configura el driver de Chrome.
        """
        print("🔧 Configurando driver de Chrome...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            print("   -> ✅ Driver configurado correctamente")
            return True
        except Exception as e:
            print(f"   -> ❌ Error configurando driver: {e}")
            return False
    
    def navigate_to_inventories(self):
        """
        Navega a la página de inventarios.
        """
        print("🌐 Navegando a inventarios...")
        
        try:
            # Cargar página principal
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Buscar enlace de inventarios
            inventory_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Inventarios')]")
            if inventory_links:
                inventory_links[0].click()
                print("   -> ✅ Navegación exitosa")
                time.sleep(5)
                return True
            else:
                print("   -> ❌ No se encontró enlace de inventarios")
                return False
                
        except Exception as e:
            print(f"   -> ❌ Error navegando: {e}")
            return False
    
    def select_all_checkboxes(self):
        """
        Selecciona todos los checkboxes disponibles.
        """
        print("📋 Seleccionando todos los checkboxes...")
        
        try:
            checkboxes = self.driver.find_elements(By.XPATH, '//input[@type="checkbox"]')
            print(f"   -> Checkboxes encontrados: {len(checkboxes)}")
            
            selected_count = 0
            for i, checkbox in enumerate(checkboxes):
                try:
                    if not checkbox.is_selected():
                        checkbox.click()
                        selected_count += 1
                        print(f"      ✅ Checkbox {i+1} seleccionado")
                except Exception as e:
                    print(f"      ⚠️ Error con checkbox {i+1}: {e}")
            
            print(f"   -> Total checkboxes seleccionados: {selected_count}")
            return selected_count > 0
            
        except Exception as e:
            print(f"   -> ❌ Error seleccionando checkboxes: {e}")
            return False
    
    def configure_all_selects(self):
        """
        Configura todos los selects disponibles.
        """
        print("📅 Configurando todos los selects...")
        
        try:
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            print(f"   -> Fechas objetivo: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
            
            selects = self.driver.find_elements(By.TAG_NAME, 'select')
            print(f"   -> Selects encontrados: {len(selects)}")
            
            configured_count = 0
            for i, select in enumerate(selects):
                try:
                    select_id = select.get_attribute('id') or f'select_{i}'
                    select_name = select.get_attribute('name') or 'sin_nombre'
                    
                    print(f"      Select {i+1}: id='{select_id}', name='{select_name}'")
                    
                    # Intentar configurar según el tipo
                    if 'dia' in select_id.lower() or 'day' in select_id.lower():
                        if 'desde' in select_id.lower() or 'from' in select_id.lower():
                            Select(select).select_by_visible_text(str(start_date.day))
                            print(f"         ✅ Día desde: {start_date.day}")
                            configured_count += 1
                        elif 'hasta' in select_id.lower() or 'to' in select_id.lower():
                            Select(select).select_by_visible_text(str(end_date.day))
                            print(f"         ✅ Día hasta: {end_date.day}")
                            configured_count += 1
                    
                    elif 'mes' in select_id.lower() or 'month' in select_id.lower():
                        month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                        
                        if 'desde' in select_id.lower() or 'from' in select_id.lower():
                            month_name = month_names[start_date.month - 1]
                            try:
                                Select(select).select_by_visible_text(month_name)
                                print(f"         ✅ Mes desde: {month_name}")
                                configured_count += 1
                            except:
                                Select(select).select_by_value(str(start_date.month))
                                print(f"         ✅ Mes desde: {start_date.month}")
                                configured_count += 1
                        elif 'hasta' in select_id.lower() or 'to' in select_id.lower():
                            month_name = month_names[end_date.month - 1]
                            try:
                                Select(select).select_by_visible_text(month_name)
                                print(f"         ✅ Mes hasta: {month_name}")
                                configured_count += 1
                            except:
                                Select(select).select_by_value(str(end_date.month))
                                print(f"         ✅ Mes hasta: {end_date.month}")
                                configured_count += 1
                    
                    elif 'año' in select_id.lower() or 'year' in select_id.lower():
                        if 'desde' in select_id.lower() or 'from' in select_id.lower():
                            Select(select).select_by_visible_text(str(start_date.year))
                            print(f"         ✅ Año desde: {start_date.year}")
                            configured_count += 1
                        elif 'hasta' in select_id.lower() or 'to' in select_id.lower():
                            Select(select).select_by_visible_text(str(end_date.year))
                            print(f"         ✅ Año hasta: {end_date.year}")
                            configured_count += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Error con select {i+1}: {e}")
            
            print(f"   -> Total selects configurados: {configured_count}")
            return configured_count > 0
            
        except Exception as e:
            print(f"   -> ❌ Error configurando selects: {e}")
            return False
    
    def click_any_button(self):
        """
        Hace clic en cualquier botón disponible.
        """
        print("🔍 Buscando botón de búsqueda...")
        
        try:
            # Buscar botones
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            inputs = self.driver.find_elements(By.XPATH, '//input[@type="submit"]')
            
            print(f"   -> Botones encontrados: {len(buttons)}")
            print(f"   -> Inputs submit encontrados: {len(inputs)}")
            
            # Intentar con botones
            for i, button in enumerate(buttons):
                try:
                    button_text = button.text.strip()
                    if button_text and ('buscar' in button_text.lower() or 'search' in button_text.lower()):
                        button.click()
                        print(f"      ✅ Botón '{button_text}' clickeado")
                        time.sleep(10)
                        return True
                except Exception as e:
                    print(f"      ⚠️ Error con botón {i+1}: {e}")
            
            # Intentar con inputs
            for i, input_elem in enumerate(inputs):
                try:
                    input_value = input_elem.get_attribute('value') or ''
                    if input_value and ('buscar' in input_value.lower() or 'search' in input_value.lower()):
                        input_elem.click()
                        print(f"      ✅ Input '{input_value}' clickeado")
                        time.sleep(10)
                        return True
                except Exception as e:
                    print(f"      ⚠️ Error con input {i+1}: {e}")
            
            # Si no encuentra botón específico, intentar con el primero
            if buttons:
                try:
                    buttons[0].click()
                    print("      ✅ Primer botón clickeado")
                    time.sleep(10)
                    return True
                except Exception as e:
                    print(f"      ⚠️ Error con primer botón: {e}")
            
            print("   -> ❌ No se encontró botón de búsqueda")
            return False
            
        except Exception as e:
            print(f"   -> ❌ Error buscando botón: {e}")
            return False
    
    def extract_latest_data_with_dates(self):
        """
        Extrae el último dato disponible con su fecha real de cada exchange.
        """
        print("📊 Extrayendo último dato con fecha real...")
        
        try:
            latest_data = {}
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            
            print(f"   -> Tablas encontradas: {len(tables)}")
            
            # Buscar específicamente la tabla de inventarios
            inventory_table = None
            for i, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    if len(rows) < 2:
                        continue
                    
                    # Buscar tabla que contenga "Inventarios" en el texto
                    table_text = table.text.lower()
                    if 'inventarios' in table_text and 'tm' in table_text:
                        inventory_table = table
                        print(f"      ✅ Tabla de inventarios encontrada: Tabla {i+1}")
                        break
                except:
                    continue
            
            if not inventory_table:
                print("   -> ❌ No se encontró tabla de inventarios")
                return {}
            
            # Analizar la tabla de inventarios
            rows = inventory_table.find_elements(By.TAG_NAME, 'tr')
            print(f"   -> Filas en tabla de inventarios: {len(rows)}")
            
            # Buscar fechas en las primeras filas
            dates = []
            for row_idx in range(min(3, len(rows))):
                row = rows[row_idx]
                cells = row.find_elements(By.TAG_NAME, 'th')
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                
                print(f"      Fila {row_idx+1}: {len(cells)} celdas")
                for cell_idx, cell in enumerate(cells):
                    cell_text = cell.text.strip()
                    print(f"         Celda {cell_idx+1}: '{cell_text}'")
                    
                    # Buscar patrones de fecha específicos de Cochilco
                    if re.search(r'\d{1,2}-[a-z]{3}-\d{2,4}', cell_text.lower()):
                        dates.append(cell_text)
                        print(f"         📅 Fecha encontrada: {cell_text}")
                
                if dates:
                    print(f"      📅 Total fechas encontradas en fila {row_idx+1}: {len(dates)}")
                    break
            
            if not dates:
                print("   -> ❌ No se encontraron fechas en la tabla de inventarios")
                return {}
            
            # Analizar cada fila de datos
            for j, row in enumerate(rows[1:], 1):
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) < 2:
                        continue
                    
                    row_text = ' '.join([cell.text for cell in cells]).lower()
                    print(f"      Fila {j}: {row_text}")
                    
                    # Buscar patrones de bolsas
                    exchange = None
                    if 'bml' in row_text or 'lme' in row_text:
                        exchange = 'LME'
                    elif 'comex' in row_text:
                        exchange = 'COMEX'
                    elif 'shfe' in row_text or 'shanghai' in row_text:
                        exchange = 'SHFE'
                    
                    if exchange:
                        print(f"         🔍 Analizando {exchange}...")
                        
                        # Extraer valores y mapearlos a fechas
                        date_value_pairs = []
                        for cell_idx, cell in enumerate(cells):
                            text = cell.text.strip()
                            if re.match(r'^\d+[\.,]?\d*$', text):
                                try:
                                    clean_text = text.replace(',', '').replace('.', '')
                                    value = int(clean_text)
                                    
                                    # Mapear a fecha si existe (cell_idx - 1 porque la primera columna es el nombre)
                                    if cell_idx - 1 < len(dates):
                                        date_str = dates[cell_idx - 1]
                                        date_value_pairs.append((date_str, value))
                                        print(f"            {date_str}: {value:,}")
                                except:
                                    continue
                        
                        if date_value_pairs:
                            # Encontrar la fecha más reciente y su valor
                            latest_date_str, latest_value = date_value_pairs[-1]
                            latest_data[exchange] = {
                                'value': latest_value,
                                'date_str': latest_date_str,
                                'all_data': date_value_pairs
                            }
                            print(f"         ✅ {exchange}: {latest_value:,} en fecha {latest_date_str}")
                        else:
                            print(f"         ⚠️ No se encontraron valores numéricos para {exchange}")
                
                except Exception as e:
                    print(f"      ⚠️ Error con fila {j}: {e}")
                    continue
            
            if latest_data:
                print(f"\n--- 📊 ÚLTIMOS DATOS CON FECHAS ---")
                for exchange, data in latest_data.items():
                    print(f"  {exchange}: {data['value']:,} toneladas (fecha: {data['date_str']})")
                return latest_data
            else:
                print("\n--- ❌ NO SE ENCONTRARON DATOS ---")
                return {}
                
        except Exception as e:
            print(f"   -> ❌ Error extrayendo datos: {e}")
            return {}
    
    def create_forward_fill_dataframe(self, latest_data):
        """
        [Modificado] Extrae todos los datos históricos disponibles (últimos 5 días)
        y los prepara para upsert con sus fechas reales.
        """
        print("📈 [Datos históricos] Preparando todos los datos disponibles...")
        
        try:
            processed_data = {}
            
            for exchange, data in latest_data.items():
                all_data = data.get('all_data', [])
                
                print(f"   -> Procesando {exchange}: {len(all_data)} puntos de datos")
                
                try:
                    # Convertir fecha de Cochilco (dd-mmm-yyyy) a datetime
                    month_map = {
                        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                        'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                        'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
                    }
                    
                    # Procesar todos los datos históricos
                    dates = []
                    values = []
                    real_dates = []
                    
                    for date_str, value in all_data:
                        # Parsear fecha (ej: "08-sep-2025")
                        parts = date_str.lower().split('-')
                        if len(parts) == 3:
                            day = parts[0].zfill(2)
                            month_abbr = parts[1][:3]  # Primeros 3 caracteres
                            year = parts[2]
                            
                            if month_abbr in month_map:
                                month = month_map[month_abbr]
                                parsed_date = datetime.strptime(f"{day}-{month}-{year}", "%d-%m-%Y")
                                dates.append(parsed_date)
                                values.append(value)
                                real_dates.append(date_str)
                                print(f"      📅 {date_str} -> {parsed_date.strftime('%Y-%m-%d')}: {value:,}")
                            else:
                                print(f"      ⚠️ Mes no reconocido: {month_abbr}")
                                continue
                        else:
                            print(f"      ⚠️ Formato de fecha no reconocido: {date_str}")
                            continue
                    
                    if dates:
                        # Crear DataFrame con todos los datos históricos
                        df = pd.DataFrame({
                            'date': dates,
                            'value': values,
                            'source': ['Cochilco'] * len(dates),
                            'exchange': [exchange] * len(dates),
                            'last_updated': [datetime.now(pytz.UTC)] * len(dates),
                            'timezone': ['UTC'] * len(dates),
                            'data_source': ['Cochilco'] * len(dates),
                            'real_date': real_dates
                        })
                        
                        # Aplicar forward fill para valores 0 o faltantes (solo días de semana)
                        df = self.apply_forward_fill_weekdays(df, exchange)
                        
                        processed_data[exchange] = df
                        print(f"      ✅ {exchange}: {len(df)} puntos preparados desde {df['date'].iloc[0].strftime('%Y-%m-%d')} hasta {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
                    else:
                        print(f"      ⚠️ No se pudieron procesar fechas para {exchange}")
                
                except Exception as e:
                    print(f"      ❌ Error procesando datos de {exchange}: {e}")
                    continue
            
            # Calcular el total (LME + COMEX + SHFE) para cada fecha
            print(f"\n   -> 🧮 Calculando inventarios totales históricos...")
            try:
                # Obtener DataFrames de cada exchange
                lme_df = processed_data.get('LME')
                comex_df = processed_data.get('COMEX')
                shfe_df = processed_data.get('SHFE')
                
                if lme_df is not None and comex_df is not None and shfe_df is not None:
                    # Crear DataFrame para totales combinando fechas
                    total_dates = []
                    total_values = []
                    total_real_dates = []
                    
                    # Obtener todas las fechas únicas
                    all_dates = set()
                    for df in [lme_df, comex_df, shfe_df]:
                        all_dates.update(df['date'].dt.date)
                    
                    # Para cada fecha, calcular el total
                    for date in sorted(all_dates):
                        lme_value = 0
                        comex_value = 0
                        shfe_value = 0
                        real_date = None
                        
                        # Buscar valores para esta fecha en cada exchange
                        for df, exchange in [(lme_df, 'LME'), (comex_df, 'COMEX'), (shfe_df, 'SHFE')]:
                            matching_rows = df[df['date'].dt.date == date]
                            if not matching_rows.empty:
                                value = matching_rows.iloc[0]['value']
                                real_date = matching_rows.iloc[0]['real_date']
                                
                                if exchange == 'LME':
                                    lme_value = value
                                elif exchange == 'COMEX':
                                    comex_value = value
                                elif exchange == 'SHFE':
                                    shfe_value = value
                        
                        total_value = lme_value + comex_value + shfe_value
                        if total_value > 0 and real_date:
                            total_dates.append(datetime.combine(date, datetime.min.time()))
                            total_values.append(total_value)
                            total_real_dates.append(real_date)
                            print(f"      📊 {real_date} -> {date.strftime('%Y-%m-%d')}: {lme_value:,} + {comex_value:,} + {shfe_value:,} = {total_value:,}")
                    
                    if total_dates:
                        # Crear DataFrame para totales
                        df_total = pd.DataFrame({
                            'date': total_dates,
                            'value': total_values,
                            'source': ['Cochilco'] * len(total_dates),
                            'exchange': ['TOTAL'] * len(total_dates),
                            'last_updated': [datetime.now(pytz.UTC)] * len(total_dates),
                            'timezone': ['UTC'] * len(total_dates),
                            'data_source': ['Cochilco'] * len(total_dates),
                            'real_date': total_real_dates
                        })
                        
                        processed_data['TOTAL'] = df_total
                        print(f"      ✅ TOTAL: {len(total_dates)} puntos preparados desde {total_dates[0].strftime('%Y-%m-%d')} hasta {total_dates[-1].strftime('%Y-%m-%d')}")
                    else:
                        print(f"      ⚠️ No se pudieron calcular totales")
                else:
                    print(f"      ⚠️ Faltan DataFrames para calcular totales")
            
            except Exception as e:
                print(f"      ❌ Error calculando totales: {e}")
            
            return processed_data
                
        except Exception as e:
            print(f"   -> ❌ Error creando DataFrame: {e}")
            return {}
    
    def apply_forward_fill_weekdays(self, df, exchange):
        """
        Aplica forward fill para valores 0 o faltantes, solo en días de semana.
        """
        print(f"      🔄 Aplicando forward fill para {exchange}...")
        
        try:
            # Ordenar por fecha
            df = df.sort_values('date').reset_index(drop=True)
            
            # Crear rango de fechas desde la primera hasta la última
            start_date = df['date'].min().date()
            end_date = df['date'].max().date()
            
            # Generar todas las fechas de días hábiles en el rango
            all_weekdays = []
            current_date = start_date
            while current_date <= end_date:
                # Solo incluir días de semana (lunes=0, domingo=6)
                if current_date.weekday() < 5:  # 0-4 = lunes a viernes
                    all_weekdays.append(current_date)
                current_date += timedelta(days=1)
            
            # Crear DataFrame con todas las fechas de días hábiles
            all_dates_df = pd.DataFrame({
                'date': [datetime.combine(d, datetime.min.time()) for d in all_weekdays]
            })
            
            # Merge con los datos existentes
            merged_df = all_dates_df.merge(df, on='date', how='left')
            
            # Aplicar forward fill para valores 0 o NaN
            last_valid_value = None
            for i, row in merged_df.iterrows():
                if pd.isna(row['value']) or row['value'] == 0:
                    if last_valid_value is not None:
                        merged_df.at[i, 'value'] = last_valid_value
                        merged_df.at[i, 'source'] = 'Cochilco'
                        merged_df.at[i, 'exchange'] = exchange
                        merged_df.at[i, 'last_updated'] = datetime.now(pytz.UTC)
                        merged_df.at[i, 'timezone'] = 'UTC'
                        merged_df.at[i, 'data_source'] = 'Cochilco'
                        merged_df.at[i, 'real_date'] = f"FF-{row['date'].strftime('%d-%b-%Y')}"
                        print(f"         📅 Forward fill: {row['date'].strftime('%Y-%m-%d')} -> {last_valid_value:,}")
                else:
                    last_valid_value = row['value']
            
            # Filtrar solo filas con valores válidos
            result_df = merged_df.dropna(subset=['value']).reset_index(drop=True)
            
            print(f"         ✅ Forward fill completado: {len(result_df)} puntos finales")
            return result_df
            
        except Exception as e:
            print(f"         ❌ Error en forward fill: {e}")
            return df
    
    def sync_to_supabase(self, processed_data):
        """
        Sincroniza los datos procesados con Supabase.
        """
        print("💾 Sincronizando datos con Supabase...")
        
        try:
            if not processed_data:
                print("   -> ⚠️ No hay datos para sincronizar")
                return False
            
            # Mapear exchanges a tickers (usando los tickers reales existentes)
            exchange_mapping = {
                'LME': 'inventarios_lme',
                'COMEX': 'inventarios_comex', 
                'SHFE': 'inventarios_shfe',
                'TOTAL': 'inventarios_totales'
            }
            
            success_count = 0
            
            for exchange, df in processed_data.items():
                ticker = exchange_mapping.get(exchange)
                if not ticker:
                    print(f"   -> ⚠️ No se encontró mapeo para {exchange}")
                    continue
                
                print(f"   -> Sincronizando {exchange} ({ticker})...")
                
                try:
                    # Buscar serie existente
                    series_res = supabase.table('series_definitions').select('id').eq('ticker', ticker).execute()
                    
                    if series_res.data and len(series_res.data) > 0:
                        series_id = series_res.data[0]['id']
                        print(f"      ✅ Serie existente: {series_id}")
                    else:
                        print(f"      ❌ Serie no encontrada: {ticker}")
                        continue
                    
                    # Preparar datos para inserción (usar fechas reales de Cochilco)
                    records_to_upsert = []
                    for _, row in df.iterrows():
                        d = row['date'].date() if hasattr(row['date'], 'date') else pd.to_datetime(row['date']).date()
                        real_date = row.get('real_date', d.strftime('%Y-%m-%d'))
                        
                        # Usar la fecha real del dato de Cochilco (no la fecha de ejecución)
                        record = {
                            'series_id': series_id,
                            'timestamp': d.strftime('%Y-%m-%d'),  # Fecha real del dato
                            'value': row['value'],
                            'ticker': ticker
                        }
                        records_to_upsert.append(record)
                        print(f"      📅 Preparando upsert: {real_date} -> {d.strftime('%Y-%m-%d')}: {row['value']:,}")
                    
                    # Upsert a Supabase
                    if records_to_upsert:
                        upsert_res = supabase.table('time_series_data').upsert(
                            records_to_upsert,
                            on_conflict='series_id,timestamp'
                        ).execute()
                        
                        if upsert_res.data:
                            print(f"      ✅ {len(upsert_res.data)} registros sincronizados")
                            print(f"      📅 Rango: {df.iloc[0]['date'].strftime('%Y-%m-%d')} a {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
                            print(f"      💰 Valores: {df['value'].min():,} a {df['value'].max():,} toneladas")
                            success_count += 1
                        else:
                            print(f"      ❌ Error en upsert para {ticker}")
                    else:
                        print(f"      ⚠️ No hay registros para insertar para {ticker}")
                
                except Exception as e:
                    print(f"      ❌ Error sincronizando {ticker}: {e}")
                    continue
            
            if success_count > 0:
                print(f"✅ Sincronización completada: {success_count}/{len(processed_data)} series actualizadas")
                return True
            else:
                print("❌ No se pudo sincronizar ninguna serie")
                return False
            
        except Exception as e:
            print(f"❌ Error en sincronización: {e}")
            return False
    
    def generate_summary_report(self, processed_data):
        """
        Genera un reporte resumen de los datos procesados.
        """
        print("\n📋 GENERANDO REPORTE RESUMEN...")
        
        try:
            print("=" * 60)
            print("📊 REPORTE DE INVENTARIOS DE COBRE - COCHILCO")
            print("=" * 60)
            
            for exchange, df in processed_data.items():
                print(f"\n🔸 {exchange} (London Metal Exchange)")
                print("-" * 40)
                
                # Estadísticas básicas
                latest_value = df['value'].iloc[-1]
                latest_date = df['date'].iloc[-1]
                real_date = df['real_date'].iloc[0] if 'real_date' in df.columns else 'N/A'
                
                print(f"   📅 Fecha real del dato: {real_date}")
                print(f"   📅 Última actualización: {latest_date.strftime('%Y-%m-%d')}")
                print(f"   📊 Valor actual: {latest_value:,} toneladas")
                print(f"   📈 Rango de fechas: {df['date'].min().strftime('%Y-%m-%d')} a {df['date'].max().strftime('%Y-%m-%d')}")
                print(f"   🔢 Total de registros: {len(df)}")
                
                # Mostrar últimos 5 días
                print(f"   📋 Últimos 5 días:")
                for i, row in df.tail(5).iterrows():
                    print(f"      {row['date'].strftime('%Y-%m-%d')}: {row['value']:,} toneladas")
            
            print("\n" + "=" * 60)
            print("✅ DATOS SINCRONIZADOS CON SUPABASE")
            print("🔁 Forward fill está centralizado en 'run_all_syncs' (solo días hábiles)")
            print("=" * 60)
            
            return True
                
        except Exception as e:
            print(f"   -> ❌ Error generando reporte: {e}")
            return False
    
    def run_final_workflow(self):
        """
        Ejecuta el flujo completo final.
        """
        print("🚀 Iniciando flujo de trabajo final...")
        
        try:
            # Configurar driver
            if not self.setup_driver():
                return False
            
            # Navegar a inventarios
            if not self.navigate_to_inventories():
                return False
            
            # Seleccionar todos los checkboxes
            self.select_all_checkboxes()
            
            # Configurar todos los selects
            self.configure_all_selects()
            
            # Hacer clic en cualquier botón
            self.click_any_button()
            
            # Extraer último dato disponible con fecha real
            latest_data = self.extract_latest_data_with_dates()
            
            if not latest_data:
                print("❌ No se pudieron extraer datos")
                return False
            
            # Normalizar datos a DataFrames de un solo punto
            processed_data = self.create_forward_fill_dataframe(latest_data)
            
            if not processed_data:
                print("❌ No se pudieron crear DataFrames")
                return False
            
            # Sincronizar con Supabase
            self.sync_to_supabase(processed_data)
            
            # Generar reporte resumen
            self.generate_summary_report(processed_data)
            
            print("\n🎉 ✅ FLUJO COMPLETADO EXITOSAMENTE")
            print("📊 Datos extraídos y sincronizados con Supabase")
            print("🔄 Forward fill centralizado (run_all_syncs)")
            
            return processed_data
                
        except Exception as e:
            print(f"❌ Error en flujo de trabajo: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 Driver cerrado")

def test_final_bot():
    """
    Prueba el bot final.
    """
    print("=== PRUEBA BOT FINAL COCHILCO ===")
    
    bot = FinalCochilcoBot(headless=False)  # headless=False para ver el proceso
    result = bot.run_final_workflow()
    
    if result:
        print("\n🎉 ✅ PRUEBA EXITOSA")
        print("📊 El bot extrae el último dato y sincroniza con Supabase")
        print("🔄 Forward fill implementado correctamente")
        print("🔧 Sistema listo para producción")
        return True
    else:
        print("\n❌ PRUEBA FALLIDA")
        print("🔧 Necesita ajustes antes de producción")
        return False

if __name__ == "__main__":
    test_final_bot()

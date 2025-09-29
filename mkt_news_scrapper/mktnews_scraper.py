import os
import sys
import time
import json
import atexit
import socket
import subprocess
import urllib.request
from datetime import datetime

# Windows console unicode safety
try:
	if os.name == 'nt':
		import codecs
		sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
		sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
except Exception:
	pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MKTPAGE_URL = "https://mktnews.net/index.html"
DEBUGGER_ADDRESS = "127.0.0.1:9222"
CHROME_PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")
# Unificar carpeta de exportación con ingest_from_md.py (misma carpeta del script)
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")

_driver = None


def _is_port_open(host: str, port: int) -> bool:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.settimeout(0.3)
		try:
			return sock.connect_ex((host, port)) == 0
		except Exception:
			return False


def _fetch_cdp_version() -> dict:
	try:
		with urllib.request.urlopen(f"http://{DEBUGGER_ADDRESS}/json/version", timeout=0.8) as resp:
			return json.loads(resp.read().decode('utf-8'))
	except Exception:
		return {}


def _find_chrome_path() -> str:
	candidates = [
		os.environ.get('CHROME_PATH', ''),
		"C:/Program Files/Google/Chrome/Application/chrome.exe",
		"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
		os.path.expandvars(r"%LocalAppData%/Google/Chrome/Application/chrome.exe"),
	]
	for path in candidates:
		if path and os.path.exists(path):
			return path
	return "chrome"


def _ensure_chrome_running() -> None:
	if not os.path.exists(CHROME_PROFILE_DIR):
		os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)

	if _is_port_open("127.0.0.1", 9222):
		return

	chrome_path = _find_chrome_path()
	args = [
		chrome_path,
		"--remote-debugging-port=9222",
		f"--user-data-dir={CHROME_PROFILE_DIR}",
		"--disable-background-timer-throttling",
		"--disable-backgrounding-occluded-windows",
		"--disable-renderer-backgrounding",
		"--no-first-run",
		"--no-default-browser-check",
	]
	# Start Chrome detached; do not wait; keep running if script exits
	creationflags = 0
	startupinfo = None
	if os.name == 'nt':
		creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
	try:
		subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags)
		# Give Chrome a moment to start DevTools
		for _ in range(30):
			if _is_port_open("127.0.0.1", 9222):
				break
			time.sleep(0.2)
	except Exception as e:
		print(f"No se pudo lanzar Chrome: {e}")


def get_persistent_driver() -> webdriver.Chrome:
	global _driver
	if _driver is not None:
		return _driver

	_ensure_chrome_running()
	cdp_info = _fetch_cdp_version()
	if cdp_info:
		print(f"CDP activo: {cdp_info.get('Browser','')} @ {cdp_info.get('webSocketDebuggerUrl','')[:60]}...")

	options = Options()
	options.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
	# Important: Do NOT set headless; we want visible browser

	# Let Selenium Manager resolve chromedriver automatically
	_driver = webdriver.Chrome(options=options)

	# Never close the browser automatically
	def _do_not_quit():
		try:
			# Intentionally avoid driver.quit(); keep Chrome open
			pass
		except Exception:
			pass
	atexit.register(_do_not_quit)
	return _driver


def initialize_page(driver: webdriver.Chrome) -> None:
	driver.get(MKTPAGE_URL)
	wait = WebDriverWait(driver, 15)
	# Try to click "Important Only" once if present
	try:
		important_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//main//button[contains(., 'Important') or contains(., 'Important Only') or contains(., 'Importante')]")))
		important_button.click()
		time.sleep(1.5)
	except Exception:
		pass
def _refresh_feed(driver: webdriver.Chrome) -> None:
	"""Force a fresh load with cache-busting to get most recent items."""
	try:
		cache_bust = int(time.time())
		driver.get(f"{MKTPAGE_URL}?t={cache_bust}")
		WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//main")))
		time.sleep(0.8)
	except Exception:
		pass



def _visible_human_scroll(driver: webdriver.Chrome, total_steps: int = 12, step_px: int = 600, pause_s: float = 0.35) -> None:
	for _ in range(total_steps):
		driver.execute_script("window.scrollBy(0, arguments[0]);", step_px)
		time.sleep(pause_s)
	# small bounce to trigger lazy-load observers
	driver.execute_script("window.scrollBy(0, -200);")
	time.sleep(0.5)

def _go_to_top_and_render(driver: webdriver.Chrome) -> None:
	"""Vuelve al tope y fuerza un pequeño render del primer viewport."""
	try:
		driver.execute_script("window.scrollTo(0, 0);")
		time.sleep(0.4)
		for _ in range(3):
			driver.execute_script("window.scrollBy(0, 200);"); time.sleep(0.15)
			driver.execute_script("window.scrollBy(0, -200);"); time.sleep(0.15)
	except Exception:
		pass


def extract_visible_news(driver: webdriver.Chrome, max_items: int = 50) -> list:
	# Focus only within <main> area; ignore sidebars and chat
	news_items = []
	try:
		main = driver.find_element(By.XPATH, "//main")
		# Selector más robusto: combinamos XPATH y CSS y normalizamos el OR
		cards = main.find_elements(By.XPATH, 
			".//div[((contains(@class,'flash') and contains(@class,'item')) or contains(@class,'news')) and not(ancestor::*[contains(@class,'chat') or contains(@id,'chat')])]")
		if len(cards) == 0:
			# Fallback CSS
			cards = main.find_elements(By.CSS_SELECTOR, "div.flash.item, div.news, article.news, li.news")
		# Scroll incremental hasta reunir ~max_items
		steps = 0
		while len(cards) < max_items and steps < 20:
			try:
				driver.execute_script("window.scrollBy(0, 700);")
			except Exception:
				break
			time.sleep(0.25)
			try:
				main = driver.find_element(By.XPATH, "//main")
				cards = main.find_elements(By.XPATH, 
					".//div[((contains(@class,'flash') and contains(@class,'item')) or contains(@class,'news')) and not(ancestor::*[contains(@class,'chat') or contains(@id,'chat')])]")
			except Exception:
				pass
			steps += 1
		print(f"[dbg] tarjetas detectadas: {len(cards)} (objetivo {max_items})")
		# Si no se extrae nada más adelante, guardaremos outerHTML de las primeras
		debug_cards = cards[:2]
		last_seen_time = ""
		# Fecha simple (local)
		site_today = datetime.now().date()
		for card in cards:
			try:
				timestamp_el = None
				title_el = None
				content_el = None
				badge_els = []
				# Common patterns observed
				title_el = next((el for el in card.find_elements(By.XPATH, ".//div[contains(@class,'flash-title')][normalize-space()]")), None) or \
					   next((el for el in card.find_elements(By.XPATH, ".//*[self::h1 or self::h2 or self::h3 or contains(@class,'title') or contains(@class,'headline')][normalize-space()]")), None)
				content_el = next((el for el in card.find_elements(By.XPATH, ".//div[contains(@class,'flash-content')][normalize-space()]")), None) or \
						   next((el for el in card.find_elements(By.XPATH, ".//*[contains(@class,'content') or contains(@class,'body') or contains(@class,'desc') or self::p][normalize-space()]")), None)
				# Hora (best effort)
				timestamp_el = next((el for el in card.find_elements(By.XPATH, ".//span[normalize-space()][1]")), None)
				title_text = title_el.text.strip() if title_el else ''
				content_text = content_el.text.strip() if content_el else ''
				ts_text = timestamp_el.text.strip() if timestamp_el else ''
				if not ts_text:
					try:
						parent = card.find_element(By.XPATH, "..")
						children = parent.find_elements(By.XPATH, "./*")
						idx = children.index(card)
						if idx > 0:
							left_text = children[idx-1].text.strip()
							if ":" in left_text:
								parts = left_text.split()
								for token in parts:
									if token.count(":") >= 1 and 4 <= len(token) <= 8:
										ts_text = token
										break
					except Exception:
						pass
				# Collect small badges/labels if any
				try:
					badge_els = card.find_elements(By.XPATH, ".//*[contains(@class,'badge') or contains(@class,'tag') or contains(@class,'label')][normalize-space()]")
					badges = [b.text.strip() for b in badge_els if b.text and b.text.strip()]
				except Exception:
					badges = []
				if not title_text and content_text:
					title_text = content_text.split(". ")[0][:120]
				# Fallback fuerte
				if not title_text and not content_text:
					try:
						raw_txt = card.get_attribute('innerText') or card.text or ''
						raw_txt = raw_txt.replace('\r','\n')
						lines = [ln.strip() for ln in raw_txt.split('\n') if ln and ln.strip()]
						import re
						filtered = []
						for ln in lines:
							if re.match(r"^\d{2}:\d{2}(?::\d{2})?$", ln):
								continue
							filtered.append(ln)
						if filtered:
							title_text = filtered[0][:120]
							content_text = ' '.join(filtered[1:])[:500]
					except Exception:
						pass
				if title_text or content_text:
					news_items.append({
						"title": title_text,
						"content": content_text,
						"timestamp": ts_text,
						"tags": badges
					})
			except Exception:
				continue
	except Exception:
		pass
	# Si a pesar de detectar tarjetas no logramos noticias, volcar outerHTML de muestra
	try:
		if not news_items:
			os.makedirs(EXPORTS_DIR, exist_ok=True)
			for idx, c in enumerate(debug_cards, 1):
				try:
					outer = c.get_attribute('outerHTML') or ''
					with open(os.path.join(EXPORTS_DIR, f"debug_card_{idx}.html"), 'w', encoding='utf-8') as f:
						f.write(outer)
				except Exception:
					pass
	except Exception:
		pass
	# Respetar orden DOM y limitar a max_items
	return news_items[:max_items]


def scrape_once(driver: webdriver.Chrome) -> list:
	# Always refresh feed to get latest items (cache-busting) y re-aplicar filtro
	_refresh_feed(driver)
	initialize_page(driver)  # Reaplica "Important Only" tras reload
	_go_to_top_and_render(driver)
	# Precargado fuerte para disparar lazy-load cerca del tope
	_visible_human_scroll(driver, total_steps=16, step_px=800, pause_s=0.28)
	_go_to_top_and_render(driver)
	items = extract_visible_news(driver, max_items=50)
	print(f"Encontradas {len(items)} noticias visibles.")
	# Retry once if nothing found: reinitialize page and scroll again
	if len(items) == 0:
		try:
			print("Nada encontrado. Reintentando: recargando página...")
			initialize_page(driver)
			_go_to_top_and_render(driver)
			_visible_human_scroll(driver, total_steps=16, step_px=800, pause_s=0.28)
			_go_to_top_and_render(driver)
			items = extract_visible_news(driver, max_items=50)
			print(f"Segundo intento: {len(items)} noticias visibles.")
		except Exception:
			pass
	for i, it in enumerate(items[:15], 1):
		title_preview = it.get('title') or (it.get('content')[:120] if it.get('content') else '')
		print(f"[{i}] {title_preview}")
		if it.get('content'):
			print(f"    — {it.get('content')}")
		if it.get('timestamp'):
			print(f"    [{it.get('timestamp')}]")
		if it.get('tags'):
			print(f"    tags: {', '.join(it.get('tags'))}")
	return items


def save_markdown(items: list) -> str:
	"""Save top 15 items to Markdown and return file path."""
	try:
		os.makedirs(EXPORTS_DIR, exist_ok=True)
		stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		filename = os.path.join(EXPORTS_DIR, f"mktnews_{stamp}.md")
		latest = os.path.join(EXPORTS_DIR, "mktnews_latest.md")

		lines = []
		lines.append(f"# MktNews scrape {stamp}")
		lines.append("")
		lines.append(f"Fuente: {MKTPAGE_URL}")
		lines.append("")
		for i, it in enumerate(items, 1):
			title = it.get('title') or ''
			content = it.get('content') or ''
			ts = it.get('timestamp') or ''
			lines.append(f"## {i}. {title if title else (content[:80] if content else 'Sin título')}")
			if ts:
				lines.append(f"- Time: `{ts}`")
			if it.get('tags'):
				lines.append(f"- Tags: {', '.join(it.get('tags'))}")
			if content:
				lines.append("")
				lines.append(content)
			lines.append("")

		md = "\n".join(lines)
		with open(filename, 'w', encoding='utf-8') as f:
			f.write(md)
		with open(latest, 'w', encoding='utf-8') as f:
			f.write(md)
		print(f"Guardado Markdown: {filename}")
		print(f"Actualizado: {latest}")
		return filename
	except Exception as e:
		print(f"No se pudo guardar Markdown: {e}")
		return ""


def ingest_markdown_if_available():
	"""Trigger ingestion step after saving markdown, ignoring errors."""
	try:
		from ingest_from_md import ingest_latest_md
		ingest_latest_md()
	except Exception as e:
		print(f"No se pudo ejecutar la ingesta automática: {e}")


def main() -> None:
	driver = get_persistent_driver()
	if driver.current_url == 'data:,' or driver.current_url == 'about:blank':
		initialize_page(driver)
	else:
		try:
			# If not on mktnews, navigate there once
			if 'mktnews' not in driver.current_url:
				driver.get(MKTPAGE_URL)
			time.sleep(1)
		except Exception:
			initialize_page(driver)

	print("--- Navegador listo. La ventana quedará abierta SIEMPRE. ---")
	print("Presiona Enter para hacer un nuevo scrape. Ctrl+C para detener el script (el navegador seguirá abierto).")

	# First scrape immediately
	scrape_once(driver)

	while True:
		try:
			user_input = input("\n¿Hacer otro scrape? [Enter = sí / q = salir]: ").strip().lower()
			if user_input in ("q", "quit", "salir", "n", "no", "exit"):
				print("Saliendo del loop. El navegador permanece abierto.")
				break
			print("Iniciando nuevo scrape...", flush=True)
			items = scrape_once(driver)
			md_path = save_markdown(items)
			if md_path:
				print("Ejecutando ingesta al grafo (evita duplicados)...")
				ingest_markdown_if_available()
		except KeyboardInterrupt:
			print("Script detenido por el usuario. El navegador permanece abierto.")
			break
		except Exception as e:
			print(f"Error en loop de scraping: {e}")
			time.sleep(1)


if __name__ == "__main__":
	main()

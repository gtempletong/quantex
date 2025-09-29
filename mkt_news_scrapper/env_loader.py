import os
from pathlib import Path

def load_env_with_fallback() -> None:
	"""Load .env from current project, then fallback to C:\\Quantex\\.env if keys are missing."""
	try:
		from dotenv import load_dotenv
	except Exception:
		return

	project_env = Path(__file__).with_name('.env')
	quantex_env = Path('C:/Quantex/.env')

	# Load local first
	if project_env.exists():
		load_dotenv(project_env, override=False)

	# Fallback: load Quantex .env only for missing keys (override=False keeps existing)
	if quantex_env.exists():
		load_dotenv(quantex_env, override=False)

	# Minimal sanity aliasing
	if not os.getenv('SUPABASE_URL'):
		os.environ['SUPABASE_URL'] = os.getenv('QUANTEX_SUPABASE_URL', '') or os.getenv('SUPABASE_URL', '')

	# Use Quantex naming exactly: SUPABASE_SERVICE_KEY
	if not os.getenv('SUPABASE_SERVICE_KEY'):
		alias = (
			os.getenv('SUPABASE_SERVICE_KEY')
			or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
			or os.getenv('SUPABASE_ANON_KEY')
			or os.getenv('SUPABASE_KEY')
		)
		if alias:
			os.environ['SUPABASE_SERVICE_KEY'] = alias



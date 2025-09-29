import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from quantex.config import Config

# --- 1. Cargar Credenciales de forma segura ---
# Asegúrate de que tu archivo .env está en la raíz del proyecto
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

BC_USER = os.getenv("BC_USER")
BC_PASSWORD = os.getenv("BC_PASSWORD")

if not all([BC_USER, BC_PASSWORD]):
    print("❌ ERROR: Las credenciales del Banco Central (BC_USER, BC_PASSWORD) no están en el archivo .env")
else:
    print("✅ Credenciales del Banco Central cargadas.")

# --- 2. Función para consultar la API ---
def get_bcentral_series(serie_id: str, start_date: str, end_date: str):
    """
    Obtiene los datos para una serie específica del Banco Central de Chile.
    """
    # ✅ SEGURO: Obtener URL desde configuración
    api_url = f"{Config.get_bcch_url()}/{serie_id}/observations"

    # Parámetros para la petición, incluyendo autenticación
    params = {
        'user': BC_USER,
        'pass': BC_PASSWORD,
        'firstdate': start_date,
        'lastdate': end_date
    }

    print(f"🔎 Consultando la serie '{serie_id}' a la API del BCCh...")

    try:
        # Realizar la petición GET
        response = requests.get(api_url, params=params)

        # Verificar si la petición fue exitosa (código 200)
        if response.status_code == 200:
            print("   -> ✅ Petición exitosa.")
            # Convertir la respuesta a JSON
            data = response.json()
            return data.get('series', [{}])[0].get('obs', [])
        else:
            print(f"   -> ❌ Error en la petición: Código {response.status_code}")
            print(f"      Respuesta: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ Error de conexión: {e}")
        return None

# --- 3. Ejecución de Ejemplo ---
if __name__ == "__main__":
    # Definir la serie y el rango de fechas que nos interesa
    serie_dolar = "F073.TCO.PRE.Z.D"
    fecha_hoy = datetime.now()
    fecha_inicio = (fecha_hoy - timedelta(days=7)).strftime('%Y-%m-%d') # Últimos 7 días
    fecha_fin = fecha_hoy.strftime('%Y-%m-%d')

    # Obtener los datos
    observaciones = get_bcentral_series(serie_dolar, fecha_inicio, fecha_fin)

    # Procesar y mostrar el último dato
    if observaciones:
        ultimo_dato = observaciones[-1]
        fecha = ultimo_dato[0]
        valor = ultimo_dato[1]
        print(f"\n📈 Último dato para el Dólar Observado ({serie_dolar}):")
        print(f"   -> Fecha: {fecha}")
        print(f"   -> Valor: ${valor}")
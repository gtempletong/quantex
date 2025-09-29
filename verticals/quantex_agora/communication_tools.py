# quantex/core/communication_tools.py

import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv

# --- Configuración de la API de Brevo ---
configuration = sib_api_v3_sdk.Configuration()
# La clave se carga desde las variables de entorno más adelante

def send_email(subject: str, html_content: str, recipient_email: str, recipient_name: str) -> bool:
    """
    Envía un email usando la API de Brevo.
    Devuelve True si el envío fue exitoso, False si no.
    """
    # La clave de API se carga aquí para asegurar que .env ha sido leído por el script principal
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # --- Estructura del Email ---
    sender = {"name": "Quantex by Gavin", "email": "gavin.templeton@gavintempleton.net"} # Reemplazar con tu email de remitente verificado en Brevo
    to = [{"email": recipient_email, "name": recipient_name}]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    # --- Envío ---
    try:
        print(f"⏳ Enviando email a: {recipient_email}...")
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"✅ Email enviado exitosamente. Message ID: {api_response.message_id}")
        return True
    except ApiException as e:
        print(f"❌ Error al enviar email a través de Brevo: {e}")
        return False

# --- Bloque de Prueba Directa ---
# Este código solo se ejecuta cuando corremos "python quantex/core/communication_tools.py"
if __name__ == '__main__':
    # Cargamos las variables de entorno para la prueba
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    print("--- 🧪 Iniciando prueba directa de 'communication_tools.py' ---")
    
    # Reemplaza con tu propio email para recibir el correo de prueba
    test_recipient = "gavintempleton@gavintempleton.net" 
    
    test_subject = "Prueba de Envío desde Quantex"
    test_html = """
    <h1>¡Hola!</h1>
    <p>Este es un correo de prueba para la nueva herramienta de comunicación de Quantex.</p>
    <p>Si recibes esto, la conexión con Brevo funciona correctamente.</p>
    """

    if not os.getenv("BREVO_API_KEY"):
        print("❌ No se encontró la BREVO_API_KEY en el archivo .env. Abortando prueba.")
    else:
        send_email(test_subject, test_html, test_recipient, "Gavin de Prueba")
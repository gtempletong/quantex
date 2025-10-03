# C:\Quantex\app.py

import os
import sys
import logging

# Forzar salida inmediata de prints en consola (útil en Windows/Flask)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass

# Asegurar logs de requests del servidor de desarrollo y enrutar todo a stdout
logging.getLogger('werkzeug').setLevel(logging.INFO)
_root_logger = logging.getLogger()
if not _root_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    _root_logger.addHandler(_handler)
_root_logger.setLevel(logging.INFO)

# Esta es la forma estándar en Python de ejecutar código solo cuando
# el archivo se corre directamente (y no cuando es importado).
if __name__ == '__main__':
    # Usamos las variables de entorno para el puerto y el modo debug si existen,
    # con valores por defecto si no.
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    
    print(f"🚀 Iniciando servidor Quantex en el puerto {port} en modo debug={'ON' if debug_mode else 'OFF'}...")
    
    # Importación perezosa para respetar el orden de configuración y evitar stdout capturado
    from quantex.api.server import create_app

    # Creamos la instancia de la aplicación llamando a nuestra función de fábrica
    app = create_app()

    # Ejecutamos la aplicación
    # Desactivar el reloader para que los prints de las requests aparezcan en esta misma terminal
    app.run(debug=debug_mode, port=port, host='0.0.0.0', use_reloader=False)
# C:\Quantex\app.py

import os
from quantex.api.server import create_app

# Creamos la instancia de la aplicación llamando a nuestra función de fábrica
app = create_app()

# Esta es la forma estándar en Python de ejecutar código solo cuando
# el archivo se corre directamente (y no cuando es importado).
if __name__ == '__main__':
    # Usamos las variables de entorno para el puerto y el modo debug si existen,
    # con valores por defecto si no.
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    
    print(f"🚀 Iniciando servidor Quantex en el puerto {port} en modo debug={'ON' if debug_mode else 'OFF'}...")
    
    # Ejecutamos la aplicación
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
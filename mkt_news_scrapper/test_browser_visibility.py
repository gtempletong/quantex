"""
Script de prueba para verificar que el navegador sea visible
"""

import os
import sys
import time

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(__file__))

from mktnews_scraper import get_persistent_driver, initialize_page

def test_browser_visibility():
    """Prueba que el navegador sea visible"""
    print("🌐 Probando visibilidad del navegador...")
    
    try:
        # Obtener driver
        print("  -> Inicializando driver...")
        driver = get_persistent_driver()
        
        # Verificar que el navegador esté visible
        print("  -> Navegando a MktNews...")
        initialize_page(driver)
        
        print("  -> ✅ Navegador debería ser visible ahora")
        print("  -> 📱 Si puedes ver Chrome abierto con MktNews, la configuración es correcta")
        
        # Esperar un poco para que el usuario pueda ver
        print("  -> ⏳ Esperando 10 segundos para verificación...")
        time.sleep(10)
        
        print("  -> ✅ Prueba completada")
        return True
        
    except Exception as e:
        print(f"  -> ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 PRUEBA DE VISIBILIDAD DEL NAVEGADOR")
    print("=" * 50)
    
    success = test_browser_visibility()
    
    if success:
        print("\n🎉 ¡Navegador configurado correctamente!")
        print("   El navegador debería ser visible cuando ejecutes el scraper.")
    else:
        print("\n⚠️ Hubo un problema con la configuración del navegador.")

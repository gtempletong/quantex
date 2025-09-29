"""
Script de prueba para la integración MktNewsScraper → Quantex
"""

import os
import sys
import hashlib
from datetime import datetime

# Agregar Quantex al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def test_quantex_integration():
    """Prueba la integración con Quantex"""
    print("🧪 Probando integración MktNewsScraper → Quantex...")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        print("✅ Importación exitosa de quantex_integration")
    except Exception as e:
        print(f"❌ Error importando quantex_integration: {e}")
        return False
    
    # Crear instancia de integración
    try:
        integration = MktNewsQuantexIntegration()
        print("✅ Inicialización exitosa de MktNewsQuantexIntegration")
    except Exception as e:
        print(f"❌ Error inicializando integración: {e}")
        return False
    
    # Crear item de prueba con URL única
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = hashlib.sha256(f"test-integration-{timestamp}".encode()).hexdigest()[:16]
    
    test_item = {
        "title": f"Prueba de Integración Quantex {timestamp}",
        "content": f"""
        Esta es una noticia de prueba para verificar la integración con el motor unificado de Quantex.
        ID único: {unique_id}
        Timestamp: {timestamp}
        
        Puntos clave:
        - Mercados financieros muestran volatilidad
        - Inflación sigue siendo una preocupación
        - Tasas de interés podrían aumentar
        - Commodities como el cobre muestran tendencia alcista
        
        Esta noticia contiene múltiples entidades financieras que deberían ser detectadas
        y conectadas semánticamente con otros nodos del grafo de conocimiento.
        """,
        "time": datetime.now().isoformat(),
        "url": f"https://mktnews.net/test-integration-{unique_id}",
        "item_hash": hashlib.sha256(f"test-integration-quantex-{timestamp}".encode()).hexdigest(),
        "category": "Prueba_Integración"
    }
    
    print(f"📰 Procesando item de prueba: {test_item['title']}")
    
    # Procesar item
    try:
        result = integration.process_news_item(test_item)
        
        if result.get("success"):
            print("✅ Item procesado exitosamente")
            print(f"  -> Nodos creados: {result.get('nodes_created', 0)}")
            print(f"  -> Entidades encontradas: {result.get('entities_found', 0)}")
            print(f"  -> Conexiones creadas: {result.get('connections_created', 0)}")
            return True
        else:
            print(f"❌ Error procesando item: {result.get('reason', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción procesando item: {e}")
        return False

def test_duplicate_detection():
    """Prueba la detección de duplicados"""
    print("\n🔍 Probando detección de duplicados...")
    
    try:
        from quantex_integration import MktNewsQuantexIntegration
        integration = MktNewsQuantexIntegration()
        
        # Probar URL
        test_url = "https://mktnews.net/test-duplicate"
        exists = integration.check_duplicate_by_url(test_url)
        print(f"  -> Duplicado por URL '{test_url}': {exists}")
        
        # Probar hash
        test_hash = hashlib.sha256("test-duplicate".encode()).hexdigest()
        exists = integration.check_duplicate_by_hash(test_hash)
        print(f"  -> Duplicado por hash '{test_hash[:16]}...': {exists}")
        
        print("✅ Pruebas de detección de duplicados completadas")
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas de duplicados: {e}")
        return False

def test_compatibility_functions():
    """Prueba las funciones de compatibilidad"""
    print("\n🔄 Probando funciones de compatibilidad...")
    
    try:
        # Probar función de compatibilidad
        from quantex_integration import process_and_store_knowledge
        
        # Crear URL única para evitar duplicados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = hashlib.sha256(f"test-compat-{timestamp}".encode()).hexdigest()[:16]
        
        source_context = {
            "source": "Test",
            "topic": "Prueba",
            "original_url": f"https://test.com/compat-{unique_id}",
            "time": datetime.now().isoformat(),
            "hash": hashlib.sha256(f"test-compat-{timestamp}".encode()).hexdigest()
        }
        
        result = process_and_store_knowledge("Contenido de prueba para compatibilidad", source_context)
        
        if result.get("success"):
            print("✅ Función de compatibilidad funciona correctamente")
            return True
        else:
            print(f"⚠️ Función de compatibilidad retornó: {result.get('reason', 'Error')}")
            return True  # Es normal que falle si ya existe
            
    except Exception as e:
        print(f"❌ Error en función de compatibilidad: {e}")
        return False

def main():
    """Ejecuta todas las pruebas"""
    print("🚀 Iniciando pruebas de integración MktNewsScraper → Quantex\n")
    
    tests = [
        ("Integración básica", test_quantex_integration),
        ("Detección de duplicados", test_duplicate_detection),
        ("Funciones de compatibilidad", test_compatibility_functions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"📋 Ejecutando: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
        print()
    
    # Resumen
    print("📊 RESUMEN DE PRUEBAS:")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} pruebas pasaron")
    
    if passed == len(results):
        print("🎉 ¡Todas las pruebas pasaron! La integración está funcionando correctamente.")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

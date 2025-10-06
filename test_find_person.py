#!/usr/bin/env python3
"""
Test directo de la herramienta supabase.find_person
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio del proyecto al path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Importar directamente la función sin dependencias complejas
import sys
sys.path.append('quantex/core/agents/modular_agent')

def execute_tool(tool_call):
    """Función simplificada para testing"""
    tool = tool_call.get("tool")
    params = tool_call.get("params", {})
    
    if tool == "supabase.find_person":
        return _execute_supabase_find_person(params)
    else:
        return {"ok": False, "error": f"Tool '{tool}' not implemented"}

def _execute_supabase_find_person(params):
    """Ejecuta búsqueda de persona en Supabase con información completa."""
    try:
        search_term = params.get("search_term", "").strip()
        search_type = params.get("search_type", "name")
        only_unsent = params.get("only_unsent", False)
        
        if not search_term:
            return {"ok": False, "error": "search_term vacío"}
        
        # Importar cliente Supabase
        from supabase import create_client, Client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Usar service key para testing
        
        if not supabase_url or not supabase_key:
            return {"ok": False, "error": "Configuración de Supabase no encontrada"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print(f"Buscando persona por {search_type}: '{search_term}' en Supabase...")
        
        # Construir query para obtener información básica de persona
        query = supabase.table('personas').select("""
            id,
            rut_empresa,
            nombre_contacto,
            cargo_contacto,
            email_contacto,
            celular_contacto,
            telefono_contacto,
            email_sent,
            email_sent_at,
            estado,
            tipo_empresa
        """)
        
        # Aplicar filtro de búsqueda según el tipo
        if search_type == "name":
            query = query.ilike('nombre_contacto', f'%{search_term}%')
        elif search_type == "email":
            query = query.ilike('email_contacto', f'%{search_term}%')
        elif search_type == "rut":
            query = query.ilike('rut_empresa', f'%{search_term}%')
        
        # Filtrar solo personas que no han recibido emails si se solicita
        if only_unsent:
            query = query.eq('email_sent', False)
        
        response = query.execute()
        
        if response.data and len(response.data) > 0:
            person_data = response.data[0]
            
            # Buscar información de empresa si existe rut_empresa
            empresa_info = None
            if person_data.get('rut_empresa'):
                try:
                    empresa_response = supabase.table('empresas').select('razon_social, rut_empresa, sitio_web').eq('rut_empresa', person_data['rut_empresa']).execute()
                    if empresa_response.data:
                        empresa_data = empresa_response.data[0]
                        empresa_info = {
                            "razon_social": empresa_data.get('razon_social'),
                            "rut_empresa": empresa_data.get('rut_empresa'),
                            "sitio_web": empresa_data.get('sitio_web')
                        }
                except Exception as e:
                    print(f"Error buscando empresa: {e}")
            
            return {
                "ok": True,
                "found": True,
                "person": {
                    "id": person_data.get("id"),
                    "nombre_contacto": person_data.get("nombre_contacto"),
                    "cargo_contacto": person_data.get("cargo_contacto"),
                    "email_contacto": person_data.get("email_contacto"),
                    "celular_contacto": person_data.get("celular_contacto"),
                    "telefono_contacto": person_data.get("telefono_contacto"),
                    "email_sent": person_data.get("email_sent", False),
                    "email_sent_at": person_data.get("email_sent_at"),
                    "estado": person_data.get("estado"),
                    "tipo_empresa": person_data.get("tipo_empresa"),
                    "empresa": empresa_info
                }
            }
        else:
            return {
                "ok": True,
                "found": False,
                "message": f"No se encontró persona con {search_type} '{search_term}'"
            }
            
    except Exception as e:
        return {"ok": False, "error": f"Error buscando en Supabase: {str(e)}"}

def test_find_person():
    """Prueba la herramienta supabase.find_person"""
    
    print("🔍 Probando herramienta supabase.find_person...")
    print("=" * 50)
    
    # Test 1: Búsqueda por nombre
    print("\n📋 Test 1: Búsqueda por nombre")
    result1 = execute_tool({
        "tool": "supabase.find_person",
        "params": {
            "search_term": "Juan",
            "search_type": "name"
        }
    })
    print(f"Resultado: {result1}")
    
    # Test 2: Búsqueda por email
    print("\n📧 Test 2: Búsqueda por email")
    result2 = execute_tool({
        "tool": "supabase.find_person",
        "params": {
            "search_term": "@",
            "search_type": "email"
        }
    })
    print(f"Resultado: {result2}")
    
    # Test 3: Solo personas que NO han recibido emails
    print("\n🚫 Test 3: Solo personas sin emails enviados")
    result3 = execute_tool({
        "tool": "supabase.find_person",
        "params": {
            "search_term": "a",  # Búsqueda amplia
            "search_type": "name",
            "only_unsent": True
        }
    })
    print(f"Resultado: {result3}")
    
    # Test 4: Búsqueda por RUT
    print("\n🆔 Test 4: Búsqueda por RUT")
    result4 = execute_tool({
        "tool": "supabase.find_person",
        "params": {
            "search_term": "12345678",
            "search_type": "rut"
        }
    })
    print(f"Resultado: {result4}")
    
    print("\n✅ Tests completados!")

if __name__ == "__main__":
    test_find_person()

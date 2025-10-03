#!/usr/bin/env python3

"""
SimpleAgent - Agent minimalista para buscar personas y enviar emails
Un solo archivo, directo al grano
"""

import os
import sys
import json

# Añadir path para importar llm_manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from quantex.core.llm_manager import generate_structured_output

def simular_supabase_query(sql):
    """
    Simula query a Supabase - en producción aquí llamarías tu MCP
    """
    print(f"📊 Supabase Query: {sql[:100]}...")
    
    # Buscar Gavin Templeton (conocido que existe)
    if "gavin" in sql.lower() or "templeton" in sql.lower():
        return [
            {
                "id": 976,
                "nombre_contacto": "Gavin Templeton",
                "email_contacto": "gavintempletong@gmail.com",
                "cargo_contacto": "Desarrollador"
            }
        ]
    
    # Buscar CEOs
    elif "ceo" in sql.lower():
        return [
            {
                "id": 1,
                "nombre_contacto": "María González", 
                "email_contacto": "maria.gonzalez@banco.com",
                "cargo_contacto": "CEO"
            }
        ]
    
    return []

def simular_brevo_email(to, subject, html_content):
    """
    Simula envío via Brevo - enviaría a través del token dado
    """
    print(f"📧 Brevo Email:")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")
    print(f"   Content: {html_content[:100]}...")
    print(f"   SENT!")
    
    return {
        "sent": True,
        "recipient": to,
        "subject": subject
    }

def crear_prompt_simple():
    """
    Prompt minimalista para Sonnet 4
    """
    return """
    Agent Simple: Solo busca en tabla 'personas' y envía emails.
    
    HERRAMIENTAS:
    - supabase_query(sql) - Query a tabla personas
    - brevo_email(to, subject, html) - Envía email
    
    TABLA personas: id, nombre_contacto, email_contacto, cargo_contacto
    
    EJEMPLO: "Busca Gavin Templeton y envíale hello"
    
    Responde con JSON:
    {
        "sql": "SELECT * FROM personas WHERE nombre_contacto LIKE '%gavin%'", 
        "email_to": "email@encontrado.com",
        "email_subject": "Hello from Quantex",
        "email_content": "Hi Gavin! ..."
    }
    """

def ejecutar_agent(query):
    """
    Ejecuta el agent completo
    """
    print(f"🤖 SimpleAgent - Query: {query}")
    print("-" * 50)
    
    try:
        # Paso 1: Prompt para Sonnet
        prompt = crear_prompt_simple()
        
        user_input = f"Busca personas y envíale email. Query usuario: '{query}'"
        
        # Paso 2: Llama Sonnet 4
        print("🧠 Llamando Sonnet 4...")
        response = generate_structured_output(
            system_prompt=prompt,
            user_prompt=user_input,
            model_name="claude-sonnet-4-20250514",
            output_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "email_to": {"type": "string"}, 
                    "email_subject": {"type": "string"},
                    "email_content": {"type": "string"}
                },
                "required": ["sql"]
            }
        )
        
        print("✅ Sonnet 4 respondió")
        
        # Paso 3: Ejecutar acciones
        if response and "sql" in response:
            print("\n🔰 EJECUTANDO:")
            
            # Buscar personas
            personas = simular_supabase_query(response["sql"])
            
            if not personas:
                return {
                    "ok": False,
                    "mensaje": "Ninguna persona encontrada"
                }
            
            # Usar la primera persona encontrada
            persona = personas[0]
            
            print(f"✅ Encontrado: {persona['nombre_contacto']} ({persona['email_contacto']})")
            
            # Enviar email si hay datos
            if response.get("email_subject") and response.get("email_content"):
                to_email = persona["email_contacto"]
                subject = response["email_subject"]
                content = response["email_content"]
                
                email_result = simular_brevo_email(to_email, subject, content)
                
                return {
                    "ok": True,
                    "mensaje": f"Email enviado a {persona['nombre_contacto']} ({persona['email_contacto']})",
                    "persona": persona,
                    "email": {
                        "to": to_email,
                        "subject": subject,
                        "sent": True
                    }
                }
            else:
                return {
                    "ok": True,
                    "mensaje": f"Encontrado: {persona['nombre_contacto']} ({persona['email_contacto']})",
                    "persona": persona,
                    "email": None
                }
        
        else:
            return {
                "ok": False,
                "mensaje": "Sonnet 4 no generó respuesta válida",
                "error": str(response)
            }
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "ok": False,
            "mensaje": f"Error: {str(e)}"
        }

if __name__ == "__main__":
    # Test case Gavin Templeton
    query = "Busca Gavin Templeton y envíale hello"
    resultado = ejecutar_agent(query)
    
    print("\n🎯 RESULTADO FINAL:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

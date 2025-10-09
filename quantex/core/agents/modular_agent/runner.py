"""
Runner del agente modular.
Ejecuta las herramientas usando SDKs oficiales con flujo de aprobación.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import re
import os
import sys
try:
    from .sdk_config import SDKConfig
except ImportError:
    # Fallback for absolute import
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from sdk_config import SDKConfig


def _is_valid_email(email: str) -> bool:
    """Valida formato de email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _extract_first_name(full_name: str) -> str:
    """Devuelve el primer nombre, preservando nombres compuestos comunes (ej. 'Juan Pablo')."""
    if not isinstance(full_name, str):
        return ""
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return ""
    # Heurística para nombres compuestos frecuentes en ES
    compound_triggers = {"Juan", "Jose", "José", "Maria", "María", "Luis", "Ana", "Carlos"}
    if len(parts) >= 2 and parts[0] in compound_triggers:
        # Evitar unir si el segundo token parece partícula o apellido corto común
        second = parts[1]
        particles = {"de", "del", "la", "las", "los"}
        if second.lower() not in particles and second[0].isupper():
            return f"{parts[0]} {second}"
    return parts[0]


def execute_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una herramienta específica.
    
    Args:
        tool_call: Dict con 'tool' y 'params'
        
    Returns:
        Dict con resultado de la ejecución
    """
    tool = tool_call.get("tool")
    params = tool_call.get("params", {})

    if tool == "supabase.query_table":
        return _execute_supabase_query_table(params)
    elif tool == "supabase.find_person":
        return _execute_supabase_find_person(params)
    elif tool == "llm.compose_email":
        return _execute_llm_compose_email(params)
    elif tool == "llm.compose_email_template":
        return _execute_llm_compose_email_template(params)
    elif tool == "brevo.send_email":
        return _execute_brevo_send_email(params)
    elif tool == "gmail.send_email":
        return _execute_gmail_send_email(params)
    elif tool == "gmail.ingest_received":
        return _execute_gmail_ingest_received(params)
    else:
        return {"ok": False, "error": f"Tool '{tool}' not implemented"}


def _execute_supabase_query_table(params: Dict[str, Any]) -> Dict[str, Any]:
    """Herramienta genérica para hacer queries a cualquier tabla especificando columnas y filtros."""
    try:
        table_name = params.get("table_name", "").strip()
        columns = params.get("columns", "*").strip()
        filters = params.get("filters", {})
        limit = params.get("limit", 10)
        order_by = params.get("order_by", "")
        ascending = params.get("ascending", True)
        
        if not table_name:
            return {"ok": False, "error": "table_name es requerido"}
        
        # Importar cliente Supabase
        from supabase import create_client, Client
        
        # Usar SDKConfig para configuración centralizada
        config = SDKConfig.get_supabase_config()
        supabase: Client = create_client(config['url'], config['key'])
        
        print(f"Ejecutando query en tabla '{table_name}' con columnas '{columns}'")
        if filters:
            print(f"Filtros: {filters}")
        
        # Construir query
        query = supabase.table(table_name).select(columns)
        
        # Aplicar filtros dinámicamente
        if filters:
            for column, value in filters.items():
                if value is None:
                    query = query.is_(column, "null")
                elif isinstance(value, str) and value.startswith("not_null"):
                    query = query.not_(column, "is", "null")
                elif isinstance(value, str) and value.startswith("like:"):
                    # Filtro LIKE: "like:%juan%"
                    like_value = value[5:]  # Remover "like:"
                    query = query.ilike(column, like_value)
                else:
                    query = query.eq(column, value)
        
        # Aplicar ordenamiento
        if order_by:
            if ascending:
                query = query.order(order_by)
            else:
                query = query.order(order_by, desc=True)
        
        # Aplicar límite
        query = query.limit(limit)
        
        # Ejecutar query
        response = query.execute()
        
        if response.data is not None:
            return {
                "ok": True,
                "data": response.data,
                "count": len(response.data),
                "table": table_name,
                "columns": columns,
                "filters": filters,
                "limit": limit
            }
        else:
            return {"ok": False, "error": "No se recibieron datos de la tabla"}
            
    except Exception as e:
        return {"ok": False, "error": f"Error ejecutando query en tabla: {str(e)}"}


def _execute_supabase_find_person(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta búsqueda de persona en Supabase con información completa."""
    try:
        search_term = params.get("search_term", "").strip()
        search_type = params.get("search_type", "name")
        only_unsent = params.get("only_unsent", False)
        limit = params.get("limit", 10)

        # Determinar si es búsqueda general
        is_general_search = (search_type == "general" or 
                           (only_unsent and not search_term) or
                           (search_type == "name" and not search_term))

        # Para búsquedas generales, no requerir search_term
        if not is_general_search and not search_term:
            return {"ok": False, "error": "search_term requerido para búsquedas específicas"}
        
        # Importar cliente Supabase
        from supabase import create_client, Client
        
        # Usar SDKConfig para configuración centralizada
        config = SDKConfig.get_supabase_config()
        supabase: Client = create_client(config['url'], config['key'])
        
        # Determinar tipo de búsqueda
        if is_general_search:
            if only_unsent:
                print(f"Buscando todas las personas que no han recibido emails en Supabase...")
            else:
                print(f"Buscando todas las personas en Supabase...")
        else:
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
        if is_general_search:
            if only_unsent:
                # Búsqueda general solo para personas sin emails
                query = query.eq('email_sent', False)
            # Para búsqueda general sin filtros, no aplicar filtros adicionales
        elif search_type == "name":
            query = query.ilike('nombre_contacto', f'%{search_term}%')
        elif search_type == "email":
            query = query.ilike('email_contacto', f'%{search_term}%')
        elif search_type == "rut":
            query = query.ilike('rut_empresa', f'%{search_term}%')
        
        # Aplicar límite
        query = query.limit(limit)
        
        # Filtrar solo personas que no han recibido emails si se solicita (para búsquedas específicas)
        if only_unsent and not is_general_search:
            query = query.eq('email_sent', False)
        
        response = query.execute()
        
        if response.data and len(response.data) > 0:
            # Si es búsqueda general, retornar múltiples resultados
            if is_general_search:
                persons = []
                for person_data in response.data:
                    # Buscar información de empresa para cada persona
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
                    
                    persons.append({
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
                    })
                
                return {
                    "ok": True,
                    "found": True,
                    "count": len(persons),
                    "persons": persons
                }
            else:
                # Búsqueda individual (comportamiento original)
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


def _execute_llm_compose_email(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta redacción de email usando LLM."""
    try:
        recipient_name = _extract_first_name(params.get("recipient_name", "").strip())
        recipient_company = params.get("recipient_company", "")
        email_purpose = params.get("email_purpose", "").strip()
        context = params.get("context", "")
        tone = params.get("tone", "professional")
        
        if not recipient_name or not email_purpose:
            return {"ok": False, "error": "recipient_name y email_purpose son requeridos"}
        
        # Importar llm_manager
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from quantex.core.llm_manager import generate_structured_output
        
        # Prompt para redacción de email
        system_prompt = f"""Eres un asistente profesional de redacción de emails. 
Redacta emails {tone} y efectivos basándote en el contexto proporcionado.

Formato requerido:
- Asunto: Claro y conciso
- Contenido: Profesional, estructurado y apropiado para el destinatario
- Usa HTML básico para formato (p, strong, em, br)
- Máximo 300 palabras"""

        user_prompt = f"""Redacta un email con los siguientes detalles:

Destinatario: {recipient_name}
Empresa: {recipient_company or 'No especificada'}
Propósito: {email_purpose}
Contexto adicional: {context or 'Ninguno'}
Tono: {tone}

Devuelve un JSON con 'subject' y 'html_content'."""

        output_schema = {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "html_content": {"type": "string"}
            },
            "required": ["subject", "html_content"]
        }
        
        print(f"Redactando email para {recipient_name} sobre {email_purpose}...")
        
        result = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_name="claude-sonnet-4-20250514",
            output_schema=output_schema,
            force_json_output=True
        )
        
        if result and "subject" in result and "html_content" in result:
            return {
                "ok": True,
                "subject": result["subject"],
                "html_content": result["html_content"],
                "recipient_name": recipient_name,
                "email_purpose": email_purpose
            }
        else:
            return {"ok": False, "error": "LLM no devolvió formato válido"}
            
    except Exception as e:
        return {"ok": False, "error": f"Error redactando email: {str(e)}"}


def _execute_llm_compose_email_template(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta redacción de email usando plantilla simple de presentación."""
    try:
        recipient_name = params.get("recipient_name", "").strip()
        recipient_company = params.get("recipient_company", "")
        template_variables = params.get("template_variables", {}) or {}
        # Permite override opcional por params, pero por defecto se usa el archivo de subject
        subject_override = (params.get("subject") or "").strip()
        
        if not recipient_name:
            return {"ok": False, "error": "recipient_name es requerido"}
        
        # Obtener rutas de los archivos de plantilla
        current_dir = os.path.dirname(__file__)
        subject_template_path = os.path.join(current_dir, "email_template_subject.txt")
        html_template_path = os.path.join(current_dir, "email_template.html")
        
        # Leer plantilla de asunto (solo si no viene override)
        subject_template = ""
        if not subject_override:
            try:
                with open(subject_template_path, 'r', encoding='utf-8') as f:
                    subject_template = f.read().strip()
            except FileNotFoundError:
                return {"ok": False, "error": f"Archivo de plantilla no encontrado: {subject_template_path}"}
        
        # Leer plantilla HTML (la usamos como contenedor de texto plano dentro de <pre>)
        try:
            with open(html_template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
        except FileNotFoundError:
            return {"ok": False, "error": f"Archivo de plantilla no encontrado: {html_template_path}"}
        
        # Construir mapping de variables con defaults vacíos
        class DefaultDict(dict):
            def __missing__(self, key):
                return ""

        variables = DefaultDict(
            recipient_name=recipient_name,
            recipient_company=recipient_company or 'Su Empresa',
            **template_variables
        )

        # Aplicar variables a las plantillas
        company_name = recipient_company or 'Su Empresa'
        if subject_override:
            subject = subject_override
        else:
            try:
                subject = subject_template.format(recipient_company=company_name)
            except Exception:
                subject = subject_template

        # Reemplazar variables directamente en el HTML completo para mantener estilos inline
        try:
            html_content = html_template.format_map(variables)
        except Exception:
            try:
                html_content = html_template.format(**variables)
            except Exception:
                html_content = html_template

        # Generar texto plano para textContent eliminando etiquetas HTML
        text_content = re.sub(r"<[^>]+>", "", html_content)
        
        print(f"Generando email con plantilla para {recipient_name}...")
        
        return {
            "ok": True,
            "subject": subject,
            "text_content": text_content,
            "html_content": html_content,
            "recipient_name": recipient_name,
            "recipient_company": recipient_company,
            "template_variables": template_variables,
            "template_files": {
                "subject": subject_template_path,
                "html": html_template_path
            }
        }
        
    except Exception as e:
        return {"ok": False, "error": f"Error generando email con plantilla: {str(e)}"}


def _execute_brevo_send_email(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta envío de email via Brevo."""
    # Feature flag: permitir desactivar Brevo y redirigir a Gmail
    sender_provider = os.getenv('SENDER_PROVIDER', 'gmail').lower()
    if sender_provider != 'brevo':
        # Redirigir a Gmail con los mismos parámetros si es posible
        print("⚠️  Brevo desactivado por SENDER_PROVIDER. Redirigiendo a gmail.send_email…")
        return _execute_gmail_send_email(params)
    # Validaciones básicas
    to_list = params.get("to", [])
    subject = params.get("subject", "")
    html_body = params.get("html_body", "")
    text_body = params.get("text_body", "")
    
    # Validar emails
    invalid_emails = [email for email in to_list if not _is_valid_email(email)]
    if invalid_emails:
        return {
            "ok": False, 
            "error": f"Emails inválidos: {invalid_emails}"
        }
    
    if not subject.strip():
        return {"ok": False, "error": "Asunto vacío"}
        
    if not (html_body.strip() or text_body.strip()):
        return {"ok": False, "error": "Contenido vacío"}
    
    # Envío real via API REST de Brevo
    try:
        import requests
        
        # Usar SDKConfig para configuración centralizada de Brevo
        config = SDKConfig.get_brevo_config()
        
        # Preparar datos para API REST de Brevo
        email_data = {
            "to": [{"email": email} for email in to_list],
            "subject": subject,
            # Enviar texto plano si existe; html es opcional
            **({"textContent": text_body} if text_body.strip() else {}),
            **({"htmlContent": html_body} if html_body.strip() else {}),
            "sender": {
                "email": config['sender_email'],
                "name": config['sender_name']
            },
            "replyTo": {
                "email": config['reply_to_email'],
                "name": config['reply_to_name']
            }
        }
        
        print(f"Enviando email real a {to_list} con asunto '{subject}'")
        print(f"Desde: gavintempleton@gavintempleton.net")
        
        # Llamar API REST de Brevo
        headers = {
            "api-key": config['api_key'],
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers=headers,
            json=email_data
        )
        
        if response.status_code == 201:
            result = response.json()
        else:
            return {
                "ok": False,
                "error": f"Error API Brevo: {response.status_code} - {response.text}"
            }
        
        return {
            "ok": True, 
            "message_id": result.get("messageId", "brevo-real"),
            "recipients": to_list,
            "subject": subject,
            "from": "gavintempleton@gavintempleton.net",
            "brevo_response": result
        }
        
    except Exception as e:
        return {
            "ok": False, 
            "error": f"Error enviando email: {str(e)}"
        }


def _execute_gmail_send_email(params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía email vía Gmail API usando la herramienta local (sin tracking)."""
    to_list = params.get("to", [])
    subject = params.get("subject", "").strip()
    html_body = params.get("html_body", "").strip()
    from_email = params.get("from_email")

    if isinstance(to_list, str):
        to_list = [to_list]

    if not to_list:
        return {"ok": False, "error": "Destinatario(s) requerido(s)"}
    if not subject:
        return {"ok": False, "error": "Asunto requerido"}
    if not html_body:
        return {"ok": False, "error": "Contenido HTML requerido"}

    # Enviar uno por uno para reportar estado
    try:
        # Importar herramienta
        from .gmail_send_tool import send_email as gmail_send

        results = []
        for to in to_list:
            res = gmail_send(to=to, subject=subject, html_body=html_body, from_email=from_email)
            results.append(res)

        all_ok = all(r.get("ok") for r in results)
        if all_ok:
            return {"ok": True, "results": results}
        # Tomar el primer error disponible para mostrarlo claramente
        first_error = None
        for r in results:
            if not r.get("ok"):
                first_error = r.get("error") or "Error en envío individual"
                break
        return {"ok": False, "error": first_error, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _execute_gmail_ingest_received(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingiere emails recibidos desde Gmail y los persiste en Supabase.
    Puentea a la herramienta local `gmail_ingest_tool.ingest_received`.
    """
    try:
        # Import ligero para evitar dependencias circulares
        from .gmail_ingest_tool import ingest_received as gmail_ingest

        # Params con defaults seguros
        max_days = int(params.get("max_days", 1))
        max_messages = int(params.get("max_messages", 50))
        include_spam = bool(params.get("include_spam", False))

        result = gmail_ingest(max_days=max_days, max_messages=max_messages, include_spam=include_spam)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": f"Error ingiriendo emails: {str(e)}"}

def run_agent(user_query: str, auto_approve: bool = False) -> Dict[str, Any]:
    """
    Ejecuta el agente completo: planifica y ejecuta.
    
    Args:
        user_query: Consulta del usuario
        auto_approve: Si True, no pide confirmación
        
    Returns:
        Dict con status y resultados
    """
    # Importación dinámica para evitar problemas de módulo
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from planner import plan_action
    
    # Paso 1: Planificar
    print("Planificando acción...")
    plan = plan_action(user_query)
    
    if not plan or "error" in plan:
        return {"status": "error", "message": plan.get("error", "Error desconocido")}
    
    print("PLAN:")
    for i, step in enumerate(plan.get("plan", []), 1):
        print(f"  {i}. {step}")
    
    print(f"\nHERRAMIENTAS A USAR:")
    for i, call in enumerate(plan.get("tool_calls", []), 1):
        print(f"  {i}. {call['tool']} con params: {call['params']}")
    
    # Paso 2: Aprobación (si es necesaria)
    approvals_needed = plan.get("approvals_needed", True)
    if approvals_needed and not auto_approve:
        print(f"\nSe requiere aprobación para ejecutar {len(plan.get('tool_calls', []))} herramienta(s)")
        approval = input("¿Ejecutar? (y/n): ").lower().strip()
        if approval != "y":
            return {"status": "cancelled", "plan": plan}
    
    # Paso 3: Ejecutar herramientas con conexión inteligente
    print(f"\n🔧 Ejecutando {len(plan.get('tool_calls', []))} herramientas...")
    results = []
    
    for i, call in enumerate(plan.get("tool_calls", []), 1):
        tool_name = call['tool']
        params = call.get('params', {})
        
        # Conexión inteligente: usar resultados anteriores
        if tool_name == "llm.compose_email" and results:
            # Usar datos de persona encontrada
            person_result = None
            for prev_result in results:
                if prev_result["tool"] == "supabase.find_person" and prev_result["response"].get("found"):
                    person_result = prev_result["response"]["person"]
                    break
            
            if person_result:
                params = {
                    "recipient_name": _extract_first_name(person_result.get("nombre_contacto", params.get("recipient_name", ""))),
                    "recipient_company": person_result.get("empresa", {}).get("razon_social", ""),
                    "email_purpose": params.get("email_purpose", ""),
                    "tone": params.get("tone", "professional")
                }
                print(f"   🔗 Conectando con datos de persona: {person_result.get('nombre_contacto')}")
        
        elif tool_name == "llm.compose_email_template" and results:
            # Usar datos de persona encontrada para plantilla SOLO si hay resultado específico
            person_result = None
            for prev_result in results:
                if prev_result["tool"] == "supabase.find_person" and prev_result["response"].get("found"):
                    resp = prev_result["response"]
                    if isinstance(resp.get("person"), dict):
                        person_result = resp["person"]
                    break
            
            if person_result:
                # Manejar empresa que puede ser None
                empresa_info = person_result.get("empresa")
                empresa_name = ""
                if empresa_info and isinstance(empresa_info, dict):
                    empresa_name = empresa_info.get("razon_social", "")
                elif empresa_info and isinstance(empresa_info, str):
                    empresa_name = empresa_info
                
                params = {
                    "recipient_name": _extract_first_name(person_result.get("nombre_contacto", params.get("recipient_name", ""))),
                    "recipient_company": empresa_name
                }
                print(f"   🔗 Conectando plantilla con datos de persona: {person_result.get('nombre_contacto')}")
        
        elif tool_name == "brevo.send_email" and results:
            # Usar email redactado y datos de persona, con validaciones estrictas
            email_result = None
            person_result = None
            
            for prev_result in results:
                if prev_result["tool"] in ["llm.compose_email", "llm.compose_email_template"]:
                    email_result = prev_result["response"]
                elif prev_result["tool"] == "supabase.find_person" and prev_result["response"].get("found"):
                    resp = prev_result["response"]
                    if isinstance(resp.get("person"), dict):
                        person_result = resp["person"]

            # Validaciones: persona específica y correo presentes
            if not person_result or not person_result.get("email_contacto"):
                invalid_msg = "Falta destinatario válido: ejecute una búsqueda específica (supabase.find_person) que devuelva 'person' con 'email_contacto'."
                print(f"   ❌ {invalid_msg}")
                result = {"ok": False, "error": invalid_msg}
                results.append({"tool": tool_name, "params": params, "response": result})
                continue

            # Validación: email redactado debe incluir subject y al menos text/html
            if not email_result or not email_result.get("subject"):
                invalid_msg = "Falta 'subject' del email: asegúrese de redactar el email antes de enviarlo."
                print(f"   ❌ {invalid_msg}")
                result = {"ok": False, "error": invalid_msg}
                results.append({"tool": tool_name, "params": params, "response": result})
                continue

            # Validación: recipient_name debe existir en la redacción
            recipient_name_present = bool(email_result.get("recipient_name"))
            if not recipient_name_present:
                invalid_msg = "Falta 'recipient_name' en la redacción: no se enviará el email sin destinatario nominal."
                print(f"   ❌ {invalid_msg}")
                result = {"ok": False, "error": invalid_msg}
                results.append({"tool": tool_name, "params": params, "response": result})
                continue

            # Construcción segura de parámetros: priorizar HTML si existe (para respetar estilos)
            text_body = email_result.get("text_content", "")
            html_body = email_result.get("html_content", "")
            params = {
                "to": [person_result.get("email_contacto", "")],
                "subject": email_result.get("subject", ""),
                **({"html_body": html_body} if html_body else {}),
                **({"text_body": text_body} if (text_body and not html_body) else {})
            }
            print(f"   🔗 Conectando email redactado con destinatario: {person_result.get('email_contacto')}")

        elif tool_name == "gmail.send_email" and results:
            # Conectar automáticamente subject/html/to desde pasos previos
            email_result = None
            person_result = None
            came_from_template = False
            # Soportar flag vía params o variable de entorno FORCE_SEND
            force_send_flag = bool(params.get("force_send", False)) or (
                str(os.getenv('FORCE_SEND', '')).lower() in ['1', 'true', 'yes']
            )

            for prev_result in results:
                if prev_result["tool"] in ["llm.compose_email", "llm.compose_email_template"]:
                    email_result = prev_result["response"]
                    if prev_result["tool"] == "llm.compose_email_template":
                        came_from_template = True
                elif prev_result["tool"] == "supabase.find_person" and prev_result["response"].get("found"):
                    resp = prev_result["response"]
                    if isinstance(resp.get("person"), dict):
                        person_result = resp["person"]

            # Validaciones mínimas antes de construir los params
            if person_result and person_result.get("email_contacto") and email_result and email_result.get("subject"):
                # Check de envío previo de introducción si viene de plantilla
                if came_from_template and not force_send_flag:
                    try:
                        from quantex.core import database_manager as db
                        # Intentar por contact_id si se puede resolver
                        prior_intro = None
                        # Resolver contact_id por email
                        contact_q = db.supabase.table('personas').select('id').eq('email_contacto', person_result.get('email_contacto')).limit(1).execute()
                        contact_id_chk = contact_q.data[0]['id'] if contact_q and contact_q.data else None
                        if contact_id_chk is not None:
                            prior_intro = db.supabase.table('email_messages').select('id').eq('contact_id', contact_id_chk).eq('direction','sent').eq('message_kind','intro').limit(1).execute()
                        else:
                            prior_intro = db.supabase.table('email_messages').select('id').contains('to_emails', [person_result.get('email_contacto')]).eq('direction','sent').eq('message_kind','intro').limit(1).execute()
                        if prior_intro and prior_intro.data:
                            # Si hay consola interactiva, pedir confirmación
                            if sys.stdin and sys.stdin.isatty():
                                    user_ans = input("Ya existe una intro previa. ¿Enviar de todos modos? (y/n): ").strip().lower()
                                    if user_ans == 'y':
                                        force_send_flag = True
                                        print("   ⚠️ Confirmado manualmente: se enviará a pesar de intro previa.")
                                    else:
                                        print("   ❌ Intro previa detectada. Envío cancelado por el usuario.")
                                        result = {"ok": False, "error": "Intro ya enviada a este destinatario"}
                                        results.append({"tool": tool_name, "params": params, "response": result})
                                        continue
                            else:
                                # Sin TTY (p.ej. UI web): devolver requiere confirmación
                                print("   ❌ Ya existe un email de introducción previo. Requiere confirmación para reenviar.")
                                result = {
                                    "ok": False,
                                    "requires_confirmation": True,
                                    "reason": "duplicate_intro",
                                    "suggested_params": {"force_send": True},
                                    "error": "Intro ya enviada a este destinatario"
                                }
                                results.append({"tool": tool_name, "params": params, "response": result})
                                continue
                    except Exception as _chk_e:
                        print(f"   ⚠️ No se pudo verificar intro previa: {_chk_e}")
                elif came_from_template and force_send_flag:
                    print("   ⚠️ force_send=True: se omite el bloqueo de intro duplicada por petición explícita.")
                text_body = email_result.get("text_content", "")
                html_body = email_result.get("html_content", "")
                params = {
                    "to": [person_result.get("email_contacto")],
                    "subject": email_result.get("subject", ""),
                    **({"html_body": html_body} if html_body else {}),
                    **({"text_body": text_body} if (text_body and not html_body) else {}),
                    **({"force_send": True} if force_send_flag else {})
                }
                print(f"   🔗 Conectando email redactado con destinatario (Gmail): {person_result.get('email_contacto')}")
        
        print(f"\n📋 Ejecutando {i}/{len(plan.get('tool_calls', []))}: {tool_name}")
        print(f"   Parámetros: {params}")
        
        result = execute_tool({"tool": tool_name, "params": params})
        
        print(f"   Resultado: {result.get('ok', False)}")
        if result.get('ok', False):
            print(f"   ✅ {tool_name} ejecutado exitosamente")

            # Persistencia de envíos en email_messages cuando se usa Gmail
            if tool_name == "gmail.send_email":
                try:
                    # Recuperar contexto de persona y redacción
                    email_result = None
                    person_result_ctx = None
                    came_from_template = False
                    for prev_result in results:
                        if prev_result["tool"] in ["llm.compose_email", "llm.compose_email_template"]:
                            email_result = prev_result["response"]
                            if prev_result["tool"] == "llm.compose_email_template":
                                came_from_template = True
                        elif prev_result["tool"] == "supabase.find_person" and prev_result["response"].get("found"):
                            resp = prev_result["response"]
                            if isinstance(resp.get("person"), dict):
                                person_result_ctx = resp["person"]

                    # Preparar campos
                    to_list = params.get("to", []) if isinstance(params.get("to"), list) else [params.get("to")]
                    subject_val = params.get("subject") or (email_result or {}).get("subject") or ""
                    html_body_val = params.get("html_body") or (email_result or {}).get("html_content") or ""
                    text_body_val = (email_result or {}).get("text_content") or ""
                    from_email_val = os.getenv('GMAIL_FROM_EMAIL')

                    # Resolver contact_id y company_id si es posible
                    contact_id_val = None
                    company_id_val = None
                    try:
                        from quantex.core import database_manager as db
                        # Preferir primer destinatario
                        to_email = to_list[0] if to_list else None
                        if to_email:
                            contact_res = db.supabase.table('personas').select('id,rut_empresa').eq('email_contacto', to_email).limit(1).execute()
                            if contact_res and contact_res.data:
                                contact_id_val = contact_res.data[0].get('id')
                                rut_emp = contact_res.data[0].get('rut_empresa')
                                if rut_emp:
                                    emp_res = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_emp).limit(1).execute()
                                    if emp_res and emp_res.data:
                                        company_id_val = emp_res.data[0].get('id')
                        # Si no se encontró por correo, intentar por contexto de persona
                        if (contact_id_val is None) and person_result_ctx and person_result_ctx.get('email_contacto'):
                            to_email_ctx = person_result_ctx.get('email_contacto')
                            contact_res = db.supabase.table('personas').select('id,rut_empresa').eq('email_contacto', to_email_ctx).limit(1).execute()
                            if contact_res and contact_res.data:
                                contact_id_val = contact_res.data[0].get('id')
                                rut_emp = contact_res.data[0].get('rut_empresa')
                                if rut_emp:
                                    emp_res = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_emp).limit(1).execute()
                                    if emp_res and emp_res.data:
                                        company_id_val = emp_res.data[0].get('id')

                        # Insertar registro de email enviado
                        message_kind_val = 'intro' if came_from_template else 'other'
                        payload = {
                            'direction': 'sent',
                            **({'contact_id': contact_id_val} if contact_id_val is not None else {}),
                            **({'company_id': company_id_val} if company_id_val is not None else {}),
                            'from_email': from_email_val or '',
                            'to_emails': to_list or [],
                            'cc_emails': [],
                            'subject': subject_val,
                            'body_html': html_body_val,
                            'body_text': text_body_val,
                            'message_id': (result or {}).get('message_id'),
                            'thread_id': None,
                            'sent_at': datetime.now(timezone.utc).isoformat(),
                            'message_kind': message_kind_val
                        }
                        db.supabase.table('email_messages').insert(payload).execute()
                        print("   📝 Registro de envío guardado en email_messages")

                        # Si es intro y hay contact_id, marcar en personas
                        if message_kind_val == 'intro' and contact_id_val is not None:
                            try:
                                db.supabase.table('personas').update({
                                    'email_sent': True,
                                    'email_sent_at': datetime.now(timezone.utc).isoformat()
                                }).eq('id', contact_id_val).eq('email_sent', False).execute()
                                print("   🏷️  Marcado persona.email_sent = true")
                            except Exception as _ue:
                                print(f"   ⚠️ No se pudo actualizar personas.email_sent: {_ue}")
                    except Exception as _e:
                        print(f"   ⚠️ No se pudo registrar el envío en email_messages: {_e}")
                except Exception as _outer_e:
                    print(f"   ⚠️ Error general registrando email enviado: {_outer_e}")
        else:
            print(f"   ❌ Error en {tool_name}: {result.get('error', 'Error desconocido')}")
        
        results.append({
            "tool": tool_name,
            "params": params,
            "response": result
        })
    
    return {
        "status": "completed",
        "plan": plan,
        "results": results
    }

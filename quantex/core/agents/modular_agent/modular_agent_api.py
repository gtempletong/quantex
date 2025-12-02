#!/usr/bin/env python3
"""
API endpoint para el sistema modular
"""

import os
import sys
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from C:\Quantex\.env
load_dotenv('C:/Quantex/.env')

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from quantex.core.agents.modular_agent.runner import run_agent
except ImportError as e:
    print(f"Error importing run_agent: {e}")
    # Fallback: try to import components separately
    from quantex.core.agents.modular_agent.planner import plan_action
    from quantex.core.agents.modular_agent.runner import execute_tool
    
    def run_agent(query: str, auto_approve: bool = True) -> Dict[str, Any]:
        """Fallback implementation of run_agent"""
        try:
            # Generate plan using LLM
            plan = plan_action(query)
            
            # Execute tools
            results = []
            if plan.get("tool_calls"):
                for tool_call in plan["tool_calls"]:
                    result = execute_tool(tool_call)
                    results.append(result)
            
            return {
                "status": "completed",
                "plan": plan.get("plan", []),
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

app = Flask(__name__)
CORS(app)

# HTML template for the interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Modular - Quantex</title>
    <style>
        /* Estilos base - Similar a app.py */
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            background-color: #f0f2f5;
            color: #333333;
            min-height: 100vh;
            overflow-y: auto; 
        }

        .container {
            display: flex;
            flex-direction: column;
            width: 100%; 
            padding: 20px;
            gap: 15px;
            box-sizing: border-box;
            max-width: 900px;
            margin: 0 auto;
        }

        h1 {
            text-align: center; 
            color: #333; 
            margin: 0 0 10px 0; 
            font-weight: 600;
            font-size: 24px;
        }

        .query-section {
            background-color: #ffffff; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }

        .query-input {
            width: 100%; 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 18px; 
            font-size: 14px; 
            margin-bottom: 10px;
            box-sizing: border-box;
        }

        .query-input:focus {
            outline: none;
            border-color: #007bff;
        }

        .submit-btn {
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 18px;
            cursor: pointer;
            font-weight: bold;
            width: 100%;
            font-size: 15px;
        }

        .submit-btn:hover {
            background-color: #0056b3;
        }

        .submit-btn:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }

        .examples {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-size: 13px;
        }

        .examples h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
            font-weight: 600;
        }

        .example {
            background-color: #e3f2fd;
            padding: 10px 12px;
            margin: 6px 0;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
            font-size: 13px;
        }

        .example:hover {
            background-color: #bbdefb;
        }

        .result {
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            white-space: pre-wrap;
            font-family: 'Monaco', 'Courier New', monospace;
            max-height: 500px;
            overflow-y: auto;
            font-size: 13px;
            line-height: 1.5;
        }

        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 40px 20px;
            font-size: 15px;
        }

        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            border-left: 4px solid #dc3545;
        }

        .error h3 {
            margin-top: 0;
            font-size: 16px;
        }

        .success {
            background-color: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            border-left: 4px solid #28a745;
        }

        .success h3 {
            margin-top: 0;
            font-size: 16px;
        }

        .success h4 {
            color: #0c5460;
            font-size: 14px;
            margin: 15px 0 8px 0;
        }

        .workflow-steps {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .workflow-steps h3 {
            margin: 0 0 12px 0;
            font-size: 14px;
            color: #333;
            font-weight: 600;
        }

        .step {
            display: flex;
            align-items: center;
            margin: 8px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #007bff;
            font-size: 13px;
        }

        .step-number {
            background: #007bff;
            color: white;
            min-width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            font-weight: 600;
            font-size: 12px;
        }

        /* Detalles plegables */
        details {
            margin-top: 15px;
            cursor: pointer;
        }

        summary {
            color: #007bff;
            font-weight: 500;
            font-size: 13px;
            padding: 5px 0;
        }

        summary:hover {
            color: #0056b3;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            h1 {
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Sistema Modular - Quantex</h1>
        
        <div class="workflow-steps">
            <h3>📋 Flujo de trabajo para emails:</h3>
            <div class="step">
                <div class="step-number">1</div>
                <div>
                    <strong>BUSCAR:</strong> Encuentra personas específicas o listas de contactos
                </div>
            </div>
            <div class="step">
                <div class="step-number">2</div>
                <div>
                    <strong>REDACTAR:</strong> Crea emails profesionales personalizados
                </div>
            </div>
            <div class="step">
                <div class="step-number">3</div>
                <div>
                    <strong>ENVIAR:</strong> Envía emails automáticamente usando Gmail
                </div>
            </div>
        </div>
        
        <div class="query-section">
            <form id="queryForm">
                <input type="text" 
                       id="queryInput" 
                       class="query-input" 
                       placeholder="Escribe tu query aquí... (ej: 'Busca a Gavin Templeton')"
                       required>
                <button type="submit" class="submit-btn">Ejecutar Query</button>
            </form>
        </div>

        <div class="examples">
            <h3>💡 Casos de uso principales:</h3>
            <div class="example" onclick="setQuery('Busca a Gavin Templeton')">
                🔍 1. BUSCAR: "Busca a Gavin Templeton"
            </div>
            <div class="example" onclick="setQuery('Encuentra personas que no han recibido emails')">
                📋 "Encuentra personas que no han recibido emails"
            </div>
            <div class="example" onclick="setQuery('Redacta un email profesional para Gavin Templeton sobre seguimiento de proyecto')">
                📝 2. REDACTAR: "Redacta un email profesional para Gavin Templeton sobre seguimiento de proyecto"
            </div>
            <div class="example" onclick="setQuery('Busca a Gavin y redacta un email para él sobre seguimiento de proyecto')">
                🔗 "Busca a Gavin y redacta un email para él sobre seguimiento de proyecto"
            </div>
            <div class="example" onclick="setQuery('Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo')">
                🚀 3. ENVIAR: "Busca a Gavin, redacta un email sobre seguimiento de proyecto y envíalo"
            </div>
            <div class="example" onclick="setQuery('Busca a Gavin y redacta email con plantilla')">
                📋 TEMPLATE: "Busca a Gavin y redacta email con plantilla"
            </div>
            <div class="example" onclick="setQuery('Envía email con plantilla a Gavin')">
                📧 TEMPLATE: "Envía email con plantilla a Gavin"
            </div>
        </div>

        <div id="result"></div>
    </div>

    <script>
        function setQuery(query) {
            document.getElementById('queryInput').value = query;
        }

        document.getElementById('queryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const query = document.getElementById('queryInput').value;
            const resultDiv = document.getElementById('result');
            
            if (!query.trim()) {
                return;
            }
            
            // Show loading
            resultDiv.innerHTML = '<div class="loading">⏳ Procesando query...</div>';
            
            try {
                const response = await fetch('/api/modular-agent/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Formatear mejor los resultados
                    let formattedResult = '';
                    
                    if (data.result.results && data.result.results.length > 0) {
                        formattedResult += '<h4>🔧 Herramientas ejecutadas:</h4>';
                        data.result.results.forEach((result, index) => {
                            formattedResult += `<div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">`;
                            formattedResult += `<strong>Herramienta ${index + 1}:</strong> ${result.tool || 'N/A'}<br>`;
                            // Verificar si la respuesta está en result.response o directamente en result
                            const response = result.response || result;
                            if (response.ok) {
                                formattedResult += `<span style="color: green;">✅ Ejecutado exitosamente</span><br>`;
                                if (response.data) {
                                    formattedResult += `<strong>Resultado:</strong> ${JSON.stringify(response.data, null, 2)}`;
                                } else if (response.person) {
                                    formattedResult += `<strong>Persona encontrada:</strong> ${response.person.nombre_contacto || 'N/A'}<br>`;
                                    formattedResult += `<strong>Email:</strong> ${response.person.email_contacto || 'N/A'}<br>`;
                                    formattedResult += `<strong>Empresa:</strong> ${response.person.empresa?.razon_social || 'N/A'}`;
                                } else if (response.found) {
                                    formattedResult += `<strong>Búsqueda exitosa:</strong> ${response.found ? 'Sí' : 'No'}`;
                                }
                            } else {
                                formattedResult += `<span style="color: red;">❌ Error: ${response.error || 'Error desconocido'}</span>`;
                            }
                            formattedResult += `</div>`;
                        });
                    }
                    
                    if (data.result.plan && data.result.plan.plan) {
                        formattedResult += '<h4>📋 Plan de ejecución:</h4>';
                        formattedResult += '<ol>';
                        data.result.plan.plan.forEach(step => {
                            formattedResult += `<li>${step}</li>`;
                        });
                        formattedResult += '</ol>';
                    }
                    
                    resultDiv.innerHTML = `
                        <div class="success">
                            <h3>✅ Query ejecutado exitosamente</h3>
                            ${formattedResult}
                            <details style="margin-top: 15px;">
                                <summary>Ver respuesta completa (JSON)</summary>
                                <div class="result">${JSON.stringify(data.result, null, 2)}</div>
                            </details>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="error">
                            <h3>❌ Error</h3>
                            <div class="result">${data.error}</div>
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="error">
                        <h3>❌ Error de conexión</h3>
                        <div class="result">${error.message}</div>
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Página principal con interfaz web"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/modular-agent/query', methods=['POST'])
def execute_query():
    """Endpoint para ejecutar queries del sistema modular"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query vacío'
            }), 400
        
        print(f"\n🤖 Ejecutando query: '{query}'")
        print("=" * 60)
        
        # Ejecutar el query con el sistema modular
        result = run_agent(query, auto_approve=True)
        
        print("=" * 60)
        print(f"✅ Query completado: '{query}'")
        
        return jsonify({
            'success': True,
            'query': query,
            'result': result
        })
        
    except Exception as e:
        print(f"\n❌ Error ejecutando query: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-report', methods=['POST'])
def send_report():
    """Endpoint específico para envío masivo de reportes con PDF adjunto"""
    try:
        data = request.get_json()
        recipients = data.get('recipients', [])
        report_topic = data.get('report_topic', '')
        subject = data.get('subject', 'Reporte Quantex')
        
        if not recipients:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron destinatarios'
            }), 400
            
        if not report_topic:
            return jsonify({
                'success': False,
                'error': 'No se proporcionó el tópico del reporte'
            }), 400
        
        print(f"\n📧 Enviando reporte a {len(recipients)} destinatarios...")
        print(f"📋 Asunto: {subject}")
        print(f"📊 Tópico: {report_topic}")
        
        # Importar execute_tool y db para usar directamente
        from quantex.core.agents.modular_agent.runner import execute_tool
        from quantex.core import database_manager as db
        from datetime import datetime, timezone
        
        # Nota: PostgREST no expone information_schema; evitamos introspección runtime
        
        # Obtener el último informe final desde Supabase
        latest_report = db.get_latest_report(report_keyword=report_topic)
        if not latest_report:
            return jsonify({
                'success': False,
                'error': f'No se encontró un informe final para "{report_topic}". Genéralo primero.'
            }), 400
        
        # Obtener URL del PDF
        pdf_url = latest_report.get('pdf_url')
        if not pdf_url:
            return jsonify({
                'success': False,
                'error': f'El informe "{report_topic}" no tiene PDF generado. Regenera el informe.'
            }), 400
        
        print(f"📎 PDF encontrado: {pdf_url}")
        
        # Mapeo de report_topic a nombre legible del informe
        report_names = {
            'clp': 'Peso Chileno',
            'copper': 'Cobre',
            'gold': 'Oro',
            'silver': 'Plata'
        }
        report_name = report_names.get(report_topic, report_topic)
        
        # Crear subject personalizado
        custom_subject = f"Informe del {report_name}"
        
        results = []
        successful_sends = 0
        
        # Enviar a cada destinatario individualmente
        for email in recipients:
            try:
                # Buscar nombre del destinatario EXCLUSIVAMENTE en active_contacts
                contact_name = None
                from quantex.core import database_manager as db_temp
                email_norm = (email or '').strip()
                print(f"    🔍 Buscando contacto (apollo_persons): {email_norm}")
                try:
                    ac_res = db_temp.supabase.table('apollo_persons') \
                        .select('full_name') \
                        .eq('email', email_norm) \
                        .limit(1) \
                        .execute()
                    if ac_res and ac_res.data:
                        full_name = ac_res.data[0].get('full_name')
                        contact_name = full_name.split()[0] if full_name else None
                        print(f"    ✅ Nombre encontrado: {full_name}")
                except Exception as lookup_err:
                    print(f"    ❌ Error consultando apollo_persons: {lookup_err}")

                # Estricto: si no hay nombre en active_contacts, abortar
                if not contact_name:
                    return jsonify({
                        'success': False,
                        'error': f"No se encontró nombre en active_contacts para '{email}'."
                    }), 400
                
                # Mensaje simple de texto plano
                simple_body = f"Hola {contact_name},\n\nAdjunto encontrarás el informe del {report_name}.\n\nSaludos cordiales,\nGavin Templeton"
                
                tool_call = {
                    "tool": "gmail.send_email",
                    "params": {
                        "to": email,
                        "subject": custom_subject,
                        "body": simple_body,
                        "attachment_url": pdf_url
                    }
                }
                
                print(f"  -> 📤 Enviando a: {email}")
                print(f"  -> 🔍 Tool call: {tool_call}")
                result = execute_tool(tool_call)
                
                # SIEMPRE guardar en email_messages (exitoso o fallido)
                try:
                    # Buscar contact_id por email
                    contact_id_val = None
                    company_id_val = None
                    
                    # Resolver contact_id/company_id solo si existen en 'personas'; no bloquear si no
                    try:
                        contact_res = db.supabase.table('personas').select('id,rut_empresa').eq('email_contacto', email).limit(1).execute()
                        if contact_res and contact_res.data:
                            contact_id_val = contact_res.data[0].get('id')
                            rut_emp = contact_res.data[0].get('rut_empresa')
                            if rut_emp:
                                emp_res = db.supabase.table('empresas').select('id').eq('rut_empresa', rut_emp).limit(1).execute()
                                if emp_res and emp_res.data:
                                    company_id_val = emp_res.data[0].get('id')
                    except Exception:
                        pass
                    
                    # Determinar el estado del envío
                    sent_at = datetime.now(timezone.utc).isoformat() if result.get("ok") else None
                    message_id = result.get('message_id') if result.get("ok") else None
                    
                    # Construir el cuerpo del email para el registro
                    email_body_text = f"Estimado {contact_name or 'Cliente'},\n\nTe adjunto el informe del {report_name}.\n\nSaludos,\nGavin Templeton"
                    
                    # Guardar en email_messages (siempre, exitoso o fallido)
                    payload = {
                        'direction': 'sent',
                        **({'contact_id': contact_id_val} if contact_id_val is not None else {}),
                        **({'company_id': company_id_val} if company_id_val is not None else {}),
                        'from_email': 'gavintempleton@gavintempleton.net',
                        'to_emails': [email],
                        'cc_emails': [],
                        'subject': custom_subject,
                        'body_html': simple_html,
                        'body_text': email_body_text,
                        'message_id': message_id,
                        'thread_id': None,
                        'sent_at': sent_at,  # null si falló
                        'message_kind': 'other',
                        'attachments': [{'filename': f'{report_name}.pdf', 'url': pdf_url}] if pdf_url else []
                    }
                    db.supabase.table('email_messages').insert(payload).execute()
                    
                    if result.get("ok"):
                        print(f"    📝 Registro guardado en email_messages (enviado)")
                        
                        # Actualizar personas.email_sent solo si fue exitoso
                        if contact_id_val is not None:
                            try:
                                db.supabase.table('personas').update({
                                    'email_sent': True,
                                    'email_sent_at': sent_at
                                }).eq('id', contact_id_val).eq('email_sent', False).execute()
                                print(f"    🏷️  Marcado persona.email_sent = true")
                            except Exception as _ue:
                                print(f"    ⚠️ No se pudo actualizar personas.email_sent: {_ue}")
                    else:
                        print(f"    📝 Registro guardado en email_messages (fallido: {result.get('error')})")
                        
                except Exception as save_error:
                    print(f"    ⚠️ Error guardando en BD: {save_error}")
                
                results.append({
                    "email": email,
                    "success": result.get("ok", False),
                    "message_id": result.get("message_id"),
                    "error": result.get("error") if not result.get("ok") else None
                })
                
                if result.get("ok"):
                    successful_sends += 1
                    print(f"    ✅ Enviado exitosamente")
                else:
                    print(f"    ❌ Error: {result.get('error')}")
                    
            except Exception as e:
                print(f"    ❌ Excepción: {e}")
                results.append({
                    "email": email,
                    "success": False,
                    "error": str(e)
                })
        
        print(f"📊 Resumen: {successful_sends}/{len(recipients)} emails enviados exitosamente")
        
        return jsonify({
            'success': True,
            'total_recipients': len(recipients),
            'successful_sends': successful_sends,
            'failed_sends': len(recipients) - successful_sends,
            'results': results
        })
        
    except Exception as e:
        print(f"\n❌ Error en envío masivo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/modular-agent/execute-tool', methods=['POST'])
def execute_tool_endpoint():
    """Endpoint para ejecutar herramientas directamente (sin LLM planner)"""
    try:
        data = request.get_json()
        tool = data.get('tool')
        params = data.get('params', {})
        
        if not tool:
            return jsonify({
                'ok': False,
                'error': 'Tool name is required'
            }), 400
        
        print(f"\n🔧 Ejecutando herramienta directa: {tool}")
        
        # Loggear parámetros de forma inteligente (ocultar contenido grande)
        params_for_log = {}
        for key, value in params.items():
            if key == 'attachments' and isinstance(value, list):
                # Mostrar solo la cantidad de attachments, no el contenido
                params_for_log[key] = f"[{len(value)} archivo(s)]"
            elif isinstance(value, str) and len(value) > 200:
                # Truncar strings largos
                params_for_log[key] = value[:200] + "..."
            elif isinstance(value, dict) and 'content' in value and isinstance(value['content'], str) and len(value['content']) > 100:
                # Truncar contenido base64
                params_for_log[key] = f"{{... content: {len(value['content'])} chars ...}}"
            else:
                params_for_log[key] = value
        print(f"📋 Parámetros: {params_for_log}")
        
        # Importar execute_tool
        from quantex.core.agents.modular_agent.runner import execute_tool
        
        # Ejecutar la herramienta
        result = execute_tool({
            "tool": tool,
            "params": params
        })
        
        if result.get("ok"):
            print(f"✅ Herramienta ejecutada exitosamente")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"\n❌ Error ejecutando herramienta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@app.route('/api/modular-agent/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'system': 'modular-agent',
        'version': '1.0.0'
    })

@app.route('/api/modular-agent/logs', methods=['GET'])
def get_logs():
    """Endpoint para obtener logs recientes"""
    # En una implementación real, esto leería de un archivo de log
    return jsonify({
        'message': 'Los logs se muestran en la consola del servidor',
        'tip': 'Revisa la ventana donde ejecutaste el servidor para ver los logs en tiempo real'
    })

if __name__ == '__main__':
    print("🚀 Iniciando servidor del Sistema Modular...")
    print("📱 Interfaz web: http://localhost:5003")
    print("🔌 API: http://localhost:5003/api/modular-agent/query")
    print("❤️  Health: http://localhost:5003/api/modular-agent/health")
    
    app.run(host='0.0.0.0', port=5003, debug=True)

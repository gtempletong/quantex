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
    """Endpoint específico para envío masivo de reportes (sin LLM)"""
    try:
        data = request.get_json()
        recipients = data.get('recipients', [])
        report_html = data.get('report_html', '')
        subject = data.get('subject', 'Reporte Quantex')
        
        if not recipients:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron destinatarios'
            }), 400
            
        if not report_html:
            return jsonify({
                'success': False,
                'error': 'No se proporcionó contenido HTML del reporte'
            }), 400
        
        print(f"\n📧 Enviando reporte a {len(recipients)} destinatarios...")
        print(f"📋 Asunto: {subject}")
        
        # Importar execute_tool para usar directamente
        from quantex.core.agents.modular_agent.runner import execute_tool
        
        results = []
        successful_sends = 0
        
        # Enviar a cada destinatario individualmente
        for email in recipients:
            try:
                tool_call = {
                    "tool": "gmail.send_email",
                    "params": {
                        "to": [email],
                        "subject": subject,
                        "html_body": report_html
                    }
                }
                
                print(f"  -> 📤 Enviando a: {email}")
                result = execute_tool(tool_call)
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
        print(f"📋 Parámetros: {params}")
        
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

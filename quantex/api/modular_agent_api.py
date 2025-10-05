#!/usr/bin/env python3
"""
API endpoint para el sistema modular
"""

import os
import sys
from flask import Flask, request, jsonify, render_template_string
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

# HTML template for the interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Modular - Quantex</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .query-section {
            margin-bottom: 30px;
        }
        .query-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .query-input:focus {
            outline: none;
            border-color: #4CAF50;
        }
        .submit-btn {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        .submit-btn:hover {
            background-color: #45a049;
        }
        .examples {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .example {
            background-color: #e8f5e8;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .example:hover {
            background-color: #d4edda;
        }
        .result {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 500px;
            overflow-y: auto;
        }
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        .workflow-steps {
            background-color: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .step {
            display: flex;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
            border-left: 4px solid #2196f3;
        }
        .step-number {
            background: #2196f3;
            color: white;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Sistema Modular - Quantex</h1>
        
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
                    <strong>ENVIAR:</strong> Envía emails automáticamente usando Brevo
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
    print("📱 Interfaz web: http://localhost:5000")
    print("🔌 API: http://localhost:5000/api/modular-agent/query")
    print("❤️  Health: http://localhost:5000/api/modular-agent/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

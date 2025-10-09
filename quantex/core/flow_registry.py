# quantex/core/flow_registry.py (Versión 2.1 - Completa y Corregida)

"""
Registro Central de Flujos (Single Source of Truth).
Este archivo define todas las acciones que el sistema Quantex puede realizar,
incluyendo sus descripciones y los parámetros que esperan en formato JSON Schema.
Es la base para construir el catálogo de herramientas del Router de IA.
"""

FLOW_REGISTRY = {
    # --- Flujos de Generación y Carga de Datos ---
    "load_data": {
        "handler_name": "_handle_load_data",
        "description": "Función interna para forzar la actualización y procesamiento de la evidencia de un tópico. Normalmente no es la primera herramienta a elegir para un usuario que pide un informe.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "El tópico principal para el cual cargar datos, por ejemplo 'cobre' o 'clp'."
                }
            },
            "required": ["report_keyword"]
        }
    },
    "generate_draft_report": {
        "handler_name": "_handle_fusion_synthesis",
        "description": "Genera el borrador de un informe de Mesa Redonda (ej. Cobre, CLP).",
        "parameters": {
            "type": "object",
            "properties": { "report_keyword": { "type": "string", "description": "El tópico del informe a generar, ej. 'cobre' o 'peso chileno'." }},
            "required": ["report_keyword"]
        }
    },
    "publish_final_report": {
        "handler_name": "_handle_publish",
        "description": "Genera y publica la versión final de un informe para un tópico.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "El tópico del informe a publicar, por ejemplo 'cobre' o 'clp'."
                }
            },
            "required": ["report_keyword"]
        }
    },

    # --- Flujos de Interacción con Informes Existentes ---
    "retrieve_latest_report": {
        "handler_name": "_handle_retrieve_report",
        "description": "Recupera y muestra el último informe final. Puede buscar por tipo de informe (ej. 'cobre', 'clp') O por ticker específico (ej. 'SPIPSA.INDX').",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "El tipo de informe a recuperar, por ejemplo 'cobre', 'clp', 'comite_tecnico_mercado'."
                },
                "ticker": {
                    "type": "string",
                    "description": "El ticker específico del informe a recuperar, por ejemplo 'SPIPSA.INDX', 'COPPER', 'USDCLP'."
                }
            },
            "required": []
        }
    },
    "edit_artifact": {
        "handler_name": "_handle_edit",
        "description": "Edita el contenido del último artefacto (informe/gráfico) visualizado. El usuario debe especificar qué quiere cambiar.",
        "parameters": {
            "type": "object",
            "properties": {
                "edit_instruction": {
                    "type": "string",
                    "description": "La instrucción detallada de la edición. Por ejemplo: 'Haz el resumen más corto y directo' o 'cambia el color del gráfico a azul'."
                }
            },
            "required": ["edit_instruction"]
        }
    },

    # --- Flujos de Enriquecimiento de Dossiers ---

    "trace_evidence_for_conclusion": {
        "handler_name": "_handle_answer_with_reasoning",
        "description": "Se activa para responder preguntas de seguimiento ('por qué', 'qué pasaría si...') sobre un informe ya mostrado, usando un proceso de razonamiento avanzado.",
        "parameters": { # Los parámetros que la IA debe extraer
            "type": "object",
            "properties": {
                "conclusion_text": {
                    "type": "string",
                    "description": "El texto exacto de la conclusión o el tema sobre el cual el usuario está preguntando."
                }
            },
            "required": ["conclusion_text"]
        }
    },
    "strategic_alignment_session": {
    "handler_name": "_handle_strategic_alignment_session",
    "description": "Inicia una conversación interactiva con un analista de IA para analizar y refinar la tesis de un informe borrador.",
    "parameters": {
        "type": "object",
        "properties": {
            "report_keyword": {
                "type": "string",
                "description": "El tópico (ej. 'clp' o 'cobre') para el cual se iniciará la sesión de alineamiento."
            }
        },
        "required": ["report_keyword"]
    }
},



    # --- Flujos de Comunicación y Búsqueda ---
    "send_report": {
        "handler_name": "_handle_send_report",
        "description": "Envía el último informe final a un contacto o a un segmento de contactos.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "El tópico del informe a enviar."
                },
                "recipient": {
                    "type": "string",
                    "description": "El nombre del contacto o del segmento de contactos (ej. 'Juan Perez' o 'Clientes Premium')."
                }
            },
            "required": ["report_keyword", "recipient"]
        }
    },

    "list_contacts": {
        "handler_name": "_handle_list_contacts",
        "description": "Muestra la lista de contactos disponibles de Airtable.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },

    # --- Flujos de Análisis Independientes ---
    
    "run_fair_value_analysis": {
        "handler_name": "_handle_run_specialist_analysis", # <-- Debe apuntar al genérico
        "description": "Ejecuta el análisis de Fair Value y genera su informe final.",
        "parameters": {
            "type": "object",
            "properties": { "report_keyword": { "type": "string", "description": "El activo para el análisis, ej. 'fair_value_clp'." }},
            "required": ["report_keyword"]
        },
    },  
    
    "run_technical_committee": {
        "handler_name": "_handle_run_technical_committee",
        "description": "Ejecuta el motor de análisis del comité técnico para un activo específico.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "La palabra clave de la definición del informe a ejecutar, ej: 'comite_tecnico_clp'."
                }
            },
            "required": ["report_keyword"]
        }
    },
    
    "generate_consolidated_report": {
        "handler_name": "_handle_generate_consolidated_report",
        "description": "Genera un reporte consolidado independiente basado en los datos base ya generados por el comité técnico. No re-ejecuta análisis técnico.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_keyword": {
                    "type": "string",
                    "description": "La palabra clave del reporte para generar consolidado, ej: 'comite_tecnico_mercado'."
                }
            },
            "required": ["report_keyword"]
        }
    },
    

    # --- Flujos de Conversación General ---
    "social_response": {
        "handler_name": "_handle_social_response",
        "description": "Se utiliza para responder a interacciones sociales simples como saludos, agradecimientos o despedidas.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    "out_of_domain_response": {
        "handler_name": "_handle_out_of_domain_response",
        "description": "Se utiliza cuando la petición del usuario no corresponde a ninguna de las capacidades del sistema.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
}
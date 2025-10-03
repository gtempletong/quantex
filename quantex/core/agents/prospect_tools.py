#!/usr/bin/env python3

"""
Registry de herramientas para QuantexAgent
Wrapper functions que llaman a MCPs existentes
"""

import json
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class ProspectTools:
    """
    Registry de herramientas para QuantexAgent
    Cada herramienta es un wrapper que llama a MCPs existentes
    """
    
    def __init__(self):
        self.tools_registry = {
            'supabase_query': self.supabase_query,
            'find_prospects': self.find_prospects, 
            'gmail_send_email': self.gmail_send_email,
            'brevo_send_email': self.brevo_send_email,
            'airtable_create_record': self.airtable_create_record
        }
        
        print("🔧 ProspectTools initialized")
        
    def execute_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """
        Ejecuta una herramienta por nombre con parámetros
        """
        if tool_name not in self.tools_registry:
            return {
                "ok": False,
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.tools_registry.keys())
            }
        
        try:
            func = self.tools_registry[tool_name]
            result = func(**params)
            
            return {
                "ok": True,
                "tool": tool_name,
                "result": result,
                "timestamp": self._timestamp()
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "tool": tool_name,
                "timestamp": self._timestamp()
            }
    
    def supabase_query(self, sql: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Ejecuta query SQL en Supabase
        En producción: llamaría al MCP de Supabase
        """
        print(f"📊 Supabase Query (dry_run={dry_run}): {sql[:100]}...")
        
        # Simulación de ejecución
        await_time = 1.0 if dry_run else 2.0
        import time
        time.sleep(min(await_time, 0.1))
        
        # Datos simulados de Gavin Templeton
        if "gavin" in sql.lower() or "templeton" in sql.lower():
            mock_data = [
                {
                    "id": 976,
                    "rut_empresa": "10097641-2",
                    "nombre_contacto": "Gavin Templeton",
                    "email_contacto": "gavintempletong@gmail.com",
                    "cargo_contacto": "Desarrollador", 
                    "razon_social": "Testing Company SA",
                    "actividad_economica": "Technology",
                    "region": "Región Metropolitana"
                }
            ]
        elif "ceo" in sql.lower():
            mock_data = [
                {
                    "id": 1,
                    "nombre_contacto": "María González",
                    "email_contacto": "maria.gonzalez@banco.com",
                    "cargo_contacto": "CEO",
                    "razon_social": "Banco Santander Chile",
                    "actividad_economica": "Banking"
                }
            ]
        else:
            mock_data = []
        
        return {
            "sql_executed": sql,
            "rows_returned": len(mock_data),
            "data": mock_data,
            "dry_run": dry_run,
            "execution_time": "~1s"
        }
    
    def find_prospects(self, criteria: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """
        Busca prospectos con criterios específicos
        """
        print(f"🔍 Finding prospects with criteria: {criteria}")
        
        # Genera SQL desde criterios
        sql_conditions = []
        
        if "name" in criteria:
            sql_conditions.append(f"nombre_contacto ILIKE '%{criteria['name']}%'")
        if "role" in criteria:
            sql_conditions.append(f"cargo_contacto ILIKE '%{criteria['role']}%'")
        if "industry" in criteria:
            sql_conditions.append(f"actividad_economica ILIKE '%{criteria['industry']}%'")
        if "location" in criteria:
            sql_conditions.append(f"region ILIKE '%{criteria['location']}%'")
            
        if not sql_conditions:
            sql_conditions.append("1=1")  # Sin filtros específicos
            
        sql_conditions.append("email_contacto IS NOT NULL AND email_contacto != ''")
        
        sql = f"""
        SELECT p.id, p.nombre_contacto, p.email_contacto, p.cargo_contacto, p.rut_empresa,
               e.razon_social, e.actividad_economica, e.region
        FROM personas p 
        LEFT JOIN empresas e ON p.rut_empresa = e.rut_empresa
        WHERE {' AND '.join(sql_conditions)}
        ORDER BY p.nombre_contacto
        LIMIT 50
        """
        
        # Ejecuta query usando supabase_query
        return self.supabase_query(sql, dry_run=dry_run)
    
    def gmail_send_email(self, to: str, subject: str, body: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Envía email via Gmail MCP
        """
        print(f"📧 Gmail Email (dry_run={dry_run}) to: {to}")
        print(f"   Subject: {subject}")
        
        import time
        time.sleep(0.5)
        
        return {
            "to": to,
            "subject": subject,
            "body": body,
            "sent": not dry_run,
            "message_id": f"gmail_{int(time.time())}" if not dry_run else None,
            "dry_run": dry_run,
            "tool": "gmail"
        }
        
    def brevo_send_email(self, to: str, subject: str, html_content: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Envía email transaccional via Brevo MCP
        """
        print(f"📧 Brevo Email (dry_run={dry_run}) to: {to}")
        print(f"   Subject: {subject}")
        
        import time  
        time.sleep(0.5)
        
        return {
            "to": to,
            "subject": subject, 
            "html_content": html_content,
            "sent": not dry_run,
            "message_id": f"brevo_{int(time.time())}" if not dry_run else None,
            "dry_run": dry_run,
            "tool": "brevo"
        }
        
    def airtable_create_record(self, table: str, fields: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """
        Crea registro en Airtable MCP  
        """
        print(f"📝 Airtable Record (dry_run={dry_run}) in table: {table}")
        print(f"   Fields: {json.dumps(fields, indent=2)}")
        
        import time
        time.sleep(0.3)
        
        return {
            "table": table,
            "fields": fields,
            "created": not dry_run,
            "record_id": f"airtable_{int(time.time())}" if not dry_run else None,
            "dry_run": dry_run,
            "tool": "airtable"
        }
        
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Retorna lista de herramientas disponibles con sus parámetros
        """
        return {
            "supabase_query": {
                "description": "Execute SQL query in Supabase",
                "params": ["sql", "dry_run"], 
                "required": ["sql"]
            },
            "find_prospects": {
                "description": "Search prospects with criteria",
                "params": ["criteria", "dry_run"],
               <｜tool▁sep｜>required": ["criteria"]
            },
            "gmail_send_email": {
                "description": "Send email via Gmail",
                "params": ["to", "subject", "body", "dry_run"],
                "required": ["to", "subject", "body"]
            },
            "brevo_send_email": {
                "description": "Send transactional email via Brevo", 
                "params": ["to", "subject", "html_content", "dry_run"],
                "required": ["to", "subject", "html_content"]
            },
            "airtable_create_record": {
                "description": "Create record in Airtable",
                "params": ["table", "fields", "dry_run"],
                "required": ["table", "fields"]
            }
        }
        
    def _timestamp(self) -> str:
        """Genera timestamp actual"""
        import datetime
        return datetime.datetime.now().isoformat()

# Instancia global para usar en el Agent
prospect_tools = ProspectTools()



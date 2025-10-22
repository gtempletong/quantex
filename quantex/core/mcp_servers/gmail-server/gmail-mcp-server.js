#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema
} from '@modelcontextprotocol/sdk/types.js';

// Configuración de Gmail usando tus credenciales existentes
const GMAIL_CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || './google_credentials.json';
const GMAIL_USER_EMAIL = process.env.GMAIL_USER_EMAIL || 'templetonglen@gmail.com';

class QuantexGmailServer {
  constructor() {
    this.server = new Server(
      {
        name: 'quantex-gmail-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    // Listar herramientas disponibles
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'send_email',
            description: 'Envía un email usando Gmail API integrada',
            inputSchema: {
              type: 'object',
              properties: {
                to: {
                  type: 'string',
                  description: 'Dirección de email destinatario'
                },
                subject: {
                  type: 'string', 
                  description: 'Asunto del email'
                },
                body: {
                  type: 'string',
                  description: 'Cuerpo del email (HTML)'
                },
                attachment_url: {
                  type: 'string',
                  description: 'URL del PDF para adjuntar'
                },
                from_email: {
                  type: 'string',
                  description: 'Email remitente (opcional)'
                },
                tracking_id: {
                  type: 'string',
                  description: 'ID de tracking opcional'
                }
              },
              required: ['to', 'subject', 'body']
            }
          },
          {
            name: 'search_emails',
            description: 'Busca emails en Gmail usando queries específicas',
            inputSchema: {
              type: 'object',
              properties: {
                query: {
                  type: 'string',
                  description: 'Query de búsqueda Gmail (ej: "from:cliente@empresa.com")'
                },
                max_results: {
                  type: 'number',
                  description: 'Máximo número de resultados (default: 10)'
                }
              },
              required: ['query']
            }
          },
          {
            name: 'get_unread_count',
            description: 'Obtiene el número de emails no leídos',
            inputSchema: {
              type: 'object',
              properties: {},
              required: []
            }
          },
          {
            name: 'check_email_status',
            description: 'Verifica el estado de lectura de un email específico',
            inputSchema: {
              type: 'object',
              properties: {
                message_id: {
                  type: 'string',
                  description: 'ID del mensaje de Gmail'
                }
              },
              required: ['message_id']
            }
          }
        ]
      };
    });

    // Manejador de llamadas a herramientas
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'send_email':
            return await this.sendEmail(args);
          case 'search_emails':
            return await this.searchEmails(args);
          case 'get_unread_count':
            return await this.getUnreadCount();
          case 'check_email_status':
            return await this.checkEmailStatus(args);
          default:
            throw new Error(`Herramienta desconocida: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `❌ Error ejecutando ${name}: ${error.message}`
            }
          ]
        };
      }
    });
  }

  async sendEmail(args) {
    const { to, subject, body, attachment_url, from_email, tracking_id } = args;
    
    // Importar y usar tu GmailSender existente
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const { writeFileSync, unlinkSync } = await import('fs');
    const { tmpdir } = await import('os');
    const { join } = await import('path');
    const execAsync = promisify(exec);

    // Crear archivo temporal para el cuerpo del email
    const tempFile = join(tmpdir(), `email_body_${Date.now()}.txt`);
    try {
      writeFileSync(tempFile, body, 'utf8');
      
      const command = `python "base/scripts/gmail_sender.py" --to "${to}" --subject "${subject}" --body-file "${tempFile}" ${from_email ? `--from "${from_email}"` : ''} ${attachment_url ? `--attachment-url "${attachment_url}"` : ''} ${tracking_id ? `--track "${tracking_id}"` : ''}`;

      console.log(`🔍 Comando ejecutado: ${command}`);
      console.log(`📄 Contenido del archivo: ${body}`);

      const { stdout, stderr } = await execAsync(command);
      
      return {
        content: [
          {
            type: 'text',
            text: `✅ Email enviado exitosamente a ${to}\n📧 Subject: ${subject}\n${stdout}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error enviando email: ${error.message}`
          }
        ]
      };
    } finally {
      // Limpiar archivo temporal
      try {
        unlinkSync(tempFile);
      } catch (e) {
        // Ignorar errores de limpieza
      }
    }
  }

  async searchEmails(args) {
    const { query, max_results = 10 } = args;
    
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    const command = `python "base/scripts/gmail_monitor.py" --query "${query}" --max ${max_results}`;

    try {
      const { stdout, stderr } = await execAsync(command);
      
      return {
        content: [
          {
            type: 'text',
            text: `📧 Resultados de búsqueda para: "${query}"\n${stdout}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error buscando emails: ${error.message}`
          }
        ]
      };
    }
  }

  async getUnreadCount() {
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    try {
      const { stdout, stderr } = await execAsync(`python "base/scripts/gmail_monitor.py" --unread`);
      
      return {
        content: [
          {
            type: 'text',
            text: `📬 Email stats:\n${stdout}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error obteniendo stats: ${error.message}`
          }
        ]
      };
    }
  }

  async checkEmailStatus(args) {
    const { message_id } = args;
    
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    try {
      const { stdout, stderr } = await execAsync(`python "base/scripts/gmail_monitor.py" --status "${message_id}"`);
      
      return {
        content: [
          {
            type: 'text',
            text: `📊 Estado del email ${message_id}:\n${stdout}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ Error verificando estado: ${error.message}`
          }
        ]
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('🚀 Quantex Gmail MCP Server iniciado');
  }
}

const server = new QuantexGmailServer();
server.run().catch(console.error);


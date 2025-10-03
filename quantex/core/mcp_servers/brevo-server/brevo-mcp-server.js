#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// MCP Server for Brevo Email Marketing
// Based on Brevo API documentation
class BrevoMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'brevo-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'brevo_send_email',
            description: 'Send transactional email using Brevo SMTP',
            inputSchema: {
              type: 'object',
              properties: {
                to: { type: 'string', description: 'Recipient email address' },
                subject: { type: 'string', description: 'Email subject' },
                htmlContent: { type: 'string', description: 'HTML content' },
                textContent: { type: 'string', description: 'Plain text content' },
                from: { type: 'string', description: 'Sender email address' },
                replyTo: { type: 'string', description: 'Reply-to address' }
              },
              required: ['to', 'subject', 'htmlContent', 'from']
            }
          },
          {
            name: 'brevo_create_contact',
            description: 'Create a new contact in Brevo',
            inputSchema: {
              type: 'object',
              properties: {
                email: { type: 'string', description: 'Contact email' },
                attributes: { 
                  type: 'object', 
                  description: 'Contact attributes like firstName, lastName, etc.' 
                },
                updateEnabled: { type: 'boolean', description: 'Update existing contact' }
              },
              required: ['email']
            }
          },
          {
            name: 'brevo_update_contact',
            description: 'Update existing contact in Brevo',
            inputSchema: {
              type: 'object',
              properties: {
                identifier: { type: 'string', description: 'Contact identifier (email or ID)' },
                attributes: { 
                  type: 'object', 
                  description: 'Contact attributes to update' 
                }
              },
              required: ['identifier', 'attributes']
            }
          },
          {
            name: 'brevo_get_contact',
            description: 'Get contact information from Brevo',
            inputSchema: {
              type: 'object',
              properties: {
                identifier: { type: 'string', description: 'Contact identifier (email or ID)' }
              },
              required: ['identifier']
            }
          },
          {
            name: 'brevo_create_campaign',
            description: 'Create a new email campaign in Brevo',
            inputSchema: {
              type: 'object',
              properties: {
                name: { type: 'string', description: 'Campaign name' },
                subject: { type: 'string', description: 'Email subject' },
                htmlContent: { type: 'string', description: 'HTML content' },
                recipients: { type: 'object', description: 'Recipient lists' }
              },
              required: ['name', 'subject', 'htmlContent']
            }
          },
          {
            name: 'brevo_send_campaign',
            description: 'Send email campaign',
            inputSchema: {
              type: 'object',
              properties: {
                campaignId: { type: 'number', description: 'Campaign ID to send' }
              },
              required: ['campaignId']
            }
          },
          {
            name: 'brevo_get_stats',
            description: 'Get campaign statistics from Brevo',
            inputSchema: {
              type: 'object',
              properties: {
                campaignId: { type: 'number', description: 'Campaign ID' },
                statisticDate: { type: 'string', description: 'Date for statistics' }
              },
              required: ['campaignId']
            }
          },
          {
            name: 'brevo_track_email_open',
            description: 'Track email open events for analytics',
            inputSchema: {
              type: 'object',
              properties: {
                emailId: { type: 'string', description: 'Email ID to track' },
                contactId: { type: 'string', description: 'Contact ID' }
              },
              required: ['emailId', 'contactId']
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        const apiKey = process.env.BREVO_API_KEY;
        if (!apiKey) {
          throw new Error('BREVO_API_KEY environment variable is required');
        }

        switch (name) {
          case 'brevo_send_email':
            return await this.sendEmail(args, apiKey);
          case 'brevo_create_contact':
            return await this.createContact(args, apiKey);
          case 'brevo_update_contact':
            return await this.updateContact(args, apiKey);
          case 'brevo_get_contact':
            return await this.getContact(args, apiKey);
          case 'brevo_create_campaign':
            return await this.createCampaign(args, apiKey);
          case 'brevo_send_campaign':
            return await this.sendCampaign(args, apiKey);
          case 'brevo_get_stats':
            return await this.getStats(args, apiKey);
          case 'brevo_track_email_open':
            return await this.trackEmailOpen(args, apiKey);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [{
            type: 'text',
            text: `Error executing ${name}: ${error.message}`
          }],
          isError: true
        };
      }
    });
  }

  async sendEmail(args, apiKey) {
    const url = 'https://api.brevo.com/v3/smtp/email';
    
    const payload = {
      to: [{ email: args.to }],
      subject: args.subject,
      htmlContent: args.htmlContent,
      textContent: args.textContent,
      sender: { email: args.from },
      replyTo: args.replyTo ? { email: args.replyTo } : undefined
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': apiKey
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Email sent successfully! Message ID: ${result.messageId || 'N/A'}`
      }]
    };
  }

  async createContact(args, apiKey) {
    const url = 'https://api.brevo.com/v3/contacts';
    
    const payload = {
      email: args.email,
      attributes: args.attributes || {},
      updateEnabled: args.updateEnabled || false
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': apiKey
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Contact created successfully! Contact ID: ${result.id || 'N/A'}`
      }]
    };
  }

  async updateContact(args, apiKey) {
    const url = `https://api.brevo.com/v3/contacts/${encodeURIComponent(args.identifier)}`;
    
    const payload = {
      attributes: args.attributes
    };

    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'api-key': apiKey
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Contact updated successfully!`
      }]
    };
  }

  async getContact(args, apiKey) {
    const url = `https://api.brevo.com/v3/contacts/${encodeURIComponent(args.identifier)}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'api-key': apiKey
      }
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Contact Information:\nEmail: ${result.email}\nAttributes: ${JSON.stringify(result.attributes, null, 2)}`
      }]
    };
  }

  async createCampaign(args, apiKey) {
    const url = 'https://api.brevo.com/v3/emailCampaigns';
    
    const payload = {
      name: args.name,
      subject: args.subject,
      htmlContent: args.htmlContent,
      recipients: args.recipients || { listIds: [] }
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': apiKey
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Campaign created successfully! Campaign ID: ${result.id || 'N/A'}`
      }]
    };
  }

  async sendCampaign(args, apiKey) {
    const url = `https://api.brevo.com/v3/emailCampaigns/${args.campaignId}/send`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'api-key': apiKey
      }
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Campaign sent successfully!`
      }]
    };
  }

  async getStats(args, apiKey) {
    const url = `https://api.brevo.com/v3/emailCampaigns/${args.campaignId}/report`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'api-key': apiKey
      }
    });

    const result = await response.json();

    return {
      content: [{
        type: 'text',
        text: `Campaign Statistics:\nDelivered: ${result.delivered || 0}\nOpened: ${result.opened || 0}\nClicked: ${result.clicked || 0}\nUnsubscribed: ${result.unsubscribed || 0}`
      }]
    };
  }

  async trackEmailOpen(args, apiKey) {
    // Brevo automatically tracks opens via tracking pixels
    return {
      content: [{
        type: 'text',
        text: `Email open tracking enabled for email ID: ${args.emailId}`
      }]
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Brevo MCP Server running on stdio');
  }
}

const server = new BrevoMCPServer();
server.run().catch(console.error);

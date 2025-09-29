#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import Airtable from 'airtable';

// Configuración de Airtable
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

// Inicializar Airtable
const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

// Crear servidor MCP
const server = new Server({
  name: 'airtable-mcp-server',
  version: '1.0.0'
}, {
  capabilities: {
    tools: {}
  }
});

// Definir herramientas disponibles
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'airtable_get_records',
        description: 'Get records from an Airtable table',
        inputSchema: {
          type: 'object',
          properties: {
            tableName: {
              type: 'string',
              description: 'Name of the Airtable table'
            },
            maxRecords: {
              type: 'number',
              description: 'Maximum number of records to return (default: 100)',
              default: 100
            }
          },
          required: ['tableName']
        }
      },
      {
        name: 'airtable_update_record',
        description: 'Update a record in Airtable',
        inputSchema: {
          type: 'object',
          properties: {
            tableName: {
              type: 'string',
              description: 'Name of the Airtable table'
            },
            recordId: {
              type: 'string',
              description: 'ID of the record to update'
            },
            fields: {
              type: 'object',
              description: 'Fields to update'
            }
          },
          required: ['tableName', 'recordId', 'fields']
        }
      },
      {
        name: 'airtable_create_record',
        description: 'Create a new record in Airtable',
        inputSchema: {
          type: 'object',
          properties: {
            tableName: {
              type: 'string',
              description: 'Name of the Airtable table'
            },
            fields: {
              type: 'object',
              description: 'Fields for the new record'
            }
          },
          required: ['tableName', 'fields']
        }
      },
      {
        name: 'airtable_search_records',
        description: 'Search records in Airtable by field value',
        inputSchema: {
          type: 'object',
          properties: {
            tableName: {
              type: 'string',
              description: 'Name of the Airtable table'
            },
            fieldName: {
              type: 'string',
              description: 'Name of the field to search'
            },
            fieldValue: {
              type: 'string',
              description: 'Value to search for'
            }
          },
          required: ['tableName', 'fieldName', 'fieldValue']
        }
      }
    ]
  };
});

// Manejar llamadas a herramientas
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'airtable_get_records':
        return await getRecords(args.tableName, args.maxRecords || 100);
      
      case 'airtable_update_record':
        return await updateRecord(args.tableName, args.recordId, args.fields);
      
      case 'airtable_create_record':
        return await createRecord(args.tableName, args.fields);
      
      case 'airtable_search_records':
        return await searchRecords(args.tableName, args.fieldName, args.fieldValue);
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`
        }
      ],
      isError: true
    };
  }
});

// Funciones helper
async function getRecords(tableName, maxRecords) {
  const records = [];
  
  await base(tableName).select({
    maxRecords: maxRecords
  }).eachPage((pageRecords, fetchNextPage) => {
    pageRecords.forEach(record => {
      records.push({
        id: record.id,
        fields: record.fields
      });
    });
    fetchNextPage();
  });

  return {
    content: [
      {
        type: 'text',
        text: `Found ${records.length} records in table "${tableName}":\n\n${JSON.stringify(records, null, 2)}`
      }
    ]
  };
}

async function updateRecord(tableName, recordId, fields) {
  const record = await base(tableName).update(recordId, fields);
  
  return {
    content: [
      {
        type: 'text',
        text: `Updated record ${recordId} in table "${tableName}":\n\n${JSON.stringify(record.fields, null, 2)}`
      }
    ]
  };
}

async function createRecord(tableName, fields) {
  const record = await base(tableName).create(fields);
  
  return {
    content: [
      {
        type: 'text',
        text: `Created new record in table "${tableName}":\n\n${JSON.stringify(record.fields, null, 2)}`
      }
    ]
  };
}

async function searchRecords(tableName, fieldName, fieldValue) {
  const records = [];
  
  await base(tableName).select({
    filterByFormula: `{${fieldName}} = "${fieldValue}"`,
    maxRecords: 100
  }).eachPage((pageRecords, fetchNextPage) => {
    pageRecords.forEach(record => {
      records.push({
        id: record.id,
        fields: record.fields
      });
    });
    fetchNextPage();
  });

  return {
    content: [
      {
        type: 'text',
        text: `Found ${records.length} records matching ${fieldName} = "${fieldValue}" in table "${tableName}":\n\n${JSON.stringify(records, null, 2)}`
      }
    ]
  };
}

// Iniciar servidor
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Airtable MCP server running on stdio');
}

main().catch(console.error);
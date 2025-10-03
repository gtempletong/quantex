#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';

// Configuración de Phantombuster
const PHANTOMBUSTER_API_KEY = process.env.PHANTOMBUSTER_API_KEY;

// Crear servidor MCP
const server = new Server({
  name: 'phantombuster-mcp-server',
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
        name: 'phantombuster_launch_phantom',
        description: 'Launch a Phantombuster phantom',
        inputSchema: {
          type: 'object',
          properties: {
            phantomId: {
              type: 'string',
              description: 'ID of the phantom to launch'
            },
            payload: {
              type: 'object',
              description: 'Payload for the phantom'
            }
          },
          required: ['phantomId', 'payload']
        }
      },
      {
        name: 'phantombuster_get_container_status',
        description: 'Get status of a phantom container',
        inputSchema: {
          type: 'object',
          properties: {
            containerId: {
              type: 'string',
              description: 'ID of the container'
            }
          },
          required: ['containerId']
        }
      },
      {
        name: 'phantombuster_get_containers',
        description: 'Get list of containers for a phantom',
        inputSchema: {
          type: 'object',
          properties: {
            phantomId: {
              type: 'string',
              description: 'ID of the phantom'
            }
          },
          required: ['phantomId']
        }
      },
      {
        name: 'phantombuster_get_results',
        description: 'Get results from a phantom container',
        inputSchema: {
          type: 'object',
          properties: {
            containerId: {
              type: 'string',
              description: 'ID of the container'
            }
          },
          required: ['containerId']
        }
      },
      {
        name: 'phantombuster_get_phantom_info',
        description: 'Get information about a phantom',
        inputSchema: {
          type: 'object',
          properties: {
            phantomId: {
              type: 'string',
              description: 'ID of the phantom'
            }
          },
          required: ['phantomId']
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
      case 'phantombuster_launch_phantom':
        return await launchPhantom(args.phantomId, args.payload);
      
      case 'phantombuster_get_container_status':
        return await getContainerStatus(args.containerId);
      
      case 'phantombuster_get_containers':
        return await getContainers(args.phantomId);
      
      case 'phantombuster_get_results':
        return await getResults(args.containerId);
      
      case 'phantombuster_get_phantom_info':
        return await getPhantomInfo(args.phantomId);
      
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

// Funciones helper para Phantombuster
async function launchPhantom(phantomId, payload) {
  const response = await fetch(`https://api.phantombuster.com/api/v1/agent/${phantomId}/launch`, {
    method: 'POST',
    headers: {
      'X-Phantombuster-Key-1': PHANTOMBUSTER_API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  
  return {
    content: [
      {
        type: 'text',
        text: `Phantom launched successfully:\n\n${JSON.stringify(result, null, 2)}`
      }
    ]
  };
}

async function getContainerStatus(containerId) {
  const response = await fetch(`https://api.phantombuster.com/api/v2/containers/fetch?id=${containerId}`, {
    headers: {
      'X-Phantombuster-Key-1': PHANTOMBUSTER_API_KEY
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  
  return {
    content: [
      {
        type: 'text',
        text: `Container status:\n\n${JSON.stringify(result, null, 2)}`
      }
    ]
  };
}

async function getContainers(phantomId) {
  const response = await fetch(`https://api.phantombuster.com/api/v1/agent/${phantomId}/containers`, {
    headers: {
      'X-Phantombuster-Key-1': PHANTOMBUSTER_API_KEY
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  
  return {
    content: [
      {
        type: 'text',
        text: `Containers for phantom ${phantomId}:\n\n${JSON.stringify(result, null, 2)}`
      }
    ]
  };
}

async function getResults(containerId) {
  // Primero obtener información del container
  const containerResponse = await fetch(`https://api.phantombuster.com/api/v2/containers/fetch?id=${containerId}`, {
    headers: {
      'X-Phantombuster-Key-1': PHANTOMBUSTER_API_KEY
    }
  });

  if (!containerResponse.ok) {
    throw new Error(`HTTP error! status: ${containerResponse.status}`);
  }

  const container = await containerResponse.json();
  
  // Obtener resultados desde S3
  if (container.result && container.result.s3Url) {
    const resultsResponse = await fetch(container.result.s3Url);
    const results = await resultsResponse.text();
    
    return {
      content: [
        {
          type: 'text',
          text: `Results from container ${containerId}:\n\n${results}`
        }
      ]
    };
  } else {
    return {
      content: [
        {
          type: 'text',
          text: `No results available for container ${containerId}`
        }
      ]
    };
  }
}

async function getPhantomInfo(phantomId) {
  const response = await fetch(`https://api.phantombuster.com/api/v1/agent/${phantomId}`, {
    headers: {
      'X-Phantombuster-Key-1': PHANTOMBUSTER_API_KEY
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  
  return {
    content: [
      {
        type: 'text',
        text: `Phantom information:\n\n${JSON.stringify(result, null, 2)}`
      }
    ]
  };
}

// Iniciar servidor
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Phantombuster MCP server running on stdio');
}

main().catch(console.error);
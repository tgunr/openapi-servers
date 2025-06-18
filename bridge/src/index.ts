// src/index.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  ListToolsRequestSchema, 
  CallToolRequestSchema
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

// Infer types from schemas
type ListToolsRequest = z.infer<typeof ListToolsRequestSchema>;
type CallToolRequest = z.infer<typeof CallToolRequestSchema>;
import axios from 'axios';
import SwaggerParser from 'swagger-parser';

class OpenAPIMCPServer {
  private server: Server;
  private apiSpec: any;
  private baseUrl: string;

  constructor(baseUrl: string, openApiSpecUrl: string) {
    this.baseUrl = baseUrl;
    this.server = new Server(
      {
        name: "openapi-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
    this.loadApiSpec(openApiSpecUrl);
  }

  private async loadApiSpec(specUrl: string) {
    try {
      this.apiSpec = await (SwaggerParser as any).dereference(specUrl);
      this.registerToolsFromSpec();
    } catch (error) {
      console.error('Failed to load OpenAPI spec:', error);
    }
  }

  private registerToolsFromSpec() {
    // This method is no longer needed as we handle all tools dynamically
    // in the CallToolRequestSchema handler
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async (request: ListToolsRequest) => {
      const tools: any[] = [];

      if (this.apiSpec?.paths) {
        Object.entries(this.apiSpec.paths).forEach(([path, methods]: [string, any]) => {
          Object.entries(methods).forEach(([method, operation]: [string, any]) => {
            if (typeof operation === 'object' && operation && operation.operationId) {
              tools.push({
                name: operation.operationId,
                description: operation.summary || operation.description || `${method.toUpperCase()} ${path}`,
                inputSchema: this.buildInputSchema(operation),
              });
            }
          });
        });
      }

      return { tools };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
      return this.handleCallTool(request);
    });
  }

  private async handleCallTool(request: CallToolRequest) {
    try {
      const { name, arguments: args } = request.params;

      // Find the operation in the API spec
      let targetOperation: any = null;
      let targetPath: string = '';
      let targetMethod: string = '';

      if (this.apiSpec?.paths) {
        outer: for (const [path, methods] of Object.entries(this.apiSpec.paths)) {
          for (const [method, operation] of Object.entries(methods as any)) {
            if (typeof operation === 'object' && operation && (operation as any).operationId === name) {
              targetOperation = operation;
              targetPath = path;
              targetMethod = method;
              break outer;
            }
          }
        }
      }

      if (!targetOperation) {
        throw new Error(`Tool '${name}' not found`);
      }

      // Build the URL with path parameters
      let url = this.baseUrl + targetPath;
      if (args?.pathParams) {
        Object.entries(args.pathParams).forEach(([key, value]) => {
          url = url.replace(`{${key}}`, encodeURIComponent(String(value)));
        });
      }

      // Make the API call
      const response = await axios({
        method: targetMethod.toUpperCase(),
        url,
        params: args?.queryParams || {},
        data: args?.body || {},
        headers: args?.headers || {},
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response.data, null, 2),
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error calling tool '${request.params.name}': ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  private buildInputSchema(operation: any) {
    const properties: any = {};

    // Add path parameters
    if (operation.parameters) {
      const pathParams = operation.parameters.filter((p: any) => p.in === 'path');
      const queryParams = operation.parameters.filter((p: any) => p.in === 'query');

      if (pathParams.length > 0) {
        properties.pathParams = {
          type: "object",
          properties: pathParams.reduce((acc: any, param: any) => {
            acc[param.name] = { type: param.schema?.type || "string", description: param.description };
            return acc;
          }, {}),
        };
      }

      if (queryParams.length > 0) {
        properties.queryParams = {
          type: "object",
          properties: queryParams.reduce((acc: any, param: any) => {
            acc[param.name] = { type: param.schema?.type || "string", description: param.description };
            return acc;
          }, {}),
        };
      }
    }

    // Add request body
    if (operation.requestBody) {
      properties.body = {
        type: "object",
        description: "Request body",
      };
    }

    return {
      type: "object",
      properties,
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("OpenAPI MCP Server running on stdio");
  }
}

// Usage
const server = new OpenAPIMCPServer(
  "http://localhost:8001", // Your OpenAPI server base URL
  "http://localhost:8001/openapi.json" // Your OpenAPI spec URL
);

server.run().catch(console.error);

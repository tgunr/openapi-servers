# Integrating MCP Bridges with Open WebUI and Ollama

This guide explains how to connect your OpenAPI services to Open WebUI through MCP bridges, enabling your chat interface to directly access filesystem operations, Confluence, Git, and other services.

## 🏗️ Architecture Overview

```
Open WebUI (8080) → Ollama (11434) → MCP Client → MCP Bridges → OpenAPI Services
```

## 📋 Prerequisites

1. ✅ Ollama running (port 11434)
2. ✅ Open WebUI running (port 8080) 
3. ✅ MCP Bridge Registry (port 9000)
4. ✅ OpenAPI services running (ports 8000-8007)

## 🔧 Integration Methods

### Method 1: MCP Tools Integration (Recommended)

Open WebUI supports MCP (Model Context Protocol) tools directly. Here's how to set it up:

#### Step 1: Create MCP Configuration for Open WebUI

```bash
# Create MCP config directory for Open WebUI
mkdir -p ~/.config/open-webui/mcp

# Create MCP servers configuration
cat > ~/.config/open-webui/mcp/servers.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
      "env": {
        "OPENAPI_BASE_URL": "http://localhost:8000",
        "OPENAPI_SPEC_URL": "http://localhost:8000/openapi.json",
        "BRIDGE_ID": "filesystem"
      }
    },
    "confluence": {
      "command": "node", 
      "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
      "env": {
        "OPENAPI_BASE_URL": "http://localhost:8002",
        "OPENAPI_SPEC_URL": "http://localhost:8002/openapi.json", 
        "BRIDGE_ID": "confluence"
      }
    },
    "git": {
      "command": "node",
      "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
      "env": {
        "OPENAPI_BASE_URL": "http://localhost:8003",
        "OPENAPI_SPEC_URL": "http://localhost:8003/openapi.json",
        "BRIDGE_ID": "git"
      }
    },
    "memory": {
      "command": "node",
      "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
      "env": {
        "OPENAPI_BASE_URL": "http://localhost:8004", 
        "OPENAPI_SPEC_URL": "http://localhost:8004/openapi.json",
        "BRIDGE_ID": "memory"
      }
    }
  }
}
EOF
```

#### Step 2: Create Open WebUI MCP Integration Script

```python
# Save as: mcp-openwebui-integration.py
#!/usr/bin/env python3
"""
Open WebUI MCP Integration
Enables Open WebUI to use MCP tools from OpenAPI bridges
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class OpenWebUIMCPIntegration:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "open-webui" / "mcp"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_available_bridges(self) -> List[Dict]:
        """Get available MCP bridges from registry"""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:9000/bridges")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('bridges', [])
        except Exception as e:
            print(f"Error getting bridges: {e}")
        return []
    
    def generate_mcp_config(self, bridges: List[Dict]) -> Dict:
        """Generate MCP configuration for Open WebUI"""
        config = {"mcpServers": {}}
        
        for bridge in bridges:
            if bridge.get('status') != 'running':
                continue
                
            server_name = bridge['openapi_server']['name'].lower().replace(' ', '_')
            config["mcpServers"][server_name] = {
                "command": "node",
                "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
                "env": {
                    "OPENAPI_BASE_URL": bridge['openapi_server']['base_url'],
                    "OPENAPI_SPEC_URL": bridge['openapi_server']['openapi_url'],
                    "BRIDGE_ID": bridge['id']
                }
            }
        
        return config
    
    async def setup_integration(self):
        """Set up MCP integration with Open WebUI"""
        print("🔧 Setting up Open WebUI MCP integration...")
        
        # Get available bridges
        bridges = await self.get_available_bridges()
        if not bridges:
            print("❌ No bridges found. Make sure the registry is running.")
            return False
            
        print(f"📋 Found {len(bridges)} bridges")
        
        # Generate configuration
        config = self.generate_mcp_config(bridges)
        
        # Save configuration
        config_file = self.config_dir / "servers.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"✅ MCP configuration saved to {config_file}")
        
        # Create environment file for Open WebUI
        env_file = self.config_dir / ".env"
        with open(env_file, 'w') as f:
            f.write("MCP_SERVERS_CONFIG=/Users/davec/.config/open-webui/mcp/servers.json\n")
            f.write("ENABLE_MCP_TOOLS=true\n")
            
        print(f"✅ Environment configuration saved to {env_file}")
        
        return True

if __name__ == "__main__":
    integration = OpenWebUIMCPIntegration()
    asyncio.run(integration.setup_integration())
```

### Method 2: Function Calling Integration

Create custom functions that Open WebUI can call:

#### Step 1: Create Function Definitions

```python
# Save as: openapi-functions.py
"""
OpenAPI Function Definitions for Open WebUI
These functions can be called directly from chat
"""

import httpx
import json
from typing import Dict, Any, List

async def call_openapi_tool(base_url: str, operation_id: str, **kwargs) -> Dict[str, Any]:
    """Generic function to call any OpenAPI operation"""
    try:
        async with httpx.AsyncClient() as client:
            # Get OpenAPI spec
            spec_response = await client.get(f"{base_url}/openapi.json")
            spec = spec_response.json()
            
            # Find the operation
            for path, methods in spec['paths'].items():
                for method, operation in methods.items():
                    if operation.get('operationId') == operation_id:
                        # Build request
                        url = f"{base_url}{path}"
                        
                        # Handle path parameters
                        if 'pathParams' in kwargs:
                            for key, value in kwargs['pathParams'].items():
                                url = url.replace(f'{{{key}}}', str(value))
                        
                        # Make request
                        response = await client.request(
                            method.upper(),
                            url,
                            params=kwargs.get('queryParams', {}),
                            json=kwargs.get('body', {}),
                            headers=kwargs.get('headers', {})
                        )
                        
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "data": response.json() if response.content else None
                        }
            
            return {"success": False, "error": f"Operation {operation_id} not found"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Specific function wrappers for common operations
async def read_file(path: str) -> Dict[str, Any]:
    """Read a file using the filesystem API"""
    return await call_openapi_tool(
        "http://localhost:8000",
        "read_file_read_file_post", 
        body={"path": path}
    )

async def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write to a file using the filesystem API"""
    return await call_openapi_tool(
        "http://localhost:8000",
        "write_file_write_file_post",
        body={"path": path, "content": content}
    )

async def list_directory(path: str) -> Dict[str, Any]:
    """List directory contents using the filesystem API"""
    return await call_openapi_tool(
        "http://localhost:8000", 
        "list_directory_list_directory_post",
        body={"path": path}
    )

async def search_confluence(query: str) -> Dict[str, Any]:
    """Search Confluence using the confluence API"""
    return await call_openapi_tool(
        "http://localhost:8002",
        "search_confluence_search_confluence_post",
        body={"query": query}
    )

async def git_status() -> Dict[str, Any]:
    """Get git status using the git API"""
    return await call_openapi_tool(
        "http://localhost:8003",
        "git_status_git_status_get"
    )
```

### Method 3: Ollama Functions Integration

Create Ollama function definitions that can be loaded:

#### Step 1: Create Ollama Function Schema

```json
// Save as: ollama-functions.json
{
  "functions": [
    {
      "name": "read_file",
      "description": "Read the contents of a file from the filesystem",
      "parameters": {
        "type": "object", 
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the file to read"
          }
        },
        "required": ["path"]
      },
      "implementation": {
        "type": "http",
        "url": "http://localhost:8000/read_file",
        "method": "POST",
        "body_template": {"path": "{{path}}"}
      }
    },
    {
      "name": "write_file", 
      "description": "Write content to a file",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string", 
            "description": "Path to write the file"
          },
          "content": {
            "type": "string",
            "description": "Content to write to the file"
          }
        },
        "required": ["path", "content"]
      },
      "implementation": {
        "type": "http",
        "url": "http://localhost:8000/write_file", 
        "method": "POST",
        "body_template": {"path": "{{path}}", "content": "{{content}}"}
      }
    },
    {
      "name": "list_directory",
      "description": "List contents of a directory",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Directory path to list"
          }
        },
        "required": ["path"]
      },
      "implementation": {
        "type": "http", 
        "url": "http://localhost:8000/list_directory",
        "method": "POST",
        "body_template": {"path": "{{path}}"}
      }
    },
    {
      "name": "search_confluence",
      "description": "Search for content in Confluence",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search query for Confluence"
          }
        },
        "required": ["query"]
      },
      "implementation": {
        "type": "http",
        "url": "http://localhost:8002/search", 
        "method": "POST",
        "body_template": {"query": "{{query}}"}
      }
    }
  ]
}
```

## 🚀 Setup Instructions

### Quick Setup Script

```bash
#!/bin/bash
# Save as: setup-openwebui-mcp.sh

echo "🔧 Setting up Open WebUI MCP Integration..."

# 1. Create MCP config directory
mkdir -p ~/.config/open-webui/mcp

# 2. Generate MCP configuration from registry
python3 - << 'EOF'
import asyncio
import httpx
import json
from pathlib import Path

async def setup():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9000/bridges")
            bridges = response.json().get('bridges', [])
            
        config = {"mcpServers": {}}
        for bridge in bridges:
            if bridge.get('status') == 'running':
                name = bridge['openapi_server']['name'].lower().replace(' ', '_')
                config["mcpServers"][name] = {
                    "command": "node",
                    "args": ["/Volumes/AI/openapi-servers/bridge/dist/index.js"],
                    "env": {
                        "OPENAPI_BASE_URL": bridge['openapi_server']['base_url'],
                        "OPENAPI_SPEC_URL": bridge['openapi_server']['openapi_url'],
                        "BRIDGE_ID": bridge['id']
                    }
                }
        
        config_file = Path.home() / ".config/open-webui/mcp/servers.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"✅ Generated MCP config with {len(config['mcpServers'])} bridges")
        
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(setup())
EOF

# 3. Create environment file
cat > ~/.config/open-webui/mcp/.env << 'EOF'
MCP_SERVERS_CONFIG=/Users/davec/.config/open-webui/mcp/servers.json
ENABLE_MCP_TOOLS=true
MCP_DEBUG=true
EOF

echo "✅ MCP integration configured"
echo "🔄 Restart Open WebUI to load MCP tools"
```

### Testing the Integration

1. **Test MCP Bridge Connection:**
```bash
# Test filesystem bridge
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
OPENAPI_BASE_URL=http://localhost:8000 \
OPENAPI_SPEC_URL=http://localhost:8000/openapi.json \
node /Volumes/AI/openapi-servers/bridge/dist/index.js
```

2. **Test Through Open WebUI:**
   - Open http://localhost:8080
   - Start a new chat
   - Try prompts like:
     - "List the files in my home directory"
     - "Read the contents of a specific file"
     - "Search Confluence for documentation"

## 💡 Usage Examples

### In Open WebUI Chat:

**File Operations:**
```
User: "List the files in /Users/davec/Documents"
Assistant: I'll list the files in your Documents directory...
[Uses filesystem MCP tool]
```

**Confluence Search:**
```
User: "Search our Confluence for 'API documentation'"  
Assistant: I'll search Confluence for API documentation...
[Uses confluence MCP tool]
```

**Git Operations:**
```
User: "What's the status of my git repository?"
Assistant: I'll check the git status...
[Uses git MCP tool]
```

## 🔧 Troubleshooting

### Common Issues:

1. **MCP Tools Not Available:**
   - Check if bridges are running: `curl http://localhost:9000/bridges`
   - Verify Open WebUI can access the config: `~/.config/open-webui/mcp/servers.json`

2. **Bridge Connection Errors:**
   - Test bridge manually: `node bridge/dist/index.js`
   - Check OpenAPI service status: `curl http://localhost:8000/openapi.json`

3. **Open WebUI Not Loading Tools:**
   - Restart Open WebUI service
   - Check logs: `docker logs open-webui` (if using Docker)

### Debug Commands:

```bash
# Check bridge registry
curl http://localhost:9000/stats

# Test individual bridge
OPENAPI_BASE_URL=http://localhost:8000 \
node /Volumes/AI/openapi-servers/bridge/dist/index.js

# Check Open WebUI logs
tail -f ~/.local/share/open-webui/logs/app.log
```

## 🎯 Next Steps

1. **Custom Functions:** Create specific function wrappers for your most-used operations
2. **RAG Integration:** Connect the external RAG service for document search
3. **Memory Integration:** Use the memory service for conversation persistence
4. **Workflow Automation:** Chain multiple API calls together

This integration turns your Open WebUI into a powerful interface that can directly interact with your filesystem, Confluence, Git repositories, and all your other OpenAPI services through natural language! 🚀


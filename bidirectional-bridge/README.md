# 🔄 Bi-directional OpenAPI ↔ MCP Bridge System

This system creates a unified ecosystem where OpenAPI servers and MCP servers can seamlessly call each other, enabling true bi-directional connectivity and interoperability.

## 🌟 Key Features

- **✅ OpenAPI → MCP**: OpenAPI servers can call MCP tool functions
- **✅ MCP → OpenAPI**: MCP servers can call OpenAPI endpoint operations  
- **🔍 Dynamic Discovery**: Automatically discovers both OpenAPI and MCP servers
- **🔌 Unified Interface**: Single bridge system managing all connections
- **📊 Real-time Monitoring**: Live status and statistics for all servers
- **🚀 Easy Integration**: RESTful API with comprehensive documentation

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│   OpenAPI       │    │  Bi-directional      │    │   MCP Servers   │
│   Servers       │◄──►│  Bridge System       │◄──►│                 │
│                 │    │  (Port 8100)         │    │                 │
│ • Filesystem    │    │                      │    │ • fetch         │
│ • Git           │    │ ┌──────────────────┐ │    │ • memory        │
│ • Confluence    │    │ │   Discovery &    │ │    │ • github        │
│ • Weather       │    │ │   Registry       │ │    │ • brave-search  │
│ • Time Utils    │    │ └──────────────────┘ │    │ • puppeteer     │
│ • etc...        │    │ ┌──────────────────┐ │    │ • etc...        │
│                 │    │ │  Call Routing &  │ │    │                 │
│                 │    │ │  Translation     │ │    │                 │
│                 │    │ └──────────────────┘ │    │                 │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
```

## 📋 Current System Status

**System Statistics** (as of setup):
- **MCP Servers**: 12 total, 2 running, 5 tools available
- **OpenAPI Servers**: 10 total, 10 online, 381 endpoints available

**Active Connections**:
- 🟢 **MCP**: mcp-server-fetch (1 tool), docker-mcp (4 tools)
- 🟢 **API**: Filesystem, Git, Confluence, Weather, Time Utils, Registry, etc.

## 🚀 Quick Start

### 1. Start the Bridge System

```bash
# Option 1: Use the setup script (recommended)
python3 setup-bidirectional-bridge.py

# Option 2: Manual start
cd bidirectional-bridge
pip install -r requirements.txt
python3 main.py
```

### 2. Verify System Status

```bash
# Check bridge system status
curl http://localhost:8100/stats

# List all available servers
curl http://localhost:8100/mcp-servers
curl http://localhost:8100/openapi-servers
```

### 3. Explore the Web Interface

Open http://localhost:8100/docs for the interactive API documentation.

## 🔧 Usage Examples

### OpenAPI → MCP Tool Calls

```bash
# Call MCP fetch tool from OpenAPI context
curl -X POST http://localhost:8100/call-mcp-tool \
  -H 'Content-Type: application/json' \
  -d '{
    "server_id": "mcp_c4206a5f",
    "tool_name": "fetch",
    "arguments": {
      "url": "https://api.github.com",
      "max_length": 1000
    }
  }'

# Use simplified proxy syntax
curl -X POST http://localhost:8100/proxy/mcp/mcp_c4206a5f/fetch \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://httpbin.org/json"}'
```

### MCP → OpenAPI Endpoint Calls

```bash
# Call OpenAPI filesystem from MCP context
curl -X POST http://localhost:8100/call-openapi \
  -H 'Content-Type: application/json' \
  -d '{
    "server_id": "openapi_b6e72a18",
    "operation_id": "list_directory_list_directory_post",
    "body": {"path": "/Users/davec/tmp"}
  }'

# Use simplified proxy syntax
curl -X POST http://localhost:8100/proxy/openapi/openapi_b6e72a18/read_file_read_file_post \
  -H 'Content-Type: application/json' \
  -d '{"path": "/Users/davec/test.txt"}'
```

## 📊 API Endpoints

### Discovery & Management

- `GET /` - Bridge system information and stats
- `GET /stats` - Detailed system statistics
- `POST /discover` - Trigger discovery of all servers
- `GET /mcp-servers` - List all MCP servers
- `GET /openapi-servers` - List all OpenAPI servers

### Server Management

- `POST /mcp-servers/{server_id}/start` - Start an MCP server
- `GET /mcp-servers/{server_id}/tools` - Get available tools
- `GET /openapi-servers/{server_id}/endpoints` - Get available endpoints

### Bi-directional Calls

- `POST /call-mcp-tool` - Call MCP tool (detailed syntax)
- `POST /call-openapi` - Call OpenAPI endpoint (detailed syntax)
- `POST /proxy/mcp/{server_id}/{tool_name}` - Call MCP tool (simple syntax)
- `POST /proxy/openapi/{server_id}/{operation_id}` - Call OpenAPI endpoint (simple syntax)

## 🔄 Integration Patterns

### Pattern 1: OpenAPI Server Calling MCP Tools

```python
# Inside an OpenAPI server endpoint
import httpx

async def enhanced_search(query: str):
    # Call MCP memory tool to get context
    async with httpx.AsyncClient() as client:
        memory_response = await client.post(
            "http://localhost:8100/proxy/mcp/memory_server/recall",
            json={"query": query}
        )
        
        # Call MCP search tool with context
        search_response = await client.post(
            "http://localhost:8100/proxy/mcp/brave_search/search", 
            json={"query": query, "count": 5}
        )
        
        return {
            "memory_context": memory_response.json(),
            "search_results": search_response.json()
        }
```

### Pattern 2: MCP Server Calling OpenAPI Endpoints

```python
# Inside an MCP tool implementation
import httpx

async def enhanced_file_tool(path: str):
    # Call OpenAPI filesystem to read file
    async with httpx.AsyncClient() as client:
        file_response = await client.post(
            "http://localhost:8100/proxy/openapi/filesystem/read_file_read_file_post",
            json={"path": path}
        )
        
        # Call OpenAPI summarizer to process content
        summary_response = await client.post(
            "http://localhost:8100/proxy/openapi/summarizer/summarize_post",
            json={"text": file_response.json()["data"]["content"]}
        )
        
        return {
            "file_content": file_response.json(),
            "summary": summary_response.json()
        }
```

## 🔐 Security Considerations

- **Access Control**: All calls go through the bridge system with centralized logging
- **Rate Limiting**: Built-in protection against excessive API calls
- **Input Validation**: Comprehensive validation for all requests
- **Error Handling**: Graceful degradation and detailed error messages

## 🛠️ Advanced Configuration

### Custom Server Discovery

```python
# Add custom OpenAPI server
curl -X POST http://localhost:8100/register-openapi \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Custom API",
    "base_url": "http://localhost:8888",
    "openapi_url": "http://localhost:8888/openapi.json"
  }'
```

### MCP Server Management

```python
# Start specific MCP server
curl -X POST http://localhost:8100/mcp-servers/mcp_12345/start

# Get available tools
curl http://localhost:8100/mcp-servers/mcp_12345/tools
```

## 📈 Monitoring & Debugging

### Real-time Status

```bash
# Watch system stats
watch -n 2 'curl -s http://localhost:8100/stats | jq'

# Monitor active connections
curl http://localhost:8100/stats | jq '.mcp_servers.running, .openapi_servers.online'
```

### Logs and Debugging

- Bridge system logs: Check console output where main.py is running
- Individual server logs: Check respective server log files
- API call tracing: Available through the web interface

## 🎯 Use Cases

### 1. **Enhanced AI Workflows**
- LLMs can seamlessly access both OpenAPI services and MCP tools
- Combine file operations (OpenAPI) with web search (MCP)
- Memory persistence (MCP) + data processing (OpenAPI)

### 2. **Microservices Integration**
- Bridge legacy OpenAPI services with modern MCP tools
- Create unified interfaces for heterogeneous systems
- Enable service-to-service communication across protocols

### 3. **Development & Testing**
- Test MCP tools using familiar REST API calls
- Prototype integrations without protocol constraints
- Debug complex multi-service workflows

## 🔮 Future Enhancements

- **WebSocket Support**: Real-time bidirectional streaming
- **Load Balancing**: Distribute calls across multiple server instances
- **Circuit Breakers**: Automatic failover and recovery
- **Metrics Dashboard**: Visual monitoring and analytics
- **Plugin System**: Custom call transformers and middleware

## 🤝 Contributing

This bi-directional bridge system demonstrates the power of unified ecosystems. Contributions welcome for:

- Additional protocol support
- Performance optimizations
- Security enhancements
- Monitoring improvements
- Documentation and examples

---

**🎉 You now have a unified OpenAPI ↔ MCP ecosystem where any server can call any other server, regardless of protocol!**


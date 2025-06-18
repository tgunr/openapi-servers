#!/usr/bin/env python3
"""
Bi-directional OpenAPI ↔ MCP Bridge System

This system creates a unified ecosystem where:
1. OpenAPI servers can call MCP server functions
2. MCP servers can call OpenAPI server endpoints
3. Both systems can discover and interact with each other dynamically
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import uuid
from dataclasses import dataclass, asdict
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MCPServerInfo:
    """Information about an MCP server"""
    id: str
    name: str
    command: List[str]
    description: str = ""
    tools: List[Dict] = None
    status: str = "stopped"  # stopped, starting, running, error
    process_id: Optional[int] = None
    last_health_check: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []

@dataclass
class OpenAPIServerInfo:
    """Information about an OpenAPI server"""
    id: str
    name: str
    base_url: str
    openapi_url: str
    description: str = ""
    endpoints: List[Dict] = None
    status: str = "unknown"  # unknown, online, offline, error
    last_seen: Optional[datetime] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []

class MCPToolRequest(BaseModel):
    """Request to call an MCP tool"""
    server_id: str
    tool_name: str
    arguments: Dict[str, Any] = {}

class OpenAPICallRequest(BaseModel):
    """Request to call an OpenAPI endpoint"""
    server_id: str
    operation_id: str
    path_params: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None

class BidirectionalBridge:
    """Main bridge system for OpenAPI ↔ MCP connectivity"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.mcp_servers: Dict[str, MCPServerInfo] = {}
        self.openapi_servers: Dict[str, OpenAPIServerInfo] = {}
        self.client_sessions: Dict[str, Any] = {}  # MCP client sessions
        
        # Load existing data
        self.load_data()
        
    def load_data(self):
        """Load persisted bridge data"""
        try:
            mcp_file = self.data_dir / "mcp_servers.json"
            if mcp_file.exists():
                with open(mcp_file) as f:
                    data = json.load(f)
                    for server_id, server_data in data.items():
                        if server_data.get("last_health_check"):
                            server_data["last_health_check"] = datetime.fromisoformat(
                                server_data["last_health_check"]
                            )
                        self.mcp_servers[server_id] = MCPServerInfo(**server_data)
                        
            openapi_file = self.data_dir / "openapi_servers.json"
            if openapi_file.exists():
                with open(openapi_file) as f:
                    data = json.load(f)
                    for server_id, server_data in data.items():
                        if server_data.get("last_seen"):
                            server_data["last_seen"] = datetime.fromisoformat(
                                server_data["last_seen"]
                            )
                        self.openapi_servers[server_id] = OpenAPIServerInfo(**server_data)
                        
            logger.info(f"Loaded {len(self.mcp_servers)} MCP servers and {len(self.openapi_servers)} OpenAPI servers")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def save_data(self):
        """Persist bridge data"""
        try:
            def json_encoder(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            mcp_file = self.data_dir / "mcp_servers.json"
            with open(mcp_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.mcp_servers.items()}, 
                         f, default=json_encoder, indent=2)
                
            openapi_file = self.data_dir / "openapi_servers.json"
            with open(openapi_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.openapi_servers.items()}, 
                         f, default=json_encoder, indent=2)
                         
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    async def discover_openapi_servers(self) -> List[OpenAPIServerInfo]:
        """Discover OpenAPI servers from the registry"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:9000/servers")
                if response.status_code == 200:
                    data = response.json()
                    servers = []
                    
                    for server_data in data.get('servers', []):
                        server_id = f"openapi_{uuid.uuid4().hex[:8]}"
                        server = OpenAPIServerInfo(
                            id=server_id,
                            name=server_data['name'],
                            base_url=server_data['base_url'],
                            openapi_url=server_data['openapi_url'],
                            description=server_data.get('description', ''),
                            status=server_data.get('status', 'unknown'),
                            last_seen=datetime.now()
                        )
                        
                        # Load OpenAPI spec and extract endpoints
                        await self.load_openapi_endpoints(server)
                        servers.append(server)
                        self.openapi_servers[server_id] = server
                    
                    self.save_data()
                    return servers
        except Exception as e:
            logger.error(f"Error discovering OpenAPI servers: {e}")
        return []
    
    async def load_openapi_endpoints(self, server: OpenAPIServerInfo):
        """Load endpoints from OpenAPI specification"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(server.openapi_url)
                if response.status_code == 200:
                    spec = response.json()
                    endpoints = []
                    
                    for path, methods in spec.get('paths', {}).items():
                        for method, operation in methods.items():
                            if isinstance(operation, dict) and operation.get('operationId'):
                                endpoints.append({
                                    'operation_id': operation['operationId'],
                                    'path': path,
                                    'method': method.upper(),
                                    'summary': operation.get('summary', ''),
                                    'description': operation.get('description', ''),
                                    'parameters': operation.get('parameters', [])
                                })
                    
                    server.endpoints = endpoints
        except Exception as e:
            logger.error(f"Error loading OpenAPI endpoints for {server.name}: {e}")
    
    async def discover_mcp_servers(self) -> List[MCPServerInfo]:
        """Discover MCP servers from Claude configuration"""
        try:
            config_file = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                    
                servers = []
                for server_name, server_config in config.get('mcpServers', {}).items():
                    server_id = f"mcp_{uuid.uuid4().hex[:8]}"
                    command = [server_config['command']] + server_config.get('args', [])
                    
                    server = MCPServerInfo(
                        id=server_id,
                        name=server_name,
                        command=command,
                        description=f"MCP server: {server_name}",
                        status="stopped"
                    )
                    
                    servers.append(server)
                    self.mcp_servers[server_id] = server
                
                self.save_data()
                return servers
        except Exception as e:
            logger.error(f"Error discovering MCP servers: {e}")
        return []
    
    async def start_mcp_server(self, server_id: str) -> bool:
        """Start an MCP server and establish connection"""
        if server_id not in self.mcp_servers:
            return False
            
        server = self.mcp_servers[server_id]
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            server.status = "starting"
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=server.command[0],
                args=server.command[1:],
                env=dict(subprocess.os.environ)
            )
            
            # Start the MCP server process
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    result = await session.initialize()
                    
                    # List available tools
                    tools_result = await session.list_tools()
                    server.tools = [
                        {
                            'name': tool.name,
                            'description': tool.description,
                            'input_schema': tool.inputSchema
                        }
                        for tool in tools_result.tools
                    ]
                    
                    # Store the session for later use
                    self.client_sessions[server_id] = session
                    
                    server.status = "running"
                    server.last_health_check = datetime.now()
                    self.save_data()
                    
                    logger.info(f"Started MCP server {server.name} with {len(server.tools)} tools")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to start MCP server {server.name}: {e}")
            server.status = "error"
            return False
    
    async def call_mcp_tool(self, request: MCPToolRequest) -> Dict[str, Any]:
        """Call a tool on an MCP server"""
        if request.server_id not in self.mcp_servers:
            raise ValueError(f"MCP server {request.server_id} not found")
            
        server = self.mcp_servers[request.server_id]
        
        if server.status != "running" or request.server_id not in self.client_sessions:
            # Try to start the server
            if not await self.start_mcp_server(request.server_id):
                raise ValueError(f"Could not start MCP server {server.name}")
        
        try:
            session = self.client_sessions[request.server_id]
            result = await session.call_tool(request.tool_name, arguments=request.arguments)
            
            # Extract content from result
            content = []
            for item in result.content:
                if hasattr(item, 'text'):
                    content.append(item.text)
                else:
                    content.append(str(item))
            
            return {
                "success": True,
                "content": content,
                "is_error": getattr(result, 'isError', False)
            }
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {request.tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_openapi_endpoint(self, request: OpenAPICallRequest) -> Dict[str, Any]:
        """Call an endpoint on an OpenAPI server"""
        if request.server_id not in self.openapi_servers:
            raise ValueError(f"OpenAPI server {request.server_id} not found")
            
        server = self.openapi_servers[request.server_id]
        
        # Find the endpoint
        endpoint = None
        for ep in server.endpoints:
            if ep['operation_id'] == request.operation_id:
                endpoint = ep
                break
                
        if not endpoint:
            raise ValueError(f"Operation {request.operation_id} not found on server {server.name}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Build the URL
                url = server.base_url.rstrip('/') + endpoint['path']
                
                # Handle path parameters
                if request.path_params:
                    for key, value in request.path_params.items():
                        url = url.replace(f'{{{key}}}', str(value))
                
                # Make the request
                response = await client.request(
                    method=endpoint['method'],
                    url=url,
                    params=request.query_params or {},
                    json=request.body or {},
                    headers=request.headers or {}
                )
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json() if response.content else None,
                    "headers": dict(response.headers)
                }
                
        except Exception as e:
            logger.error(f"Error calling OpenAPI endpoint {request.operation_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge system statistics"""
        running_mcp = sum(1 for s in self.mcp_servers.values() if s.status == "running")
        online_openapi = sum(1 for s in self.openapi_servers.values() if s.status == "online")
        
        return {
            "mcp_servers": {
                "total": len(self.mcp_servers),
                "running": running_mcp,
                "tools_available": sum(len(s.tools) for s in self.mcp_servers.values())
            },
            "openapi_servers": {
                "total": len(self.openapi_servers),
                "online": online_openapi,
                "endpoints_available": sum(len(s.endpoints) for s in self.openapi_servers.values())
            }
        }

# Initialize the bridge system
bridge = BidirectionalBridge()

# FastAPI app
app = FastAPI(
    title="Bi-directional OpenAPI ↔ MCP Bridge",
    description="Unified ecosystem enabling OpenAPI servers and MCP servers to call each other",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Bridge system root endpoint"""
    return {
        "service": "Bi-directional OpenAPI ↔ MCP Bridge",
        "version": "1.0.0",
        "stats": bridge.get_stats()
    }

@app.get("/stats")
async def get_stats():
    """Get bridge system statistics"""
    return bridge.get_stats()

@app.post("/discover")
async def discover_all():
    """Discover both OpenAPI and MCP servers"""
    openapi_servers = await bridge.discover_openapi_servers()
    mcp_servers = await bridge.discover_mcp_servers()
    
    return {
        "openapi_servers": [asdict(s) for s in openapi_servers],
        "mcp_servers": [asdict(s) for s in mcp_servers],
        "message": f"Discovered {len(openapi_servers)} OpenAPI servers and {len(mcp_servers)} MCP servers"
    }

@app.get("/mcp-servers")
async def list_mcp_servers():
    """List all MCP servers"""
    return {"servers": [asdict(s) for s in bridge.mcp_servers.values()]}

@app.get("/openapi-servers")
async def list_openapi_servers():
    """List all OpenAPI servers"""
    return {"servers": [asdict(s) for s in bridge.openapi_servers.values()]}

@app.post("/mcp-servers/{server_id}/start")
async def start_mcp_server(server_id: str):
    """Start an MCP server"""
    success = await bridge.start_mcp_server(server_id)
    if success:
        return {"message": f"MCP server {server_id} started successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start MCP server")

@app.post("/call-mcp-tool")
async def call_mcp_tool(request: MCPToolRequest):
    """Call a tool on an MCP server"""
    try:
        result = await bridge.call_mcp_tool(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/call-openapi")
async def call_openapi_endpoint(request: OpenAPICallRequest):
    """Call an endpoint on an OpenAPI server"""
    try:
        result = await bridge.call_openapi_endpoint(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/mcp-servers/{server_id}/tools")
async def get_mcp_tools(server_id: str):
    """Get available tools for an MCP server"""
    if server_id not in bridge.mcp_servers:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    server = bridge.mcp_servers[server_id]
    return {"tools": server.tools}

@app.get("/openapi-servers/{server_id}/endpoints")
async def get_openapi_endpoints(server_id: str):
    """Get available endpoints for an OpenAPI server"""
    if server_id not in bridge.openapi_servers:
        raise HTTPException(status_code=404, detail="OpenAPI server not found")
    
    server = bridge.openapi_servers[server_id]
    return {"endpoints": server.endpoints}

# Add special endpoints that allow OpenAPI servers to call MCP tools
@app.post("/proxy/mcp/{server_id}/{tool_name}")
async def proxy_mcp_call(server_id: str, tool_name: str, arguments: Dict[str, Any]):
    """Proxy endpoint allowing OpenAPI servers to call MCP tools"""
    request = MCPToolRequest(
        server_id=server_id,
        tool_name=tool_name,
        arguments=arguments
    )
    return await call_mcp_tool(request)

# Add special endpoints that allow MCP servers to call OpenAPI endpoints
@app.post("/proxy/openapi/{server_id}/{operation_id}")
async def proxy_openapi_call(
    server_id: str, 
    operation_id: str,
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
):
    """Proxy endpoint allowing MCP servers to call OpenAPI endpoints"""
    request = OpenAPICallRequest(
        server_id=server_id,
        operation_id=operation_id,
        path_params=path_params,
        query_params=query_params,
        body=body,
        headers=headers
    )
    return await call_openapi_endpoint(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)


#!/usr/bin/env python3
"""
MCP Bridge Registry Service

This service provides discovery and registration for OpenAPI to MCP bridges.
It maintains a registry of available OpenAPI servers and their corresponding
MCP bridge configurations.
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy httpx logs for health checks
logging.getLogger("httpx").setLevel(logging.WARNING)

# Data Models
@dataclass
class OpenAPIServer:
    """Represents an OpenAPI server configuration"""
    name: str
    base_url: str
    openapi_url: str
    description: str = ""
    tags: List[str] = None
    health_endpoint: str = "/health"
    last_seen: Optional[datetime] = None
    status: str = "unknown"  # unknown, online, offline, error
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass 
class MCPBridge:
    """Represents an MCP bridge configuration"""
    id: str
    name: str
    openapi_server: OpenAPIServer
    bridge_url: str
    process_id: Optional[int] = None
    status: str = "stopped"  # stopped, starting, running, error
    created_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    
class BridgeRequest(BaseModel):
    """Request to create a new bridge"""
    openapi_url: HttpUrl
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class RegistryStats(BaseModel):
    """Registry statistics"""
    total_servers: int
    online_servers: int
    total_bridges: int
    running_bridges: int
    registry_uptime: float

class MCPBridgeRegistry:
    """Main registry service for managing OpenAPI servers and MCP bridges"""
    
    def __init__(self, data_dir: str = "./data", bridge_port_start: int = 8100):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.servers: Dict[str, OpenAPIServer] = {}
        self.bridges: Dict[str, MCPBridge] = {}
        self.bridge_port_start = bridge_port_start
        self.next_port = bridge_port_start
        self.start_time = time.time()
        
        # Load existing data
        self.load_data()
        
    def load_data(self):
        """Load persisted registry data"""
        try:
            servers_file = self.data_dir / "servers.json"
            if servers_file.exists():
                with open(servers_file) as f:
                    data = json.load(f)
                    for server_id, server_data in data.items():
                        # Convert datetime strings back to datetime objects
                        if server_data.get("last_seen"):
                            server_data["last_seen"] = datetime.fromisoformat(server_data["last_seen"])
                        self.servers[server_id] = OpenAPIServer(**server_data)
                        
            bridges_file = self.data_dir / "bridges.json" 
            if bridges_file.exists():
                with open(bridges_file) as f:
                    data = json.load(f)
                    for bridge_id, bridge_data in data.items():
                        # Convert datetime strings and reconstruct objects
                        if bridge_data.get("created_at"):
                            bridge_data["created_at"] = datetime.fromisoformat(bridge_data["created_at"])
                        if bridge_data.get("last_health_check"):
                            bridge_data["last_health_check"] = datetime.fromisoformat(bridge_data["last_health_check"])
                        
                        # Reconstruct OpenAPIServer object
                        server_data = bridge_data["openapi_server"]
                        if server_data.get("last_seen"):
                            server_data["last_seen"] = datetime.fromisoformat(server_data["last_seen"])
                        bridge_data["openapi_server"] = OpenAPIServer(**server_data)
                        
                        self.bridges[bridge_id] = MCPBridge(**bridge_data)
                        
            logger.info(f"Loaded {len(self.servers)} servers and {len(self.bridges)} bridges")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def save_data(self):
        """Persist registry data"""
        try:
            # Custom encoder for datetime objects
            def json_encoder(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, OpenAPIServer):
                    return asdict(obj)
                elif isinstance(obj, MCPBridge):
                    data = asdict(obj)
                    return data
                return obj
            
            servers_file = self.data_dir / "servers.json"
            with open(servers_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.servers.items()}, f, default=json_encoder, indent=2)
                
            bridges_file = self.data_dir / "bridges.json"
            with open(bridges_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.bridges.items()}, f, default=json_encoder, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    async def discover_openapi_server(self, base_url: str) -> Optional[OpenAPIServer]:
        """Discover OpenAPI server by probing common endpoints"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try common OpenAPI spec endpoints
                spec_endpoints = ["/openapi.json", "/openapi.yaml", "/swagger.json", "/docs", "/api/docs"]
                
                for endpoint in spec_endpoints:
                    try:
                        spec_url = f"{base_url.rstrip('/')}{endpoint}"
                        response = await client.get(spec_url)
                        if response.status_code == 200:
                            if endpoint.endswith(('.json', '.yaml')):
                                # Found OpenAPI spec
                                spec_data = response.json() if endpoint.endswith('.json') else response.text
                                if isinstance(spec_data, dict) and ('openapi' in spec_data or 'swagger' in spec_data):
                                    server_name = spec_data.get('info', {}).get('title', f"Server at {base_url}")
                                    description = spec_data.get('info', {}).get('description', "")
                                    
                                    return OpenAPIServer(
                                        name=server_name,
                                        base_url=base_url,
                                        openapi_url=spec_url,
                                        description=description,
                                        last_seen=datetime.now(),
                                        status="online"
                                    )
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.error(f"Error discovering server at {base_url}: {e}")
        
        return None
    
    async def health_check_server(self, server: OpenAPIServer) -> bool:
        """Check if an OpenAPI server is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                # Try endpoints in order of reliability:
                # 1. OpenAPI spec (most reliable)
                # 2. Base URL 
                # 3. Health endpoint (if it exists)
                endpoints_to_try = [
                    (server.openapi_url, "OpenAPI spec"),
                    ("/", "base URL"),
                ]
                
                # Only try health endpoint if we know it exists (not default /health)
                if server.health_endpoint and server.health_endpoint != "/health":
                    endpoints_to_try.append((server.health_endpoint, "health endpoint"))
                
                for endpoint, endpoint_type in endpoints_to_try:
                    try:
                        if endpoint.startswith('http'):
                            url = endpoint  # Full URL for openapi_url
                        else:
                            url = f"{server.base_url.rstrip('/')}{endpoint}"
                            
                        response = await client.get(url)
                        if response.status_code < 400:  # Accept 2xx and 3xx as healthy
                            server.last_seen = datetime.now()
                            server.status = "online"
                            return True
                    except Exception:
                        continue
                        
                server.status = "offline"
                return False
                
        except Exception:
            # Don't log health check failures - they're too noisy
            server.status = "error"
            return False
    
    def get_next_port(self) -> int:
        """Get next available port for bridge"""
        port = self.next_port
        self.next_port += 1
        return port
    
    async def create_bridge(self, request: BridgeRequest) -> MCPBridge:
        """Create a new MCP bridge for an OpenAPI server"""
        openapi_url = str(request.openapi_url)
        base_url = openapi_url.rsplit('/', 1)[0]  # Extract base URL
        
        # Discover or validate the OpenAPI server
        server = await self.discover_openapi_server(base_url)
        if not server:
            raise ValueError(f"Could not discover OpenAPI server at {base_url}")
        
        # Override with request data if provided
        if request.name:
            server.name = request.name
        if request.description:
            server.description = request.description
        if request.tags:
            server.tags = request.tags
            
        # Generate bridge ID and configuration
        bridge_id = f"bridge_{len(self.bridges) + 1}_{int(time.time())}"
        bridge_port = self.get_next_port()
        bridge_url = f"http://localhost:{bridge_port}"
        
        bridge = MCPBridge(
            id=bridge_id,
            name=f"MCP Bridge for {server.name}",
            openapi_server=server,
            bridge_url=bridge_url,
            created_at=datetime.now(),
            status="stopped"
        )
        
        # Store in registries
        server_id = f"{server.name}_{hash(server.base_url) % 10000}"
        self.servers[server_id] = server
        self.bridges[bridge_id] = bridge
        
        # Save data
        self.save_data()
        
        logger.info(f"Created bridge {bridge_id} for {server.name}")
        return bridge
    
    async def start_bridge(self, bridge_id: str) -> bool:
        """Start an MCP bridge process"""
        if bridge_id not in self.bridges:
            raise ValueError(f"Bridge {bridge_id} not found")
            
        bridge = self.bridges[bridge_id]
        
        if bridge.status == "running":
            return True
            
        try:
            bridge.status = "starting"
            
            # Extract port from bridge URL
            parsed_url = urlparse(bridge.bridge_url)
            port = parsed_url.port
            
            # Start the bridge process
            # Assuming the bridge script is in the bridge directory
            bridge_script = Path(__file__).parent.parent / "bridge" / "dist" / "index.js"
            
            # Set environment variables for the bridge
            env = {
                "OPENAPI_BASE_URL": bridge.openapi_server.base_url,
                "OPENAPI_SPEC_URL": bridge.openapi_server.openapi_url,
                "BRIDGE_PORT": str(port),
                "BRIDGE_ID": bridge_id
            }
            
            # Start bridge process (this is a simplified version)
            process = subprocess.Popen(
                ["node", str(bridge_script)],
                env={**subprocess.os.environ, **env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            bridge.process_id = process.pid
            bridge.status = "running"
            bridge.last_health_check = datetime.now()
            
            self.save_data()
            
            logger.info(f"Started bridge {bridge_id} on port {port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bridge {bridge_id}: {e}")
            bridge.status = "error"
            return False
    
    async def stop_bridge(self, bridge_id: str) -> bool:
        """Stop an MCP bridge process"""
        if bridge_id not in self.bridges:
            raise ValueError(f"Bridge {bridge_id} not found")
            
        bridge = self.bridges[bridge_id]
        
        if bridge.status == "stopped":
            return True
            
        try:
            if bridge.process_id:
                # Kill the process
                subprocess.run(["kill", str(bridge.process_id)], check=False)
                bridge.process_id = None
                
            bridge.status = "stopped"
            self.save_data()
            
            logger.info(f"Stopped bridge {bridge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop bridge {bridge_id}: {e}")
            return False
    
    def get_stats(self) -> RegistryStats:
        """Get registry statistics"""
        online_servers = sum(1 for s in self.servers.values() if s.status == "online")
        running_bridges = sum(1 for b in self.bridges.values() if b.status == "running")
        
        return RegistryStats(
            total_servers=len(self.servers),
            online_servers=online_servers,
            total_bridges=len(self.bridges),
            running_bridges=running_bridges,
            registry_uptime=time.time() - self.start_time
        )

# Initialize registry
registry = MCPBridgeRegistry()

# FastAPI app
app = FastAPI(
    title="MCP Bridge Registry",
    description="Central registry for OpenAPI to MCP bridges",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/")
async def root():
    """Registry service root endpoint"""
    return {
        "service": "MCP Bridge Registry",
        "version": "1.0.0",
        "stats": registry.get_stats()
    }

@app.get("/stats")
async def get_stats() -> RegistryStats:
    """Get registry statistics"""
    return registry.get_stats()

@app.get("/servers")
async def list_servers():
    """List all registered OpenAPI servers"""
    return {"servers": [asdict(server) for server in registry.servers.values()]}

@app.get("/bridges")
async def list_bridges():
    """List all MCP bridges"""
    return {"bridges": [asdict(bridge) for bridge in registry.bridges.values()]}

@app.post("/bridges")
async def create_bridge(request: BridgeRequest, background_tasks: BackgroundTasks):
    """Create a new MCP bridge"""
    try:
        bridge = await registry.create_bridge(request)
        
        # Optionally auto-start the bridge
        background_tasks.add_task(registry.start_bridge, bridge.id)
        
        return {"bridge": asdict(bridge), "message": "Bridge created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/bridges/{bridge_id}/start")
async def start_bridge(bridge_id: str):
    """Start an MCP bridge"""
    try:
        success = await registry.start_bridge(bridge_id)
        if success:
            return {"message": f"Bridge {bridge_id} started successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start bridge")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/bridges/{bridge_id}/stop")
async def stop_bridge(bridge_id: str):
    """Stop an MCP bridge"""
    try:
        success = await registry.stop_bridge(bridge_id)
        if success:
            return {"message": f"Bridge {bridge_id} stopped successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop bridge")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/bridges/{bridge_id}")
async def get_bridge(bridge_id: str):
    """Get bridge details"""
    if bridge_id not in registry.bridges:
        raise HTTPException(status_code=404, detail="Bridge not found")
    
    bridge = registry.bridges[bridge_id]
    return {"bridge": asdict(bridge)}

@app.delete("/bridges/{bridge_id}")
async def delete_bridge(bridge_id: str):
    """Delete an MCP bridge"""
    if bridge_id not in registry.bridges:
        raise HTTPException(status_code=404, detail="Bridge not found")
    
    # Stop the bridge first
    await registry.stop_bridge(bridge_id)
    
    # Remove from registry
    del registry.bridges[bridge_id]
    registry.save_data()
    
    return {"message": f"Bridge {bridge_id} deleted successfully"}

@app.post("/discover")
async def discover_server(base_url: str):
    """Discover an OpenAPI server at the given base URL"""
    try:
        server = await registry.discover_openapi_server(base_url)
        if server:
            server_id = f"{server.name}_{hash(server.base_url) % 10000}"
            registry.servers[server_id] = server
            registry.save_data()
            return {"server": asdict(server), "message": "Server discovered and registered"}
        else:
            raise HTTPException(status_code=404, detail="No OpenAPI server found at the given URL")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Background task for health checking
async def health_check_task():
    """Background task to periodically health check all servers"""
    while True:
        try:
            for server in registry.servers.values():
                await registry.health_check_server(server)
            registry.save_data()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Health check task error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    # Start health checking task
    asyncio.create_task(health_check_task())
    logger.info("MCP Bridge Registry started")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info"
    )


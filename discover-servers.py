#!/usr/bin/env python3
"""
OpenAPI Server Discovery Tool

This tool scans common ports and endpoints to discover running OpenAPI servers
on your local system and can register them with the MCP Bridge Registry.
"""

import asyncio
import json
import subprocess
from typing import List, Dict, Optional
import httpx
import argparse


class OpenAPIDiscovery:
    """Tool for discovering OpenAPI servers on the local system"""
    
    def __init__(self):
        self.common_ports = [8000, 8001, 8002, 8003, 8080, 8081, 8090, 3000, 3001, 5000, 5001]
        self.common_endpoints = ["/openapi.json", "/openapi.yaml", "/swagger.json", "/docs", "/api/docs"]
        
    def get_listening_ports(self) -> List[int]:
        """Get list of ports with listening processes"""
        try:
            # Use lsof to find listening ports
            result = subprocess.run(
                ["lsof", "-i", "-P", "-n"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            ports = []
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line and ':' in line:
                    try:
                        # Extract port from lines like "TCP *:8000 (LISTEN)"
                        port_part = line.split()[-2]
                        if ':' in port_part:
                            port = int(port_part.split(':')[-1])
                            if port not in ports:
                                ports.append(port)
                    except (ValueError, IndexError):
                        continue
                        
            return sorted(ports)
            
        except subprocess.CalledProcessError:
            print("Warning: Could not get listening ports, using common ports")
            return self.common_ports
    
    async def check_openapi_endpoint(self, base_url: str, endpoint: str) -> Optional[Dict]:
        """Check if an endpoint returns valid OpenAPI spec"""
        try:
            url = f"{base_url.rstrip('/')}{endpoint}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    if endpoint.endswith('.json'):
                        try:
                            data = response.json()
                            if isinstance(data, dict) and ('openapi' in data or 'swagger' in data):
                                return {
                                    'spec_url': url,
                                    'spec_data': data,
                                    'title': data.get('info', {}).get('title', 'Unknown API'),
                                    'description': data.get('info', {}).get('description', ''),
                                    'version': data.get('info', {}).get('version', ''),
                                    'openapi_version': data.get('openapi', data.get('swagger', ''))
                                }
                        except Exception:
                            pass
                    elif endpoint in ['/docs', '/api/docs']:
                        # Check if it's a Swagger UI page
                        if 'swagger' in response.text.lower() or 'openapi' in response.text.lower():
                            return {
                                'spec_url': url,
                                'type': 'docs_page',
                                'title': 'API Documentation',
                                'description': 'Swagger/OpenAPI documentation page'
                            }
                            
        except Exception as e:
            pass
            
        return None
    
    async def discover_server(self, port: int) -> Optional[Dict]:
        """Discover OpenAPI server on a specific port"""
        base_url = f"http://localhost:{port}"
        
        # Check if port is responding
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(base_url)
                if response.status_code >= 500:
                    return None
        except Exception:
            return None
        
        # Try to find OpenAPI spec
        for endpoint in self.common_endpoints:
            result = await self.check_openapi_endpoint(base_url, endpoint)
            if result:
                result['base_url'] = base_url
                result['port'] = port
                return result
                
        return None
    
    async def discover_all_servers(self, ports: Optional[List[int]] = None) -> List[Dict]:
        """Discover all OpenAPI servers on specified or common ports"""
        if ports is None:
            ports = self.get_listening_ports()
            # Also check common ports that might not be in lsof output
            for port in self.common_ports:
                if port not in ports:
                    ports.append(port)
        
        print(f"Scanning ports: {sorted(ports)}")
        
        tasks = [self.discover_server(port) for port in ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        servers = []
        for i, result in enumerate(results):
            if isinstance(result, dict) and result is not None:
                servers.append(result)
            elif isinstance(result, Exception):
                print(f"Error checking port {ports[i]}: {result}")
                
        return servers
    
    async def register_with_registry(self, servers: List[Dict], registry_url: str = "http://localhost:9000"):
        """Register discovered servers with the MCP Bridge Registry"""
        print(f"\nRegistering {len(servers)} servers with registry at {registry_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for server in servers:
                try:
                    if 'spec_url' in server and server.get('type') != 'docs_page':
                        # Register server
                        response = await client.post(
                            f"{registry_url}/discover",
                            params={"base_url": server['base_url']}
                        )
                        
                        if response.status_code == 200:
                            print(f"✅ Registered: {server['title']} at {server['base_url']}")
                        else:
                            print(f"❌ Failed to register {server['title']}: {response.text}")
                            
                except Exception as e:
                    print(f"❌ Error registering {server.get('title', 'Unknown')}: {e}")
    
    def print_servers(self, servers: List[Dict]):
        """Print discovered servers in a nice format"""
        if not servers:
            print("No OpenAPI servers discovered.")
            return
            
        print(f"\n🔍 Discovered {len(servers)} OpenAPI servers:")
        print("=" * 80)
        
        for i, server in enumerate(servers, 1):
            print(f"\n{i}. {server.get('title', 'Unknown API')}")
            print(f"   URL: {server['base_url']}")
            if server.get('description'):
                print(f"   Description: {server['description']}")
            if server.get('version'):
                print(f"   Version: {server['version']}")
            if server.get('openapi_version'):
                print(f"   OpenAPI Version: {server['openapi_version']}")
            print(f"   Spec: {server['spec_url']}")
            if server.get('type') == 'docs_page':
                print(f"   Type: Documentation Page")


async def main():
    parser = argparse.ArgumentParser(description="Discover OpenAPI servers on local system")
    parser.add_argument("--ports", nargs="+", type=int, help="Specific ports to scan")
    parser.add_argument("--register", action="store_true", help="Register discovered servers with registry")
    parser.add_argument("--registry-url", default="http://localhost:9000", help="Registry URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    discovery = OpenAPIDiscovery()
    
    print("🔍 Discovering OpenAPI servers...")
    servers = await discovery.discover_all_servers(args.ports)
    
    if args.json:
        print(json.dumps(servers, indent=2))
    else:
        discovery.print_servers(servers)
        
    if args.register and servers:
        await discovery.register_with_registry(servers, args.registry_url)
        
    if servers and not args.register:
        print(f"\n💡 To register these servers with the MCP Bridge Registry, run:")
        print(f"   python3 {__file__} --register")


if __name__ == "__main__":
    asyncio.run(main())


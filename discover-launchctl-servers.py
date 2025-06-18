#!/usr/bin/env python3
"""
LaunchCtl OpenAPI Server Discovery Tool

This tool discovers OpenAPI servers managed by launchctl by reading plist files
and checking their actual running status and OpenAPI specifications.
"""

import asyncio
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Set
import httpx
import argparse


class LaunchCtlOpenAPIDiscovery:
    """Tool for discovering OpenAPI servers managed by launchctl"""
    
    def __init__(self):
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.common_endpoints = ["/openapi.json", "/openapi.yaml", "/swagger.json", "/docs", "/api/docs"]
        
    def get_running_services(self) -> Dict[str, Dict]:
        """Get currently running launchctl services"""
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            
            services = {}
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                parts = line.split('\t')
                if len(parts) >= 3:
                    pid = parts[0].strip()
                    exit_code = parts[1].strip()
                    label = parts[2].strip()
                    
                    services[label] = {
                        'pid': pid if pid != '-' else None,
                        'exit_code': exit_code,
                        'running': pid != '-'
                    }
                    
            return services
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting launchctl services: {e}")
            return {}
    
    def parse_plist_file(self, plist_path: Path) -> Optional[Dict]:
        """Parse a plist file and extract service configuration"""
        try:
            tree = ET.parse(plist_path)
            root = tree.getroot()
            
            # Find the main dict element
            main_dict = root.find('.//dict')
            if main_dict is None:
                return None
                
            config = {}
            i = 0
            children = list(main_dict)
            
            while i < len(children) - 1:
                key_elem = children[i]
                value_elem = children[i + 1]
                
                if key_elem.tag == 'key':
                    key = key_elem.text
                    
                    if value_elem.tag == 'string':
                        config[key] = value_elem.text
                    elif value_elem.tag == 'array':
                        config[key] = [child.text for child in value_elem if child.text]
                    elif value_elem.tag == 'dict':
                        # Parse nested dict (like EnvironmentVariables)
                        nested_dict = {}
                        j = 0
                        nested_children = list(value_elem)
                        while j < len(nested_children) - 1:
                            nested_key = nested_children[j]
                            nested_value = nested_children[j + 1]
                            if nested_key.tag == 'key' and nested_value.tag == 'string':
                                nested_dict[nested_key.text] = nested_value.text
                            j += 2
                        config[key] = nested_dict
                    elif value_elem.tag in ['true', 'false']:
                        config[key] = value_elem.tag == 'true'
                        
                i += 2
                
            return config
            
        except Exception as e:
            print(f"Error parsing {plist_path}: {e}")
            return None
    
    def extract_port_from_config(self, config: Dict) -> Optional[int]:
        """Extract port number from service configuration"""
        program_args = config.get('ProgramArguments', [])
        
        # Look for --port argument
        for i, arg in enumerate(program_args):
            if arg == '--port' and i + 1 < len(program_args):
                try:
                    return int(program_args[i + 1])
                except ValueError:
                    continue
                    
        # Check if it's uvicorn without explicit port (defaults to 8000)
        if any('uvicorn' in arg for arg in program_args):
            # Check working directory to infer default ports
            working_dir = config.get('WorkingDirectory', '')
            if 'filesystem' in working_dir:
                return 8000
            elif 'confluence' in working_dir:
                return 8002  # Based on the plist we saw
                
        return None
    
    def get_service_info_from_config(self, config: Dict, label: str) -> Dict:
        """Extract service information from configuration"""
        working_dir = config.get('WorkingDirectory', '')
        program_args = config.get('ProgramArguments', [])
        
        # Determine service name from label or working directory
        service_name = label.replace('com.davec.', '').replace('-', ' ').title()
        if working_dir:
            dir_name = Path(working_dir).name
            service_name = dir_name.replace('-', ' ').title()
            
        port = self.extract_port_from_config(config)
        
        return {
            'label': label,
            'name': service_name,
            'working_directory': working_dir,
            'port': port,
            'program_args': program_args,
            'base_url': f"http://localhost:{port}" if port else None
        }
    
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
                            
        except Exception:
            pass
            
        return None
    
    async def discover_openapi_for_service(self, service_info: Dict) -> Optional[Dict]:
        """Check if a service exposes OpenAPI spec"""
        if not service_info.get('base_url'):
            return None
            
        base_url = service_info['base_url']
        
        # Try to find OpenAPI spec
        for endpoint in self.common_endpoints:
            result = await self.check_openapi_endpoint(base_url, endpoint)
            if result:
                # Merge service info with OpenAPI info
                return {
                    **service_info,
                    **result,
                    'has_openapi': True
                }
                
        # Check if service is responding at all
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(base_url)
                return {
                    **service_info,
                    'responding': True,
                    'status_code': response.status_code,
                    'has_openapi': False
                }
        except Exception:
            return {
                **service_info,
                'responding': False,
                'has_openapi': False
            }
    
    async def discover_all_services(self) -> List[Dict]:
        """Discover all launchctl managed OpenAPI services"""
        # Get running services
        running_services = self.get_running_services()
        
        # Find all com.davec plist files
        plist_files = list(self.launch_agents_dir.glob("com.davec.*.plist"))
        
        services = []
        
        for plist_file in plist_files:
            config = self.parse_plist_file(plist_file)
            if not config:
                continue
                
            label = config.get('Label', plist_file.stem)
            service_info = self.get_service_info_from_config(config, label)
            
            # Add running status
            if label in running_services:
                service_info.update(running_services[label])
            else:
                service_info['running'] = False
                service_info['pid'] = None
                
            services.append(service_info)
        
        # Check for OpenAPI specs
        openapi_tasks = []
        for service in services:
            if service.get('running') and service.get('port'):
                openapi_tasks.append(self.discover_openapi_for_service(service))
            else:
                # Add non-running service info
                service['has_openapi'] = False
                service['responding'] = False
                
        if openapi_tasks:
            openapi_results = await asyncio.gather(*openapi_tasks, return_exceptions=True)
            
            # Update services with OpenAPI results
            running_index = 0
            for i, service in enumerate(services):
                if service.get('running') and service.get('port'):
                    result = openapi_results[running_index]
                    if isinstance(result, dict):
                        services[i] = result
                    running_index += 1
                    
        return services
    
    async def register_with_registry(self, services: List[Dict], registry_url: str = "http://localhost:9000"):
        """Register discovered services with the MCP Bridge Registry"""
        openapi_services = [s for s in services if s.get('has_openapi') and s.get('spec_url')]
        
        if not openapi_services:
            print("No OpenAPI services found to register")
            return
            
        print(f"\\nRegistering {len(openapi_services)} OpenAPI services with registry at {registry_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service in openapi_services:
                try:
                    if service.get('type') != 'docs_page':
                        # Register server
                        response = await client.post(
                            f"{registry_url}/discover",
                            params={"base_url": service['base_url']}
                        )
                        
                        if response.status_code == 200:
                            print(f"✅ Registered: {service.get('title', service['name'])} at {service['base_url']}")
                        else:
                            print(f"❌ Failed to register {service.get('title', service['name'])}: {response.text}")
                            
                except Exception as e:
                    print(f"❌ Error registering {service.get('title', service['name'])}: {e}")
    
    def print_services(self, services: List[Dict]):
        """Print discovered services in a nice format"""
        if not services:
            print("No launchctl services found.")
            return
            
        print(f"\\n🔍 Discovered {len(services)} launchctl services:")
        print("=" * 100)
        
        openapi_count = sum(1 for s in services if s.get('has_openapi'))
        running_count = sum(1 for s in services if s.get('running'))
        
        print(f"📊 Summary: {running_count} running, {openapi_count} with OpenAPI")
        
        for i, service in enumerate(services, 1):
            status_icon = "🟢" if service.get('running') else "🔴"
            openapi_icon = "📘" if service.get('has_openapi') else "❌" if service.get('responding') else "💤"
            
            print(f"\\n{i}. {status_icon} {service['name']} {openapi_icon}")
            print(f"   Label: {service['label']}")
            if service.get('base_url'):
                print(f"   URL: {service['base_url']}")
            if service.get('running'):
                print(f"   PID: {service.get('pid', 'unknown')}")
            if service.get('working_directory'):
                print(f"   Directory: {service['working_directory']}")
            
            if service.get('has_openapi'):
                print(f"   📘 Title: {service.get('title', 'Unknown')}")
                if service.get('description'):
                    print(f"   📝 Description: {service['description']}")
                if service.get('version'):
                    print(f"   🏷️  Version: {service['version']}")
                if service.get('spec_url'):
                    print(f"   🔗 Spec: {service['spec_url']}")
            elif service.get('responding'):
                print(f"   ⚠️  Responding but no OpenAPI spec found")
            elif service.get('running'):
                print(f"   ❌ Not responding")
            else:
                print(f"   💤 Not running")


async def main():
    parser = argparse.ArgumentParser(description="Discover OpenAPI servers managed by launchctl")
    parser.add_argument("--register", action="store_true", help="Register discovered servers with registry")
    parser.add_argument("--registry-url", default="http://localhost:9000", help="Registry URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--start-missing", action="store_true", help="Start services that aren't running")
    
    args = parser.parse_args()
    
    discovery = LaunchCtlOpenAPIDiscovery()
    
    print("🔍 Discovering launchctl OpenAPI services...")
    services = await discovery.discover_all_services()
    
    if args.json:
        # Remove non-serializable data for JSON output
        json_services = []
        for service in services:
            json_service = {k: v for k, v in service.items() if k != 'spec_data'}
            json_services.append(json_service)
        print(json.dumps(json_services, indent=2))
    else:
        discovery.print_services(services)
        
    if args.register:
        await discovery.register_with_registry(services, args.registry_url)
        
    if args.start_missing:
        stopped_services = [s for s in services if not s.get('running')]
        if stopped_services:
            print(f"\\n🚀 Starting {len(stopped_services)} stopped services...")
            for service in stopped_services:
                try:
                    result = subprocess.run(
                        ["launchctl", "load", f"/Users/davec/Library/LaunchAgents/{service['label']}.plist"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"✅ Started {service['name']}")
                    else:
                        print(f"❌ Failed to start {service['name']}: {result.stderr}")
                except Exception as e:
                    print(f"❌ Error starting {service['name']}: {e}")
        
    openapi_services = [s for s in services if s.get('has_openapi')]
    if openapi_services and not args.register:
        print(f"\\n💡 To register these {len(openapi_services)} OpenAPI services with the MCP Bridge Registry:")
        print(f"   python3 {__file__} --register")


if __name__ == "__main__":
    asyncio.run(main())


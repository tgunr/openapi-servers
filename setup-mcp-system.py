#!/usr/bin/env python3
"""
Complete MCP Bridge System Setup

This script sets up the complete OpenAPI to MCP bridge system including:
1. Registry service 
2. Discovery and registration of existing OpenAPI servers
3. Creation of MCP bridges for each service
4. Example usage demonstration
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
import httpx


async def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
    try:
        import httpx
        print("✅ httpx available")
    except ImportError:
        missing_deps.append("httpx")
    
    try:
        import fastapi
        print("✅ fastapi available")  
    except ImportError:
        missing_deps.append("fastapi")
        
    try:
        import uvicorn
        print("✅ uvicorn available")
    except ImportError:
        missing_deps.append("uvicorn")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Installing missing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing_deps)
        print("✅ Dependencies installed")
    else:
        print("✅ All dependencies available")


async def start_registry_service():
    """Start the MCP Bridge Registry service"""
    print("🚀 Starting MCP Bridge Registry...")
    
    registry_dir = Path("/Volumes/AI/openapi-servers/registry")
    
    # Check if registry is already running
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:9000/")
            if response.status_code == 200:
                print("✅ Registry already running on port 9000")
                return True
    except:
        pass
    
    # Start registry in background
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=registry_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a few seconds for startup
        await asyncio.sleep(3)
        
        # Check if it's running
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:9000/")
            if response.status_code == 200:
                print("✅ Registry started successfully on port 9000")
                return True
            else:
                print("❌ Registry failed to start properly")
                return False
                
    except Exception as e:
        print(f"❌ Failed to start registry: {e}")
        return False


async def discover_and_register_services():
    """Discover OpenAPI services and register them with the registry"""
    print("🔍 Discovering and registering OpenAPI services...")
    
    try:
        # Run the discovery script with registration
        result = subprocess.run([
            sys.executable, 
            "/Volumes/AI/openapi-servers/discover-launchctl-servers.py",
            "--register"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Services discovered and registered successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ Discovery failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        return False


async def create_mcp_bridges():
    """Create MCP bridges for registered services"""
    print("🌉 Creating MCP bridges...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get list of registered servers
            response = await client.get("http://localhost:9000/servers")
            if response.status_code != 200:
                print("❌ Could not get servers from registry")
                return False
                
            servers_data = response.json()
            servers = servers_data.get('servers', [])
            
            if not servers:
                print("⚠️ No servers found in registry")
                return True
                
            print(f"Found {len(servers)} servers to create bridges for...")
            
            # Create bridges for each server
            bridges_created = 0
            for server in servers:
                try:
                    bridge_request = {
                        "openapi_url": server['openapi_url'],
                        "name": server['name'],
                        "description": server.get('description', ''),
                        "tags": server.get('tags', [])
                    }
                    
                    response = await client.post(
                        "http://localhost:9000/bridges",
                        json=bridge_request
                    )
                    
                    if response.status_code == 200:
                        bridge_data = response.json()
                        bridge_id = bridge_data['bridge']['id']
                        print(f"✅ Created bridge for {server['name']} (ID: {bridge_id})")
                        bridges_created += 1
                    else:
                        print(f"❌ Failed to create bridge for {server['name']}: {response.text}")
                        
                except Exception as e:
                    print(f"❌ Error creating bridge for {server['name']}: {e}")
            
            print(f"✅ Created {bridges_created} MCP bridges")
            return bridges_created > 0
            
    except Exception as e:
        print(f"❌ Error creating bridges: {e}")
        return False


async def show_system_status():
    """Show the current status of the MCP bridge system"""
    print("\\n📊 MCP Bridge System Status")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get registry stats
            response = await client.get("http://localhost:9000/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"📈 Registry Stats:")
                print(f"   • Total Servers: {stats['total_servers']}")
                print(f"   • Online Servers: {stats['online_servers']}")
                print(f"   • Total Bridges: {stats['total_bridges']}")
                print(f"   • Running Bridges: {stats['running_bridges']}")
                print(f"   • Uptime: {stats['registry_uptime']:.1f}s")
            
            # Get bridges list
            response = await client.get("http://localhost:9000/bridges")
            if response.status_code == 200:
                bridges_data = response.json()
                bridges = bridges_data.get('bridges', [])
                
                print(f"\\n🌉 MCP Bridges ({len(bridges)}):")
                for bridge in bridges:
                    status_icon = "🟢" if bridge['status'] == 'running' else "🔴" if bridge['status'] == 'error' else "⏸️"
                    print(f"   {status_icon} {bridge['name']} ({bridge['status']})")
                    print(f"      Bridge URL: {bridge['bridge_url']}")
                    print(f"      OpenAPI: {bridge['openapi_server']['base_url']}")
                    
    except Exception as e:
        print(f"❌ Error getting system status: {e}")


async def demonstrate_usage():
    """Demonstrate how to use the MCP bridge system"""
    print("\\n💡 Usage Examples")
    print("=" * 50)
    
    print("\\n1. 🌐 Registry Web Interface:")
    print("   Open: http://localhost:9000/")
    print("   API Docs: http://localhost:9000/docs")
    
    print("\\n2. 🔍 Discovery Commands:")
    print("   # Discover services:")
    print("   python3 discover-launchctl-servers.py")
    print("   # Register with registry:")
    print("   python3 discover-launchctl-servers.py --register")
    
    print("\\n3. 🌉 Bridge Management:")
    print("   # List bridges:")
    print("   curl http://localhost:9000/bridges")
    print("   # Create new bridge:")
    print("   curl -X POST http://localhost:9000/bridges -H 'Content-Type: application/json' \\\\")
    print("        -d '{\"openapi_url\": \"http://localhost:8000/openapi.json\"}'")
    
    print("\\n4. 🔧 MCP Client Usage:")
    print("   # Test MCP bridge:")
    print("   echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}' | \\\\")
    print("        node bridge/dist/index.js")
    
    print("\\n5. 📱 OpenAPI Services:")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://localhost:9000/servers")
            if response.status_code == 200:
                servers_data = response.json()
                servers = servers_data.get('servers', [])
                for server in servers[:3]:  # Show first 3
                    print(f"   • {server['name']}: {server['base_url']}")
                if len(servers) > 3:
                    print(f"   • ... and {len(servers) - 3} more")
        except:
            pass


async def main():
    """Main setup function"""
    print("🚀 MCP Bridge System Setup")
    print("=" * 50)
    print("Setting up the complete OpenAPI to MCP bridge system...")
    print("This will create a registry and bridges for your existing OpenAPI servers.\\n")
    
    # Step 1: Check dependencies
    await check_dependencies()
    print()
    
    # Step 2: Start registry service
    registry_started = await start_registry_service()
    if not registry_started:
        print("❌ Could not start registry service. Exiting.")
        return
    print()
    
    # Step 3: Discover and register services
    discovery_success = await discover_and_register_services()
    if not discovery_success:
        print("⚠️ Service discovery had issues, but continuing...")
    print()
    
    # Step 4: Create MCP bridges
    bridges_created = await create_mcp_bridges()
    if not bridges_created:
        print("⚠️ No bridges were created")
    print()
    
    # Step 5: Show system status
    await show_system_status()
    
    # Step 6: Show usage examples
    await demonstrate_usage()
    
    print("\\n🎉 MCP Bridge System Setup Complete!")
    print("\\nYour OpenAPI to MCP bridge system is now ready to use.")
    print("The registry is running at: http://localhost:9000")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\n⏹️ Setup interrupted by user")
    except Exception as e:
        print(f"\\n\\n❌ Setup failed: {e}")


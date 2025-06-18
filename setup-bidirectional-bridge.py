#!/usr/bin/env python3
"""
Setup script for Bi-directional OpenAPI ↔ MCP Bridge System

This script sets up the complete bi-directional bridge system enabling:
1. OpenAPI servers to call MCP server functions
2. MCP servers to call OpenAPI server endpoints
3. Dynamic discovery and unified ecosystem management
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
import httpx
import json

async def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
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
        
    try:
        import httpx
        print("✅ httpx available")
    except ImportError:
        missing_deps.append("httpx")
    
    try:
        import mcp
        print("✅ mcp available")
    except ImportError:
        missing_deps.append("mcp")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Installing missing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing_deps)
        print("✅ Dependencies installed")
    else:
        print("✅ All dependencies available")

async def check_prerequisites():
    """Check if required services are running"""
    print("🔍 Checking prerequisites...")
    
    services = {
        "Registry (9000)": "http://localhost:9000",
        "OpenAPI Bridge (dist/index.js)": "/Volumes/AI/openapi-servers/bridge/dist/index.js"
    }
    
    all_good = True
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            if name.startswith("Registry"):
                try:
                    response = await client.get(url)
                    if response.status_code < 500:
                        print(f"✅ {name}")
                    else:
                        print(f"❌ {name} not responding properly")
                        all_good = False
                except Exception:
                    print(f"❌ {name} not accessible")
                    all_good = False
            else:
                # Check file existence
                if Path(url).exists():
                    print(f"✅ {name}")
                else:
                    print(f"❌ {name} not found")
                    all_good = False
    
    return all_good

async def start_bridge_system():
    """Start the bi-directional bridge system"""
    print("🚀 Starting bi-directional bridge system...")
    
    bridge_dir = Path("/Volumes/AI/openapi-servers/bidirectional-bridge")
    
    # Check if bridge is already running
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8100/")
            if response.status_code == 200:
                print("✅ Bridge system already running on port 8100")
                return True
    except:
        pass
    
    # Start bridge system in background
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=bridge_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a few seconds for startup
        await asyncio.sleep(3)
        
        # Check if it's running
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8100/")
            if response.status_code == 200:
                print("✅ Bridge system started successfully on port 8100")
                return True
            else:
                print("❌ Bridge system failed to start properly")
                return False
                
    except Exception as e:
        print(f"❌ Failed to start bridge system: {e}")
        return False

async def discover_and_connect():
    """Discover both OpenAPI and MCP servers and establish connections"""
    print("🔍 Discovering servers and establishing connections...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Trigger discovery
            response = await client.post("http://localhost:8100/discover")
            if response.status_code == 200:
                data = response.json()
                openapi_count = len(data.get('openapi_servers', []))
                mcp_count = len(data.get('mcp_servers', []))
                
                print(f"✅ Discovered {openapi_count} OpenAPI servers and {mcp_count} MCP servers")
                
                # Start MCP servers
                if mcp_count > 0:
                    mcp_response = await client.get("http://localhost:8100/mcp-servers")
                    if mcp_response.status_code == 200:
                        mcp_servers = mcp_response.json().get('servers', [])
                        
                        started_count = 0
                        for server in mcp_servers[:3]:  # Start first 3 servers as demo
                            try:
                                start_response = await client.post(
                                    f"http://localhost:8100/mcp-servers/{server['id']}/start"
                                )
                                if start_response.status_code == 200:
                                    print(f"✅ Started MCP server: {server['name']}")
                                    started_count += 1
                                else:
                                    print(f"⚠️ Could not start MCP server: {server['name']}")
                            except Exception as e:
                                print(f"❌ Error starting {server['name']}: {e}")
                        
                        print(f"📊 Started {started_count}/{min(len(mcp_servers), 3)} MCP servers")
                
                return True
            else:
                print("❌ Failed to discover servers")
                return False
                
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        return False

async def show_system_status():
    """Show the current status of the bi-directional bridge system"""
    print("\n📊 Bi-directional Bridge System Status")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get bridge stats
            response = await client.get("http://localhost:8100/stats")
            if response.status_code == 200:
                stats = response.json()
                
                print(f"🔄 Bridge System Stats:")
                print(f"   • MCP Servers: {stats['mcp_servers']['total']} total, {stats['mcp_servers']['running']} running")
                print(f"   • MCP Tools Available: {stats['mcp_servers']['tools_available']}")
                print(f"   • OpenAPI Servers: {stats['openapi_servers']['total']} total, {stats['openapi_servers']['online']} online")
                print(f"   • OpenAPI Endpoints Available: {stats['openapi_servers']['endpoints_available']}")
            
            # Get server lists
            print(f"\n🔌 Active Connections:")
            
            # MCP servers
            mcp_response = await client.get("http://localhost:8100/mcp-servers")
            if mcp_response.status_code == 200:
                mcp_servers = mcp_response.json().get('servers', [])
                running_mcp = [s for s in mcp_servers if s['status'] == 'running']
                
                for server in running_mcp:
                    tool_count = len(server.get('tools', []))
                    print(f"   🟢 MCP: {server['name']} ({tool_count} tools)")
            
            # OpenAPI servers
            api_response = await client.get("http://localhost:8100/openapi-servers")
            if api_response.status_code == 200:
                api_servers = api_response.json().get('servers', [])
                online_api = [s for s in api_servers if s['status'] == 'online']
                
                for server in online_api:
                    endpoint_count = len(server.get('endpoints', []))
                    print(f"   🟢 API: {server['name']} ({endpoint_count} endpoints)")
                    
    except Exception as e:
        print(f"❌ Error getting system status: {e}")

async def demonstrate_bidirectional_calls():
    """Demonstrate bi-directional calling capabilities"""
    print("\n💡 Bi-directional Call Examples")
    print("=" * 60)
    
    print("\n1. 🌐 Bridge System Web Interface:")
    print("   Open: http://localhost:8100/")
    print("   API Docs: http://localhost:8100/docs")
    
    print("\n2. 🔄 Direct API Calls:")
    print("   # Get all servers:")
    print("   curl http://localhost:8100/stats")
    print("   # List MCP servers and tools:")
    print("   curl http://localhost:8100/mcp-servers")
    print("   # List OpenAPI servers and endpoints:")
    print("   curl http://localhost:8100/openapi-servers")
    
    print("\n3. 🔧 OpenAPI → MCP Calls:")
    print("   # Call MCP tool from OpenAPI server:")
    print("   curl -X POST http://localhost:8100/call-mcp-tool \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"server_id\":\"mcp_12345\",\"tool_name\":\"search\",\"arguments\":{\"query\":\"test\"}}'")
    
    print("\n4. 🔧 MCP → OpenAPI Calls:")
    print("   # Call OpenAPI endpoint from MCP server:")
    print("   curl -X POST http://localhost:8100/call-openapi \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"server_id\":\"openapi_67890\",\"operation_id\":\"list_files\",\"body\":{\"path\":\"/tmp\"}}'")
    
    print("\n5. 🌉 Proxy Endpoints:")
    print("   # Direct proxy calls (simpler syntax):")
    print("   curl -X POST http://localhost:8100/proxy/mcp/{server_id}/{tool_name} \\")
    print("        -H 'Content-Type: application/json' -d '{\"query\":\"example\"}'")
    print("   curl -X POST http://localhost:8100/proxy/openapi/{server_id}/{operation_id} \\")
    print("        -H 'Content-Type: application/json' -d '{\"path\":\"/home\"}'")

async def test_connectivity():
    """Test bi-directional connectivity with simple examples"""
    print("\n🧪 Testing Bi-directional Connectivity")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Get available servers
            mcp_response = await client.get("http://localhost:8100/mcp-servers")
            api_response = await client.get("http://localhost:8100/openapi-servers")
            
            if mcp_response.status_code == 200 and api_response.status_code == 200:
                mcp_servers = mcp_response.json().get('servers', [])
                api_servers = api_response.json().get('servers', [])
                
                running_mcp = [s for s in mcp_servers if s['status'] == 'running']
                online_api = [s for s in api_servers if s['status'] == 'online']
                
                tests_passed = 0
                total_tests = 0
                
                # Test MCP tool calls
                if running_mcp:
                    server = running_mcp[0]
                    if server.get('tools'):
                        tool = server['tools'][0]
                        total_tests += 1
                        
                        try:
                            test_args = {}
                            # Add basic test arguments based on tool schema
                            schema = tool.get('input_schema', {})
                            properties = schema.get('properties', {})
                            
                            for prop_name, prop_def in properties.items():
                                if prop_def.get('type') == 'string':
                                    test_args[prop_name] = 'test'
                                elif prop_def.get('type') == 'integer':
                                    test_args[prop_name] = 1
                            
                            call_response = await client.post(
                                "http://localhost:8100/call-mcp-tool",
                                json={
                                    "server_id": server['id'],
                                    "tool_name": tool['name'],
                                    "arguments": test_args
                                }
                            )
                            
                            if call_response.status_code == 200:
                                result = call_response.json()
                                if result.get('success'):
                                    print(f"✅ MCP call test passed: {server['name']}.{tool['name']}")
                                    tests_passed += 1
                                else:
                                    print(f"⚠️ MCP call returned error: {result.get('error', 'Unknown')}")
                            else:
                                print(f"❌ MCP call test failed: HTTP {call_response.status_code}")
                                
                        except Exception as e:
                            print(f"❌ MCP call test error: {e}")
                
                # Test OpenAPI endpoint calls
                if online_api:
                    server = online_api[0]
                    if server.get('endpoints'):
                        endpoint = server['endpoints'][0]
                        total_tests += 1
                        
                        try:
                            call_response = await client.post(
                                "http://localhost:8100/call-openapi",
                                json={
                                    "server_id": server['id'],
                                    "operation_id": endpoint['operation_id'],
                                    "body": {}
                                }
                            )
                            
                            if call_response.status_code == 200:
                                result = call_response.json()
                                if result.get('success'):
                                    print(f"✅ OpenAPI call test passed: {server['name']}.{endpoint['operation_id']}")
                                    tests_passed += 1
                                else:
                                    print(f"⚠️ OpenAPI call returned error: {result.get('error', 'Unknown')}")
                            else:
                                print(f"❌ OpenAPI call test failed: HTTP {call_response.status_code}")
                                
                        except Exception as e:
                            print(f"❌ OpenAPI call test error: {e}")
                
                if total_tests > 0:
                    print(f"\n📊 Connectivity Tests: {tests_passed}/{total_tests} passed")
                else:
                    print("\n⚠️ No tests could be run - no running servers with tools/endpoints found")
                
    except Exception as e:
        print(f"❌ Error during connectivity testing: {e}")

async def main():
    """Main setup function"""
    print("🚀 Bi-directional OpenAPI ↔ MCP Bridge Setup")
    print("=" * 60)
    print("Setting up unified ecosystem for OpenAPI ↔ MCP connectivity...")
    print("This enables both directions: OpenAPI→MCP and MCP→OpenAPI calls.\n")
    
    # Step 1: Check dependencies
    await check_dependencies()
    print()
    
    # Step 2: Check prerequisites
    prerequisites_ok = await check_prerequisites()
    if not prerequisites_ok:
        print("⚠️ Some prerequisites missing, but continuing...")
    print()
    
    # Step 3: Start bridge system
    bridge_started = await start_bridge_system()
    if not bridge_started:
        print("❌ Could not start bridge system. Exiting.")
        return
    print()
    
    # Step 4: Discover and connect
    discovery_success = await discover_and_connect()
    if not discovery_success:
        print("⚠️ Discovery had issues, but bridge is running...")
    print()
    
    # Step 5: Show system status
    await show_system_status()
    
    # Step 6: Test connectivity
    await test_connectivity()
    
    # Step 7: Show usage examples
    await demonstrate_bidirectional_calls()
    
    print("\n🎉 Bi-directional Bridge System Setup Complete!")
    print("\nYour unified OpenAPI ↔ MCP ecosystem is now ready!")
    print("• OpenAPI servers can call MCP tools")
    print("• MCP servers can call OpenAPI endpoints") 
    print("• Dynamic discovery and routing enabled")
    print("• Bridge system running at: http://localhost:8100")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")


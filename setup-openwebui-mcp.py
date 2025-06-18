#!/usr/bin/env python3
"""
Open WebUI MCP Integration Setup

This script automatically configures Open WebUI to use your OpenAPI services
through MCP bridges, enabling natural language interaction with all your APIs.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import httpx


class OpenWebUIMCPSetup:
    """Setup MCP integration for Open WebUI"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "open-webui" / "mcp"
        self.bridge_script = Path("/Volumes/AI/openapi-servers/bridge/dist/index.js")
        
    async def check_prerequisites(self) -> bool:
        """Check if all prerequisites are running"""
        print("🔍 Checking prerequisites...")
        
        checks = {
            "Ollama (11434)": "http://localhost:11434",
            "Open WebUI (8080)": "http://localhost:8080", 
            "Registry (9000)": "http://localhost:9000",
            "Bridge Script": str(self.bridge_script)
        }
        
        all_good = True
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in checks.items():
                if name == "Bridge Script":
                    if Path(url).exists():
                        print(f"✅ {name}")
                    else:
                        print(f"❌ {name} not found at {url}")
                        all_good = False
                else:
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
        
        return all_good
    
    async def get_available_bridges(self) -> List[Dict]:
        """Get available MCP bridges from registry"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:9000/bridges")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('bridges', [])
        except Exception as e:
            print(f"❌ Error getting bridges: {e}")
        return []
    
    def generate_mcp_config(self, bridges: List[Dict]) -> Dict:
        """Generate MCP configuration for Open WebUI"""
        config = {"mcpServers": {}}
        
        for bridge in bridges:
            # Only include bridges that have valid OpenAPI servers
            if not bridge.get('openapi_server'):
                continue
                
            server = bridge['openapi_server']
            server_name = server['name'].lower().replace(' ', '_').replace('-', '_')
            
            # Clean up server name to be a valid identifier
            server_name = ''.join(c for c in server_name if c.isalnum() or c == '_')
            
            config["mcpServers"][server_name] = {
                "command": "node",
                "args": [str(self.bridge_script)],
                "env": {
                    "OPENAPI_BASE_URL": server['base_url'],
                    "OPENAPI_SPEC_URL": server['openapi_url'],
                    "BRIDGE_ID": bridge['id']
                }
            }
        
        return config
    
    async def setup_mcp_config(self):
        """Set up MCP configuration for Open WebUI"""
        print("🔧 Setting up MCP configuration...")
        
        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created config directory: {self.config_dir}")
        
        # Get available bridges
        bridges = await self.get_available_bridges()
        if not bridges:
            print("⚠️ No bridges found. Run the registry setup first.")
            return False
            
        print(f"📋 Found {len(bridges)} bridges")
        
        # Generate configuration
        config = self.generate_mcp_config(bridges)
        
        if not config["mcpServers"]:
            print("⚠️ No valid MCP servers to configure")
            return False
        
        # Save MCP servers configuration
        config_file = self.config_dir / "servers.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"✅ MCP configuration saved to {config_file}")
        print(f"📊 Configured {len(config['mcpServers'])} MCP servers:")
        for name in config["mcpServers"].keys():
            print(f"   • {name}")
        
        # Create environment file
        env_file = self.config_dir / ".env"
        with open(env_file, 'w') as f:
            f.write(f"MCP_SERVERS_CONFIG={config_file}\n")
            f.write("ENABLE_MCP_TOOLS=true\n")
            f.write("MCP_DEBUG=true\n")
            
        print(f"✅ Environment configuration saved to {env_file}")
        
        return True
    
    async def test_bridge_connection(self):
        """Test MCP bridge connections"""
        print("🧪 Testing MCP bridge connections...")
        
        bridges = await self.get_available_bridges()
        if not bridges:
            return False
            
        test_passed = 0
        
        for bridge in bridges:
            server = bridge.get('openapi_server')
            if not server:
                continue
                
            server_name = server['name']
            
            try:
                # Test the bridge with a simple tools/list request
                cmd = [
                    "node", str(self.bridge_script)
                ]
                
                env = {
                    **subprocess.os.environ,
                    "OPENAPI_BASE_URL": server['base_url'],
                    "OPENAPI_SPEC_URL": server['openapi_url'], 
                    "BRIDGE_ID": bridge['id']
                }
                
                # Send a test MCP request
                test_request = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
                
                process = subprocess.run(
                    cmd,
                    input=test_request,
                    text=True,
                    capture_output=True,
                    env=env,
                    timeout=10
                )
                
                if process.returncode == 0 and "tools" in process.stdout:
                    print(f"✅ {server_name} bridge working")
                    test_passed += 1
                else:
                    print(f"❌ {server_name} bridge failed: {process.stderr}")
                    
            except Exception as e:
                print(f"❌ {server_name} bridge error: {e}")
        
        print(f"📊 {test_passed}/{len(bridges)} bridges passed tests")
        return test_passed > 0
    
    def create_usage_guide(self):
        """Create a usage guide file"""
        guide_file = self.config_dir / "usage-guide.md"
        
        usage_content = """# Open WebUI MCP Tools Usage Guide

## Available Tools

Your Open WebUI now has access to the following tools through MCP:

### Filesystem Operations
- **List Directory**: "List files in /path/to/directory"
- **Read File**: "Read the contents of /path/to/file.txt"
- **Write File**: "Write 'content' to /path/to/file.txt"
- **Search Files**: "Search for files named 'pattern' in /path"

### Confluence Operations  
- **Search**: "Search Confluence for 'API documentation'"
- **Get Page**: "Get the Confluence page about 'topic'"

### Git Operations
- **Status**: "What's the git status?"
- **Log**: "Show recent git commits"
- **Diff**: "Show git diff for recent changes"

### Memory Operations
- **Store**: "Remember that the API key is 'xyz'"
- **Recall**: "What do you remember about API keys?"

## Example Conversations

**File Management:**
```
You: "List the files in my home directory"
Assistant: I'll list the files in your home directory using the filesystem tool...
```

**Code Search:**
```
You: "Find all Python files in my project directory"
Assistant: I'll search for Python files in your project...
```

**Confluence Search:**
```
You: "Search our documentation for 'deployment guide'"
Assistant: I'll search Confluence for deployment guides...
```

## Tips

1. Be specific with file paths
2. Use natural language - the AI will translate to tool calls
3. Tools can be chained together for complex operations
4. Check the response for any errors or permissions issues

## Troubleshooting

If tools aren't working:
1. Check that all services are running
2. Restart Open WebUI
3. Check the MCP configuration at ~/.config/open-webui/mcp/
"""
        
        with open(guide_file, 'w') as f:
            f.write(usage_content)
            
        print(f"📖 Usage guide created: {guide_file}")
    
    async def restart_instruction(self):
        """Provide instructions for restarting Open WebUI"""
        print("\n🔄 Next Steps:")
        print("=" * 50)
        
        # Check if Open WebUI is running via launchctl
        result = subprocess.run(
            ["launchctl", "list", "com.davec.openwebui"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("🔧 Open WebUI is managed by launchctl. To restart:")
            print("   launchctl unload ~/Library/LaunchAgents/com.davec.openwebui.plist")
            print("   launchctl load ~/Library/LaunchAgents/com.davec.openwebui.plist")
        else:
            print("🔧 To restart Open WebUI:")
            print("   • If using Docker: docker restart open-webui")
            print("   • If using pip: Stop and restart the open-webui process")
            print("   • If using systemd: sudo systemctl restart open-webui")
        
        print("\n🌐 After restart, open: http://localhost:8080")
        print("💬 Start a new chat and try: 'List files in my home directory'")
    
    async def main(self):
        """Main setup process"""
        print("🚀 Open WebUI MCP Integration Setup")
        print("=" * 50)
        print("This will configure Open WebUI to use your OpenAPI services through MCP tools.\n")
        
        # Check prerequisites
        if not await self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please ensure all services are running.")
            return False
        
        print()
        
        # Setup MCP configuration
        if not await self.setup_mcp_config():
            print("\n❌ Failed to setup MCP configuration.")
            return False
        
        print()
        
        # Test bridge connections
        if not await self.test_bridge_connection():
            print("\n⚠️ Some bridges failed tests, but configuration is saved.")
        
        print()
        
        # Create usage guide
        self.create_usage_guide()
        
        # Provide restart instructions
        await self.restart_instruction()
        
        print("\n🎉 Open WebUI MCP Integration Setup Complete!")
        print("\nYour Open WebUI can now directly interact with:")
        print("• Filesystem operations")
        print("• Confluence search and content")
        print("• Git repository management") 
        print("• Memory storage and retrieval")
        print("• And all your other OpenAPI services!")
        
        return True


async def main():
    setup = OpenWebUIMCPSetup()
    
    try:
        success = await setup.main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


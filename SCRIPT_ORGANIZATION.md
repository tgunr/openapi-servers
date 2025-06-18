# Script Organization

This document explains where the various Python scripts should be located and how to use them.

## Current Organization

### 🛠️ **Project-Specific Scripts** (Stay in `/Volumes/AI/openapi-servers/`)

These scripts are specific to this project and should remain in the project directory:

- **`setup-mcp-system.py`** - Complete MCP bridge system setup
- **`setup-bidirectional-bridge.py`** - Bidirectional bridge configuration  
- **`setup-openwebui-mcp.py`** - OpenWebUI MCP integration setup
- **`mcp-manager`** - Convenient wrapper for all project operations

**Usage:**
```bash
cd /Volumes/AI/openapi-servers
./mcp-manager setup-system
./mcp-manager setup-openwebui
```

### 🌍 **General-Purpose Tools** (Moved to `~/bin/` - In your PATH)

These are general-purpose discovery tools useful system-wide:

- **`discover-openapi-servers`** (was `discover-servers.py`)
- **`discover-launchctl-openapi-servers`** (was `discover-launchctl-servers.py`)

**Usage from anywhere:**
```bash
discover-openapi-servers
discover-openapi-servers --register
discover-launchctl-openapi-servers
```

## Quick Reference

### Project Management
```bash
# From project directory
./mcp-manager setup-system          # Complete setup
./mcp-manager discover --register   # Local discovery + registration
./mcp-manager setup-openwebui       # OpenWebUI integration
```

### System-Wide Discovery
```bash
# From anywhere
discover-openapi-servers             # Find running APIs
discover-launchctl-openapi-servers   # Find launchctl-managed APIs
```

## Benefits of This Organization

1. **Project tools stay with project** - Setup scripts remain contextual
2. **Discovery tools available everywhere** - Can discover APIs from any directory
3. **Clean separation** - Clear distinction between project-specific and general tools
4. **Convenient wrapper** - `mcp-manager` provides unified interface
5. **PATH integration** - Discovery tools work system-wide

## Environment Setup

The discovery tools are installed in `~/bin/` and added to your PATH:
```bash
export PATH="$HOME/bin:$PATH"  # Added to ~/.zshrc
```


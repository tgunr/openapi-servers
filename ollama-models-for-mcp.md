# Ollama Models for OpenAPI/MCP Server Integration

**Date:** June 18, 2025  
**Location:** Systems/mini/AI/servers  

## Current OpenAPI Servers Running

We have **9 OpenAPI servers** currently active:

1. **Secure Filesystem API** (port 8000) - File manipulation with access restrictions
2. **Confluence Cloud REST API v2** (port 8002) - Confluence page operations  
3. **Git Management API** (port 8003) - Git repository management
4. **RAG Retriever API** (port 8005) - Vector store queries using LangChain/FAISS
5. **User Info Proxy API** (port 8006) - User authentication details
6. **Summarizing Server** (port 8007) - LLM-based data summarization
7. **Secure Time Utilities API** (port 8008) - Time/timezone operations
8. **Weather API** (port 8009) - Weather data via Open-Meteo
9. **Open WebUI** (port 8080) - Web interface

## Ollama Models with Function Calling Support

### 🏆 **Top Recommendations:**

1. **`hhao/qwen2.5-coder-tools:latest`** - Specifically fine-tuned for tool use
2. **`llama3.3:latest`** - Meta's latest with excellent function calling (42 GB)
3. **`qwen2.5-coder:latest`** - Strong tool support and coding abilities (4.7 GB)

### 🥈 **Good Options:**

4. **`deepseek-r1:14b`** (9.0 GB) or **`deepseek-r1:32b`** (19 GB) - Great reasoning + tool use
5. **`llama3.1:8b`** (4.9 GB) - Reliable function calling support
6. **`phi4:latest`** (9.1 GB) - Microsoft's latest with good tool support
7. **`gemma3:latest`** (3.3 GB) - Google's model with function calling

### ⚡ **For Quick Testing:**

- **`hhao/qwen2.5-coder-tools:0.5b`** (994 MB) - Fastest, still has tool support
- **`hhao/qwen2.5-coder-tools:1.5b`** (1.6 GB) - Good balance of speed/capability
- **`hhao/qwen2.5-coder-tools:3b`** (1.9 GB) - More capability while staying compact

### ⚠️ **Limited/Unknown Function Calling:**

- Most uncensored variants
- Older models like llama2
- Code-specific models without instruction tuning

## Key Notes

- **Function calling support** is essential for OpenAPI/MCP integration
- Models with "tools" in their name are specifically optimized for this use case
- Latest versions from major providers (Meta, Qwen, Google, Microsoft) generally have the best support
- For production use, prioritize the top recommendations
- For development/testing, the smaller tool variants work well

## Next Steps

1. Test selected models with MCP bridge integration
2. Register servers with MCP Bridge Registry using: `python3 discover-servers.py --register`
3. Configure specific model preferences in MCP clients


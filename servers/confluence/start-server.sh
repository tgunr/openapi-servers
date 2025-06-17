#!/bin/zsh

# Confluence API Server Startup Script
# This script properly sets up the environment and starts the server

# Set up environment variables
export PYENV_ROOT="/Users/davec/.pyenv"
export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"

# Change to the project directory
cd "/Users/davec/AI/openapi-servers/servers/confluence" || exit 1

# Initialize pyenv if available
if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
fi

# Start the server
exec uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1


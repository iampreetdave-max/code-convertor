#!/bin/bash
# Code Converter - Startup Script

echo "=================================="
echo "  Code Converter - Starting..."
echo "=================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment variables (e.g. GROQ_API_KEY) from a local .env file if present.
# Copy .env.example to .env and add your key there. .env is gitignored.
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    . "$SCRIPT_DIR/.env"
    set +a
fi

# Change to backend directory
cd "$SCRIPT_DIR/backend"

if [ -n "$GROQ_API_KEY" ]; then
    echo "Groq API key: Set"
else
    echo "Groq API key: NOT set (create a .env file with GROQ_API_KEY=... - see .env.example)"
fi
echo ""
echo "=================================="
echo "  Open in browser:"
echo "  http://localhost:8080"
echo "=================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server on port 8080
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080

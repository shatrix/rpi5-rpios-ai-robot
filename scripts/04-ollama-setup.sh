#!/bin/bash
################################################################################
# 04: Ollama Setup
# Install Ollama LLM runtime
################################################################################

set -e

echo "=== Installing Ollama ==="

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "⚠️  Ollama already installed, skipping..."
    ollama --version
    exit 0
fi

echo "→ Downloading and installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
if ! command -v ollama &> /dev/null; then
    echo "❌ ERROR: Ollama installation failed!"
    exit 1
fi

echo "✓ Ollama installed: $(ollama --version)"

# Enable and start service
echo "→ Enabling Ollama service..."
systemctl enable ollama
systemctl start ollama

# Wait for service to be ready
echo "→ Waiting for Ollama service to start..."
sleep 5

MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if ollama list > /dev/null 2>&1; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ ERROR: Ollama service not ready after ${MAX_WAIT}s"
    systemctl status ollama
    exit 1
fi

echo "✓ Ollama service running"

echo ""
echo "  Ollama installed and running"
echo "  Service: ollama.service"
echo "  Status: systemctl status ollama"
echo ""

exit 0

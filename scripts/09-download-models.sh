#!/bin/bash
################################################################################
# 09: Download Ollama Models
# Download Llama 3.2:1b and Moondream models via Ollama
################################################################################

set -e

echo "=== Downloading Ollama Models ==="

# Wait for Ollama service
echo "→ Waiting for Ollama service..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if ollama list > /dev/null 2>&1; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ ERROR: Ollama service not ready!"
    systemctl status ollama
    exit 1
fi

echo "✓ Ollama service ready"

# Pull text model (Llama 3.2:1b)
echo "→ Pulling Llama 3.2:1b text model (~1GB)..."
echo "   This may take 5-15 minutes depending on internet speed..."
if ollama list | grep -q "llama3.2:1b"; then
    echo "⚠️  Text model already downloaded, skipping..."
else
    ollama pull llama3.2:1b
    echo "✓ Text model downloaded"
fi

# Pull vision model (Moondream)
echo "→ Pulling Moondream vision model (~1.7GB)..."
echo "   This may take 5-15 minutes depending on internet speed..."
if ollama list | grep -q "moondream"; then
    echo "⚠️  Vision model already downloaded, skipping..."
else
    ollama pull moondream
    echo "✓ Vision model downloaded"
fi


# Verify models
echo "→ Verifying installed models..."
ollama list

echo ""
echo "✓ All models downloaded successfully!"
echo ""
echo "  Available models:"
echo "    - llama3.2:1b (text chat, ~1GB)"
echo "    - moondream (vision, ~1.7GB, uses ~2.6GB RAM)"
echo ""

exit 0

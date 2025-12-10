#!/bin/bash
################################################################################
# 09: Download Ollama Models
# Download English + Arabic text models and Moondream vision model
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

# Pull English text model (Llama 3.2:1b)
echo "→ Pulling Llama 3.2:1b (English) text model (~1GB)..."
echo "   This may take 5-15 minutes depending on internet speed..."
if ollama list | grep -q "llama3.2:1b"; then
    echo "⚠️  English text model already downloaded, skipping..."
else
    ollama pull llama3.2:1b
    echo "✓ English text model downloaded"
fi

# Pull Arabic text model (prakasharyan/qwen-arabic)
echo "→ Pulling prakasharyan/qwen-arabic (Arabic) text model (~1.5GB)..."
echo "   This may take 5-15 minutes depending on internet speed..."
if ollama list | grep -q "prakasharyan/qwen-arabic"; then
    echo "⚠️  Arabic text model already downloaded, skipping..."
else
    ollama pull prakasharyan/qwen-arabic
    echo "✓ Arabic text model downloaded"
fi

# Pull vision model (Moondream - language agnostic)
echo "→ Pulling Moondream vision model (~1.7GB)..."
echo "   This may may take 5-15 minutes depending on internet speed..."
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
echo "    - llama3.2:1b (English text chat, ~1GB)"
echo "    - prakasharyan/qwen-arabic (Arabic text chat, ~1.5GB)"
echo "    - moondream (vision, ~1.7GB, language-agnostic)"
echo ""
echo "  Language selection:"
echo "    Configure in /etc/ai-chatbot/language.conf"
echo "    Or switch language anytime and restart services"
echo ""

exit 0

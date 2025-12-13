#!/bin/bash
################################################################################
# 04: Ollama Setup
# Install Ollama LLM runtime
################################################################################

set -e

# Parse arguments
RECONFIGURE=false
if [ "$1" = "--reconfigure" ]; then
    RECONFIGURE=true
fi

echo "=== Ollama Configuration ==="

# Configuration
CONFIG_FILE="/etc/ai-chatbot/config.ini"
CONFIG_DIR="/etc/ai-chatbot"

# Ensure config directory exists
mkdir -p "$CONFIG_DIR"

# Check if configuration already exists
if [ -f "$CONFIG_FILE" ] && [ "$RECONFIGURE" = false ]; then
    echo ""
    echo "✓ Configuration file already exists: $CONFIG_FILE"
    echo ""
    echo "Current Ollama configuration:"
    grep "ollama_host" "$CONFIG_FILE" || echo "  (unable to read config)"
    grep "network_vision_model" "$CONFIG_FILE" || echo ""
    echo ""
    echo "To reconfigure, run: sudo ./setup.sh --reconfigure"
    echo "Skipping configuration prompts..."
    echo ""
    
    # Continue to Ollama installation check
    SKIP_CONFIG=true
else
    SKIP_CONFIG=false
fi

if [ "$SKIP_CONFIG" = false ]; then
    # Prompt for Ollama configuration
    echo ""
    echo "Choose Ollama setup for vision processing:"
    echo "  1) Local Ollama (RPi5, ~60s per image with moondream)"
    echo "  2) Network Ollama (faster GPU server, ~2s per image)"
    echo ""
    read -p "Enter choice [1/2] (default: 1): " OLLAMA_CHOICE
    OLLAMA_CHOICE=${OLLAMA_CHOICE:-1}
    
    OLLAMA_HOST="local"
    NETWORK_MODEL="moondream"
    
    if [ "$OLLAMA_CHOICE" = "2" ]; then
        echo ""
        read -p "Enter network Ollama server IP address: " OLLAMA_IP
        read -p "Enter network Ollama server port (default: 11434): " OLLAMA_PORT
        OLLAMA_PORT=${OLLAMA_PORT:-11434}
        read -p "Enter vision model name on network server (e.g., qwen3-vl): " NETWORK_MODEL
        
        OLLAMA_HOST="${OLLAMA_IP}:${OLLAMA_PORT}"
        
        echo ""
        echo "✓ Network Ollama configured:"
        echo "  Host: $OLLAMA_HOST"
        echo "  Vision Model: $NETWORK_MODEL"
    else
        echo "✓ Using local Ollama"
    fi
    
    # Generate/update configuration file
    echo ""
    echo "→ Updating configuration file: $CONFIG_FILE"
    
    # If network mode, prompt for text model too
    NETWORK_TEXT_MODEL="llama3.2:3b"
    if [ "$OLLAMA_CHOICE" = "2" ]; then
        echo ""
        read -p "Enter text model name on network server (default: llama3.2:3b): " NETWORK_TEXT_MODEL_INPUT
        NETWORK_TEXT_MODEL=${NETWORK_TEXT_MODEL_INPUT:-llama3.2:3b}
    fi
    
    cat > "$CONFIG_FILE" << EOF
[ollama]
# Ollama server configuration
# Use 'local' for local Ollama server, or 'IP:PORT' for network server
ollama_host = $OLLAMA_HOST
# Vision model to use on network server (if ollama_host is not 'local')
network_vision_model = $NETWORK_MODEL
# Text model to use on network server (if ollama_host is not 'local')
network_text_model = $NETWORK_TEXT_MODEL
# Connection timeout for network Ollama (seconds)
network_timeout = 5

[llm]
# System prompt for concise answers (robot personality)
system_prompt = You are a helpful robot. Answer in 1 sentence maximum. Be direct and concise.
# Ollama models
text_model = llama3.2:1b
vision_model = moondream
max_tokens = 50
temperature = 0.7

[vosk]
# VOSK ASR settings
model_path = /usr/share/vosk-models/default
sample_rate = 16000

[audio]
# Audio device will be auto-detected by detect-audio.sh
# USB Audio Device is typically card 0 on RPi OS
microphone_device = plughw:0,0
speaker_device = auto
sample_rate = 16000

[camera]
enable = true
resolution = 640x480

[behavior]
# Auto-reset conversation after 5 minutes of inactivity
chat_history_timeout = 300
max_history_messages = 10
EOF
    
    chmod 644 "$CONFIG_FILE"
    echo "✓ Configuration saved to $CONFIG_FILE"
else
    # Read existing config to determine if we should skip local Ollama install
    OLLAMA_CHOICE="1"  # Default to local
    if grep -q "ollama_host = local" "$CONFIG_FILE" 2>/dev/null; then
        OLLAMA_CHOICE="1"
    else
        OLLAMA_CHOICE="2"
    fi
fi


# Skip local Ollama installation if using network server
if [ "$OLLAMA_CHOICE" = "2" ]; then
    echo ""
    echo "=== Skipping Local Ollama Installation (using network server) ==="
    echo ""
    echo "  Configuration complete"
    echo "  Network server: $OLLAMA_HOST"
    echo "  Vision model: $NETWORK_MODEL"
    echo ""
    exit 0
fi

echo ""
echo "=== Installing Local Ollama ==="

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

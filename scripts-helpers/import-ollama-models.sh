#!/bin/bash
################################################################################
# DEPRECATED: This script is no longer used
# Models are now downloaded directly via ollama pull in script 09
# 
# This script was used for manual GGUF downloads and imports
# Kept for reference only
################################################################################

MARKER_FILE="/var/lib/ollama/.models-imported"
LOG_FILE="/var/log/ollama-import.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if already imported
if [ -f "$MARKER_FILE" ]; then
    log "Models already imported, skipping"
    exit 0
fi

log "=== Starting Ollama Model Import ==="

# Wait for Ollama service to be ready (use ollama list instead of curl)
log "Waiting for Ollama service..."
MAX_WAIT=120  # Increased from 60s - Ollama takes longer on first boot
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if ollama list > /dev/null 2>&1; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log "ERROR: Ollama service not available after $MAX_WAIT seconds"
    exit 1
fi

log "✓ Ollama service is ready"

# Create Modelfile for text model (Qwen2.5-1.5B)
log "Importing text model: qwen2.5:1.5b"
cat > /tmp/Modelfile.text << 'EOF'
FROM /usr/share/ollama-models/qwen2.5-1.5b-instruct-q4_k_m.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 2048
SYSTEM "You are a helpful robot assistant. Answer questions in 2-3 sentences maximum. Be concise, direct, and friendly."
EOF

ollama create qwen2.5:1.5b -f /tmp/Modelfile.text 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
    log "✓ Text model imported successfully"
else
    log "ERROR: Failed to import text model"
    exit 1
fi

# Create Modelfile for vision model (Qwen2-VL-2B)
log "Importing vision model: qwen2-vl:2b"
cat > /tmp/Modelfile.vision << 'EOF'
FROM /usr/share/ollama-models/qwen2-vl-2b-instruct-q4_k_m.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
SYSTEM "You are a helpful AI assistant that can see and describe images. Answer questions about images in 2-3 sentences maximum. Be concise and direct."
EOF

ollama create qwen2-vl:2b -f /tmp/Modelfile.vision 2>&1 | tee -a "$LOG_FILE"
if [ $? -eq 0 ]; then
    log "✓ Vision model imported successfully"
else
    log "ERROR: Failed to import vision model"
    exit 1
fi

# Create marker file
touch "$MARKER_FILE"
log "=== Ollama Model Import Completed Successfully ==="

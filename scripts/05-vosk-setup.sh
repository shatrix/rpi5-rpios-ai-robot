#!/bin/bash
################################################################################
# 05: VOSK Setup
# Install VOSK Python package and download English model
################################################################################

set -e

echo "=== Installing VOSK ASR ==="

# Install VOSK Python package
echo "→ Installing VOSK Python package..."
pip3 install --break-system-packages vosk

# Verify installation
if ! python3 -c "import vosk" 2>/dev/null; then
    echo "❌ ERROR: VOSK Python package installation failed!"
    exit 1
fi

echo "✓ VOSK Python package installed"

# Create model directory
MODEL_DIR="/usr/share/vosk-models"
mkdir -p "$MODEL_DIR"

# Download small English model (vosk-model-small-en-us-0.15)
MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_ZIP="${MODEL_NAME}.zip"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_ZIP}"

if [ -d "$MODEL_DIR/$MODEL_NAME" ]; then
    echo "⚠️  VOSK model already downloaded, skipping..."
else
    echo "→ Downloading VOSK English model (~40MB)..."
    echo "   URL: $MODEL_URL"
    
    cd /tmp
    wget -q --show-progress "$MODEL_URL"
    
    echo "→ Extracting model..."
    unzip -q "$MODEL_ZIP"
    
    echo "→ Installing model to $MODEL_DIR..."
    mv "$MODEL_NAME" "$MODEL_DIR/"
    
    # Cleanup
    rm "$MODEL_ZIP"
    
    echo "✓ VOSK model installed"
fi

# Create symlink for easy access
ln -sf "$MODEL_DIR/$MODEL_NAME" "$MODEL_DIR/default"

# Verify model
if [ ! -d "$MODEL_DIR/default" ]; then
    echo "❌ ERROR: VOSK model not found!"
    exit 1
fi

echo "✓ VOSK model verified: $MODEL_DIR/default"

# Create wrapper script for compatibility (AI chatbot will use Python API directly)
echo "→ Creating vosk-transcribe wrapper script..."
cat > /usr/local/bin/vosk-transcribe << 'EOF'
#!/usr/bin/env python3
"""
VOSK transcription wrapper
Transcribes WAV audio file and outputs text to stdout
"""
import sys
import json
import wave
from vosk import Model, KaldiRecognizer

if len(sys.argv) < 2:
    print("Usage: vosk-transcribe <audio.wav>", file=sys.stderr)
    sys.exit(1)

audio_file = sys.argv[1]
model_path = "/usr/share/vosk-models/default"

# Load model
model = Model(model_path)

# Open audio file
wf = wave.open(audio_file, "rb")

# Check format
if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
    print("ERROR: Audio must be WAV format mono PCM.", file=sys.stderr)
    sys.exit(1)

# Create recognizer
rec = KaldiRecognizer(model, wf.getframerate())
rec.SetWords(True)

# Process audio
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    rec.AcceptWaveform(data)

# Get final result
result = json.loads(rec.FinalResult())
print(result.get("text", ""))
EOF

chmod +x /usr/local/bin/vosk-transcribe

echo "✓ vosk-transcribe wrapper created"

echo ""
echo "  VOSK ASR installed:"
echo "    Model: vosk-model-small-en-us-0.15 (40MB, WER ~9.85%)"
echo "    Path: $MODEL_DIR/default"
echo "    Wrapper: /usr/local/bin/vosk-transcribe"
echo ""
echo "  To upgrade to larger model (better accuracy, more RAM):"
echo "    wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
echo "    unzip vosk-model-en-us-0.22.zip"
echo "    sudo rm -rf $MODEL_DIR/vosk-model-small-en-us-0.15"
echo "    sudo mv vosk-model-en-us-0.22 $MODEL_DIR/"
echo "    sudo ln -sf $MODEL_DIR/vosk-model-en-us-0.22 $MODEL_DIR/default"
echo ""

exit 0

#!/bin/bash
################################################################################
# 05: VOSK Setup
# Install VOSK Python package and download English + Arabic models
# User selects preferred language during setup
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

# Language selection prompt (if not already configured)
if [ ! -f "/etc/ai-chatbot/language.conf" ]; then
    echo ""
    echo "═══════════════════════════════════════"
    echo "   Language Selection"
    echo "═══════════════════════════════════════"
    echo ""
    echo "Which language would you like to use?"
    echo "  1) English (en)"
    echo "  2) Arabic (ar) - العربية"
    echo ""
    read -p "Enter choice [1-2]: " lang_choice
    
    case $lang_choice in
        1) ROBOT_LANGUAGE="en" ;;
        2) ROBOT_LANGUAGE="ar" ;;
        *) echo "Invalid choice, defaulting to English"; ROBOT_LANGUAGE="en" ;;
    esac
    
    # Save choice to config
    mkdir -p /etc/ai-chatbot
    echo "LANGUAGE=$ROBOT_LANGUAGE" > /etc/ai-chatbot/language.conf
    echo "✓ Language set to: $ROBOT_LANGUAGE"
else
    # Load existing language choice
    ROBOT_LANGUAGE=$(grep "^LANGUAGE=" /etc/ai-chatbot/language.conf | cut -d= -f2)
    echo "✓ Using existing language: $ROBOT_LANGUAGE"
fi

echo ""
echo "→ Downloading BOTH English and Arabic models for flexibility..."
echo ""

# Download English model (vosk-model-small-en-us-0.15)
EN_MODEL_NAME="vosk-model-small-en-us-0.15"
EN_MODEL_ZIP="${EN_MODEL_NAME}.zip"
EN_MODEL_URL="https://alphacephei.com/vosk/models/${EN_MODEL_ZIP}"

if [ -d "$MODEL_DIR/$EN_MODEL_NAME" ]; then
    echo "⚠️  English VOSK model already downloaded, skipping..."
else
    echo "→ Downloading VOSK English model (~40MB)..."
    echo "   URL: $EN_MODEL_URL"
    
    cd /tmp
    wget -q --show-progress "$EN_MODEL_URL"
    
    echo "→ Extracting English model..."
    unzip -q "$EN_MODEL_ZIP"
    
    echo "→ Installing English model to $MODEL_DIR..."
    mv "$EN_MODEL_NAME" "$MODEL_DIR/"
    
    # Cleanup
    rm "$EN_MODEL_ZIP"
    
    echo "✓ English VOSK model installed"
fi

# Download Arabic model (vosk-model-ar-mgb2-0.4)
AR_MODEL_NAME="vosk-model-ar-mgb2-0.4"
AR_MODEL_ZIP="${AR_MODEL_NAME}.zip"
AR_MODEL_URL="https://alphacephei.com/vosk/models/${AR_MODEL_ZIP}"

if [ -d "$MODEL_DIR/$AR_MODEL_NAME" ]; then
    echo "⚠️  Arabic VOSK model already downloaded, skipping..."
else
    echo "→ Downloading VOSK Arabic model (~318MB)..."
    echo "   URL: $AR_MODEL_URL"
    
    cd /tmp
    wget -q --show-progress "$AR_MODEL_URL"
    
    echo "→ Extracting Arabic model..."
    unzip -q "$AR_MODEL_ZIP"
    
    echo "→ Installing Arabic model to $MODEL_DIR..."
    mv "$AR_MODEL_NAME" "$MODEL_DIR/"
    
    # Cleanup
    rm "$AR_MODEL_ZIP"
    
    echo "✓ Arabic VOSK model installed"
fi

# Create symlink to selected language model
if [ "$ROBOT_LANGUAGE" = "ar" ]; then
    ln -sf "$MODEL_DIR/$AR_MODEL_NAME" "$MODEL_DIR/default"
    ACTIVE_MODEL="$AR_MODEL_NAME (Arabic)"
else
    ln -sf "$MODEL_DIR/$EN_MODEL_NAME" "$MODEL_DIR/default"
    ACTIVE_MODEL="$EN_MODEL_NAME (English)"
fi

# Verify model
if [ ! -d "$MODEL_DIR/default" ]; then
    echo "❌ ERROR: VOSK model symlink creation failed!"
    exit 1
fi

echo "✓ Active model: $ACTIVE_MODEL"
echo "✓ Model path: $MODEL_DIR/default"

# Create wrapper script for compatibility
echo "→ Creating vosk-transcribe wrapper script..."
cat > /usr/local/bin/vosk-transcribe <<'EOF'
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
echo "    English model: vosk-model-small-en-us-0.15 (40MB, WER ~9.85%)"
echo "    Arabic model: vosk-model-ar-mgb2-0.4 (318MB, WER ~16.4%)"
echo "    Active: $ACTIVE_MODEL"
echo "    Path: $MODEL_DIR/default"
echo "    Wrapper: /usr/local/bin/vosk-transcribe"
echo ""
echo "  To switch language after setup:"
echo "    Edit /etc/ai-chatbot/language.conf"
echo "    Then restart: sudo systemctl restart ai-chatbot shatrox-buttons"
echo ""

exit 0

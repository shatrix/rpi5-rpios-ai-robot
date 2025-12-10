#!/bin/bash
################################################################################
# 06: Piper TTS Setup
# Install Piper binary and download English + Arabic voice models
################################################################################

set -e

echo "=== Installing Piper TTS ==="

PIPER_VERSION="2023.11.14-2"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_aarch64.tar.gz"
VOICES_DIR="/usr/share/piper-voices"

# Download and install Piper binary
if [ -f "/usr/local/bin/piper" ]; then
    echo "⚠️  Piper already installed, skipping binary..."
else
    echo "→ Downloading Piper TTS (~200MB)..."
    echo "   URL: $PIPER_URL"
    
    cd /tmp
    wget -q --show-progress "$PIPER_URL" -O piper.tar.gz
    
    echo "→ Extracting Piper..."
    tar -xzf piper.tar.gz
    
    echo "→ Installing Piper binary..."
    install -m 0755 piper/piper /usr/local/bin/piper
    
    # Install bundled libraries
    mkdir -p /usr/local/lib/piper
    cp piper/*.so* /usr/local/lib/piper/ 2>/dev/null || true
    
    # Install espeak-ng data
    if [ -d "piper/espeak-ng-data" ]; then
        mkdir -p /usr/share/espeak-ng-data
        cp -r piper/espeak-ng-data/* /usr/share/espeak-ng-data/
    fi
    
    # Add library path to ldconfig
    echo "/usr/local/lib/piper" > /etc/ld.so.conf.d/piper.conf
    ldconfig
    
    # Cleanup
    rm -rf piper piper.tar.gz
    
    echo "✓ Piper binary installed"
fi

# Verify Piper
if ! /usr/local/bin/piper --version > /dev/null 2>&1; then
    echo "❌ ERROR: Piper installation failed!"
    exit 1
fi

echo "✓ Piper verified: $(/usr/local/bin/piper --version 2>&1 | head -1)"

# Create voices directory
mkdir -p "$VOICES_DIR"

# Load language preference (default to English if not set)
if [ -f "/etc/ai-chatbot/language.conf" ]; then
    ROBOT_LANGUAGE=$(grep "^LANGUAGE=" /etc/ai-chatbot/language.conf | cut -d= -f2)
else
    ROBOT_LANGUAGE="en"
fi

echo "→ Downloading voice models for both English and Arabic..."
echo ""

# Voice 1: en_US-ryan-medium (English male, natural)
EN_VOICE_BASE="en_US-ryan-medium"
EN_VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium"
if [ ! -f "$VOICES_DIR/${EN_VOICE_BASE}.onnx" ]; then
    echo "   Downloading ${EN_VOICE_BASE} voice..."
    wget -q --show-progress \
        "${EN_VOICE_URL}/${EN_VOICE_BASE}.onnx" \
        -O "$VOICES_DIR/${EN_VOICE_BASE}.onnx"
    wget -q \
        "${EN_VOICE_URL}/${EN_VOICE_BASE}.onnx.json" \
        -O "$VOICES_DIR/${EN_VOICE_BASE}.onnx.json"
    echo "   ✓ ${EN_VOICE_BASE} downloaded"
else
    echo "   ⚠️  ${EN_VOICE_BASE} already exists, skipping..."
fi

# Voice 2: ar_JO-kareem-medium (Arabic male)
AR_VOICE_BASE="ar_JO-kareem-medium"
AR_VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium"
if [ ! -f "$VOICES_DIR/${AR_VOICE_BASE}.onnx" ]; then
    echo "   Downloading ${AR_VOICE_BASE} voice..."
    wget -q --show-progress \
        "${AR_VOICE_URL}/${AR_VOICE_BASE}.onnx" \
        -O "$VOICES_DIR/${AR_VOICE_BASE}.onnx"
    wget -q \
        "${AR_VOICE_URL}/${AR_VOICE_BASE}.onnx.json" \
        -O "$VOICES_DIR/${AR_VOICE_BASE}.onnx.json"
    echo "   ✓ ${AR_VOICE_BASE} downloaded"
else
    echo "   ⚠️  ${AR_VOICE_BASE} already exists, skipping..."
fi

# Create default symlink based on language preference
if [ "$ROBOT_LANGUAGE" = "ar" ]; then
    ln -sf "${AR_VOICE_BASE}.onnx" "$VOICES_DIR/default.onnx"
    ln -sf "${AR_VOICE_BASE}.onnx.json" "$VOICES_DIR/default.onnx.json"
    DEFAULT_VOICE="$AR_VOICE_BASE (Arabic)"
else
    ln -sf "${EN_VOICE_BASE}.onnx" "$VOICES_DIR/default.onnx"
    ln -sf "${EN_VOICE_BASE}.onnx.json" "$VOICES_DIR/default.onnx.json"
    DEFAULT_VOICE="$EN_VOICE_BASE (English)"
fi

echo "✓ Voice models installed"
echo "✓ Default voice: $DEFAULT_VOICE"

# Test Piper
echo "→ Testing Piper TTS..."
if echo "Test" | /usr/local/bin/piper --model "$VOICES_DIR/default.onnx" --output_file /tmp/piper-test.wav > /dev/null 2>&1; then
    echo "✓ Piper test successful"
    rm /tmp/piper-test.wav
else
    echo "❌ ERROR: Piper test failed!"
    exit 1
fi

echo ""
echo "  Piper TTS installed:"
echo "    Binary: /usr/local/bin/piper"
echo "    Voices: $VOICES_DIR"
echo "    English voice: en_US-ryan-medium (male, natural)"
echo "    Arabic voice: ar_JO-kareem-medium (male)"
echo "    Default: $DEFAULT_VOICE"
echo ""
echo "  To switch language after setup:"
echo "    Edit /etc/ai-chatbot/language.conf"
echo "    Then restart: sudo systemctl restart ai-chatbot shatrox-buttons"
echo ""

exit 0

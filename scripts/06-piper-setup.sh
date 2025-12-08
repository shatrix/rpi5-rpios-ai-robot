#!/bin/bash
################################################################################
# 06: Piper TTS Setup
# Install Piper binary and voice models
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

# Download voice models
echo "→ Downloading Piper voice models..."

# Voice 1: en_US-ryan-medium (male, natural)
RYAN_BASE="en_US-ryan-medium"
if [ ! -f "$VOICES_DIR/${RYAN_BASE}.onnx" ]; then
    echo "   Downloading ${RYAN_BASE} voice..."
    wget -q --show-progress \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/${RYAN_BASE}.onnx" \
        -O "$VOICES_DIR/${RYAN_BASE}.onnx"
    wget -q \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/${RYAN_BASE}.onnx.json" \
        -O "$VOICES_DIR/${RYAN_BASE}.onnx.json"
    echo "   ✓ ${RYAN_BASE} downloaded"
else
    echo "   ⚠️  ${RYAN_BASE} already exists, skipping..."
fi

# Voice 2: en_US-lessac-medium (male, clear)
LESSAC_BASE="en_US-lessac-medium"
if [ ! -f "$VOICES_DIR/${LESSAC_BASE}.onnx" ]; then
    echo "   Downloading ${LESSAC_BASE} voice..."
    wget -q --show-progress \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/${LESSAC_BASE}.onnx" \
        -O "$VOICES_DIR/${LESSAC_BASE}.onnx"
    wget -q \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/${LESSAC_BASE}.onnx.json" \
        -O "$VOICES_DIR/${LESSAC_BASE}.onnx.json"
    echo "   ✓ ${LESSAC_BASE} downloaded"
else
    echo "   ⚠️  ${LESSAC_BASE} already exists, skipping..."
fi

# Create default symlink (ryan as default)
ln -sf "${RYAN_BASE}.onnx" "$VOICES_DIR/default.onnx"
ln -sf "${RYAN_BASE}.onnx.json" "$VOICES_DIR/default.onnx.json"

echo "✓ Voice models installed"

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
echo "    Default: ryan-medium (male, natural)"
echo ""
echo "  Available voices:"
echo "    - en_US-ryan-medium (default)"
echo "    - en_US-lessac-medium"
echo ""

exit 0

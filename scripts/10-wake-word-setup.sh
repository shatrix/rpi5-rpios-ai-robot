#!/bin/bash
################################################################################
# Step 10: Wake Word Detection Setup
# Installs OpenWakeWord and downloads pre-trained models
################################################################################

source "$(dirname "$0")/lib/setup-state.sh" || exit 1

log() {
    echo -e "\033[0;32m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m $1"
}

error() {
    echo -e "\033[0;31m[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:\033[0m $1"
}

info() {
    echo -e "\033[0;36m[$(date '+%Y-%m-%d %H:%M:%S')] INFO:\033[0m $1"
}

echo "========================================="
log "Installing Wake Word Detection (OpenWakeWord)"
echo "========================================="
echo ""

# Step 1: Install system dependencies for PyAudio
log "Installing system dependencies for PyAudio..."
apt-get install -y portaudio19-dev python3-pyaudio 2>&1 | tee -a /var/log/rpi5-ai-robot-setup.log

if [ $? -ne 0 ]; then
    error "Failed to install portaudio dependencies"
    exit 1
fi

log "✓ PortAudio installed"
echo ""

# Step 2: Install Python dependencies
log "Installing OpenWakeWord and VAD Python packages..."
pip3 install --break-system-packages openwakeword>=0.6.0 pyaudio numpy pysilero-vad==1.0.0 webrtc-noise-gain==1.2.3 2>&1 | tee -a /var/log/rpi5-ai-robot-setup.log

if [ $? -ne 0 ]; then
    error "Failed to install OpenWakeWord Python packages"
    exit 1
fi

log "✓ OpenWakeWord, Silero VAD, and webrtc-noise-gain packages installed"
echo ""

# Step 3: Create model directory
log "Creating wake word model directory..."
mkdir -p /usr/share/openwakeword-models
chmod 755 /usr/share/openwakeword-models

log "✓ Model directory created"
echo ""

# Step 4: Download pre-trained wake word models
log "Downloading pre-trained wake word models..."

cd /usr/share/openwakeword-models

# Download Hey Jarvis model from GitHub releases v0.5.1 (temporary, will be replaced with custom "Hey Ruby")
info "Downloading 'Hey Jarvis' model (temporary wake word)..."
if ! wget -q --show-progress -O hey_jarvis_v0.1.onnx \
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_jarvis_v0.1.onnx" 2>&1 | tee -a /var/log/rpi5-ai-robot-setup.log; then
    error "Failed to download Hey Jarvis model"
    exit 1
fi

# Download Alexa model (backup option) from same release
info "Downloading 'Alexa' model (backup option)..."
if ! wget -q --show-progress -O alexa_v0.1.onnx \
    "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/alexa_v0.1.onnx" 2>&1 | tee -a /var/log/rpi5-ai-robot-setup.log; then
    error "Failed to download Alexa model"
    exit 1
fi

log "✓ Pre-trained models downloaded"
echo ""

# Step 5: Create feedback sound (ding)
log "Creating wake word feedback sound..."
mkdir -p /usr/share/sounds

# Generate a simple ding sound using sox (or provide a pre-recorded one)
if command -v sox &> /dev/null; then
    # Two-tone chime (more noticeable)
    sox -n -r 22050 -c 1 /usr/share/sounds/wake.wav synth 0.15 sine 523 synth 0.15 sine 659 fade 0 0.15 0.05 2>&1 | tee -a /var/log/rpi5-ai-robot-setup.log
    if [ $? -eq 0 ]; then
        log "✓ Generated wake word feedback sound"
    else
        info "Could not generate sound file, will use existing sound"
    fi
else
    info "sox not installed, skipping ding sound generation"
    info "You can manually add /usr/share/sounds/wake.wav later"
fi

echo ""

# Step 6: Display information
echo "========================================="
log "Wake Word Detection Setup Complete!"
echo "========================================="
echo ""
echo "Installed models:"
echo "  - Hey Jarvis (temporary wake word)"
echo "  - Alexa (backup option)"
echo ""
echo "Model directory: /usr/share/openwakeword-models"
echo ""
echo "NEXT STEPS:"
echo "  1. The system will initially use 'Hey Jarvis' as the wake word"
echo "  2. To train a custom 'Hey Ruby' model:"
echo "     - Open: https://github.com/dscripka/openWakeWord#custom-models"
echo "     - Use Google Colab to train 'hey ruby' model (~1 hour)"
echo "     - Download hey_ruby_v1.tflite"
echo "     - Copy to /usr/share/openwakeword-models/"
echo "     - Update /etc/ai-chatbot/config.ini to use 'hey_ruby_v1'"
echo ""
echo "Configuration:"
echo "  /etc/ai-chatbot/config.ini [wake_word] section"
echo ""

exit 0

#!/bin/bash
################################################################################
# 08: Install Services
# Install Python scripts, QML app, helper scripts, and systemd services
################################################################################

set -e

# Smart install function: only copy if files differ or destination doesn't exist
# Usage: smart_install <mode> <source> <destination>
smart_install() {
    local mode="$1"
    local source="$2"
    local dest="$3"
    
    # Check if source exists
    if [ ! -f "$source" ]; then
        echo "  ❌ ERROR: Source file not found: $source"
        return 1
    fi
    
    # If destination doesn't exist, install it
    if [ ! -f "$dest" ]; then
        install -m "$mode" "$source" "$dest"
        echo "  ✓ Installed: $(basename "$dest") [NEW]"
        return 0
    fi
    
    # Compare checksums
    local src_sum=$(md5sum "$source" | awk '{print $1}')
    local dst_sum=$(md5sum "$dest" | awk '{print $1}')
    
    if [ "$src_sum" != "$dst_sum" ]; then
        install -m "$mode" "$source" "$dest"
        echo "  ✓ Updated: $(basename "$dest") [MODIFIED]"
        return 0
    else
        echo "  ⊘ Unchanged: $(basename "$dest")"
        return 0
    fi
}



echo "=== Installing Application Services ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Install Python dependencies
echo "→ Installing Python dependencies..."

# Install libgpiod system library first (required for gpiod Python package)
apt install -y libgpiod-dev

# Install Python packages
pip3 install --break-system-packages ollama gpiod

# Install Python scripts
echo "→ Installing Python service scripts..."
smart_install 0755 "$SCRIPT_DIR/python/ai-chatbot.py" /usr/local/bin/ai-chatbot.py
smart_install 0755 "$SCRIPT_DIR/python/shatrox-buttons.py" /usr/local/bin/shatrox-buttons.py
smart_install 0755 "$SCRIPT_DIR/python/motor_controller.py" /usr/local/bin/motor_controller.py

# Install Waveshare PCA9685 library for motor control
if [ -f "$SCRIPT_DIR/python/WavesharePCA9685.py" ]; then
    smart_install 0644 "$SCRIPT_DIR/python/WavesharePCA9685.py" /usr/local/lib/python3.13/dist-packages/WavesharePCA9685.py
    echo "✓ Waveshare PCA9685 library installed"
fi

echo "✓ Python scripts installed"

# Install helper scripts
echo "→ Installing helper scripts..."
smart_install 0755 "$SCRIPT_DIR/scripts-helpers/speak" /usr/local/bin/speak
smart_install 0755 "$SCRIPT_DIR/scripts-helpers/detect-audio.sh" /usr/local/bin/detect-audio.sh
smart_install 0755 "$SCRIPT_DIR/scripts-helpers/import-ollama-models.sh" /usr/local/bin/import-ollama-models.sh
smart_install 0755 "$SCRIPT_DIR/scripts-helpers/startup-sound.sh" /usr/local/bin/startup-sound.sh

echo "✓ Helper scripts installed"

# Install QML display app
echo "→ Installing QML robot face display..."
mkdir -p /usr/share/shatrox
smart_install 0644 "$SCRIPT_DIR/qml/shatrox-display.qml" /usr/share/shatrox/shatrox-display.qml
smart_install 0755 "$SCRIPT_DIR/qml/shatrox-display-start" /usr/local/bin/shatrox-display-start
smart_install 0755 "$SCRIPT_DIR/qml/shatrox-touch-monitor" /usr/local/bin/shatrox-touch-monitor
smart_install 0755 "$SCRIPT_DIR/qml/shatrox-volume-monitor" /usr/local/bin/shatrox-volume-monitor

echo "✓ QML app installed"

# Install configuration
echo "→ Installing AI chatbot configuration..."
mkdir -p /etc/ai-chatbot
# Only install default config if it doesn't exist
if [ ! -f /etc/ai-chatbot/config.ini ]; then
    smart_install 0644 "$SCRIPT_DIR/config/ai-chatbot.ini" /etc/ai-chatbot/config.ini
    echo "  ✓ Default configuration installed"
else
    echo "  ⊘ Configuration already exists, skipping..."
fi

echo "✓ Configuration checked"

# Install systemd service files
echo "→ Installing systemd service units..."
smart_install 644 "${SCRIPT_DIR}/services/ai-chatbot.service" /etc/systemd/system/ai-chatbot.service
smart_install 644 "${SCRIPT_DIR}/services/shatrox-buttons.service" /etc/systemd/system/shatrox-buttons.service
smart_install 644 "${SCRIPT_DIR}/services/shatrox-display.service" /etc/systemd/system/shatrox-display.service
smart_install 644 "${SCRIPT_DIR}/services/shatrox-touch-monitor.service" /etc/systemd/system/shatrox-touch-monitor.service
smart_install 644 "${SCRIPT_DIR}/services/shatrox-volume-monitor.service" /etc/systemd/system/shatrox-volume-monitor.service
smart_install 644 "${SCRIPT_DIR}/services/startup-sound.service" /etc/systemd/system/startup-sound.service
smart_install 644 "${SCRIPT_DIR}/services/shatrox-motor-control.service" /etc/systemd/system/shatrox-motor-control.service


# Reload systemd and enable services
echo "→ Enabling and starting services..."
systemctl daemon-reload
systemctl enable ai-chatbot.service
systemctl enable shatrox-buttons.service
systemctl enable shatrox-display.service
systemctl enable shatrox-touch-monitor.service
systemctl enable shatrox-volume-monitor.service
systemctl enable startup-sound.service
systemctl enable shatrox-motor-control.service

echo "✓ Services enabled"

# Create log file and required directories
echo "→ Creating runtime directories..."
mkdir -p /tmp/ai-recordings
mkdir -p /tmp/ai-camera
chmod 777 /tmp/ai-recordings /tmp/ai-camera

touch /tmp/shatrox-display.log
chmod 666 /tmp/shatrox-display.log

touch /var/log/robot-ai.log
chmod 666 /var/log/robot-ai.log

echo "✓ Runtime directories created"

# Install logrotate configuration
echo "→ Installing logrotate configuration..."
if [ -f "$SCRIPT_DIR/configs/logrotate-ai-robot" ]; then
    smart_install 644 "$SCRIPT_DIR/configs/logrotate-ai-robot" /etc/logrotate.d/ai-robot
    echo "✓ Log rotation configured (weekly, keep 4 weeks)"
else
    echo "  ⚠ Warning: logrotate config not found, skipping..."
fi

echo ""
echo "  Services installed:"
echo "    - ai-chatbot.service (AI orchestration)"
echo "    - shatrox-buttons.service (GPIO button monitoring)"
echo "    - shatrox-display.service (QML robot face)"
echo "    - shatrox-touch-monitor.service (Touch detection)"
echo "    - shatrox-volume-monitor.service (Volume display)"
echo "    - shatrox-motor-control.service (Motor control with obstacle detection)"
echo ""
echo "  All services enabled to start on boot"
echo ""

exit 0

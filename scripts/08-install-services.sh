#!/bin/bash
################################################################################
# 08: Install Services
# Install Python scripts, QML app, helper scripts, and systemd services
################################################################################

set -e

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
install -m 0755 "$SCRIPT_DIR/python/ai-chatbot.py" /usr/local/bin/
install -m 0755 "$SCRIPT_DIR/python/shatrox-buttons.py" /usr/local/bin/

echo "✓ Python scripts installed"

# Install helper scripts
echo "→ Installing helper scripts..."
install -m 0755 "$SCRIPT_DIR/scripts-helpers/speak" /usr/local/bin/
install -m 0755 "$SCRIPT_DIR/scripts-helpers/detect-audio.sh" /usr/local/bin/
install -m 0755 "$SCRIPT_DIR/scripts-helpers/import-ollama-models.sh" /usr/local/bin/
install -m 0755 "$SCRIPT_DIR/scripts-helpers/startup-sound.sh" /usr/local/bin/

echo "✓ Helper scripts installed"

# Install QML display app
echo "→ Installing QML robot face display..."
mkdir -p /usr/share/shatrox
install -m 0644 "$SCRIPT_DIR/qml/shatrox-display.qml" /usr/share/shatrox/
install -m 0755 "$SCRIPT_DIR/qml/shatrox-display-start" /usr/local/bin/
install -m 0755 "$SCRIPT_DIR/qml/shatrox-touch-monitor" /usr/local/bin/

echo "✓ QML app installed"

# Install configuration
echo "→ Installing AI chatbot configuration..."
mkdir -p /etc/ai-chatbot
install -m 0644 "$SCRIPT_DIR/config/ai-chatbot.ini" /etc/ai-chatbot/config.ini

echo "✓ Configuration installed"

# Install systemd service files
echo "→ Installing systemd service units..."
install -m 644 "${SCRIPT_DIR}/../services/ai-chatbot.service" /etc/systemd/system/
install -m 644 "${SCRIPT_DIR}/../services/shatrox-buttons.service" /etc/systemd/system/
install -m 644 "${SCRIPT_DIR}/../services/shatrox-display.service" /etc/systemd/system/
install -m 644 "${SCRIPT_DIR}/../services/shatrox-touch-monitor.service" /etc/systemd/system/
install -m 644 "${SCRIPT_DIR}/../services/startup-sound.service" /etc/systemd/system/

# Reload systemd and enable services
echo "→ Enabling and starting services..."
systemctl daemon-reload
systemctl enable ai-chatbot.service
systemctl enable shatrox-buttons.service
systemctl enable shatrox-display.service
systemctl enable shatrox-touch-monitor.service
systemctl enable startup-sound.service

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

echo ""
echo "  Services installed:"
echo "    - ai-chatbot.service (AI orchestration)"
echo "    - shatrox-buttons.service (GPIO button monitoring)"
echo "    - shatrox-display.service (QML robot face)"
echo "    - shatrox-touch-monitor.service (Touch detection)"
echo ""
echo "  All services enabled to start on boot"
echo ""

exit 0

#!/bin/bash
################################################################################
# RPi 5 AI Robot Setup Script
# Main orchestrator for automated installation
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log file
SETUP_LOG="/var/log/rpi5-ai-robot-setup.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$SETUP_LOG"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$SETUP_LOG"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$SETUP_LOG"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (use sudo)"
    exit 1
fi

# Banner
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        RPi 5 AI Robot Automated Setup                       ║"
echo "║        Raspberry Pi OS (Debian 13)                          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

log "Setup started. Logging to: $SETUP_LOG"
log "Script directory: $SCRIPT_DIR"

# Create log file
touch "$SETUP_LOG"
chmod 644 "$SETUP_LOG"

# Installation steps
STEPS=(
    "00-system-preparation.sh"
    "01-system-dependencies.sh"
    "02-hardware-config.sh"
    "03-audio-config.sh"
    "04-ollama-setup.sh"
    "05-vosk-setup.sh"
    "06-piper-setup.sh"
    "07-camera-setup.sh"
    "08-install-services.sh"
    "09-download-models.sh"
)

TOTAL_STEPS=${#STEPS[@]}
CURRENT_STEP=0

for step_script in "${STEPS[@]}"; do
    CURRENT_STEP=$((CURRENT_STEP + 1))
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    log "Step $CURRENT_STEP/$TOTAL_STEPS: Running $step_script"
    echo "════════════════════════════════════════════════════════════"
    
    STEP_PATH="$SCRIPT_DIR/scripts/$step_script"
    
    if [ ! -f "$STEP_PATH" ]; then
        error "Step script not found: $STEP_PATH"
        exit 1
    fi
    
    # Make executable
    chmod +x "$STEP_PATH"
    
    # Run step
    if ! "$STEP_PATH"; then
        error "Step $step_script failed!"
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                     SETUP FAILED                             ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Check the log file for details: $SETUP_LOG"
        echo ""
        echo "To rollback changes:"
        echo "  sudo systemctl stop ai-chatbot shatrox-buttons shatrox-display"
        echo "  sudo systemctl disable ai-chatbot shatrox-buttons shatrox-display"
        echo ""
        exit 1
    fi
    
    log "✓ Step $CURRENT_STEP/$TOTAL_STEPS completed successfully"
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║               SETUP COMPLETED SUCCESSFULLY!                  ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
log "All installation steps completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Reboot the system:"
echo "     sudo reboot"
echo ""
echo "  2. After reboot, services will start automatically:"
echo "     - Ollama (LLM server)"
echo "     - AI Chatbot (orchestration)"
echo "     - Button Service (GPIO monitoring)"
echo "     - Display App (QML robot face)"
echo ""
echo " 3. Check service status:"
echo "     sudo systemctl status ollama ai-chatbot shatrox-buttons shatrox-display"
echo ""
echo "  4. View logs:"
echo "     sudo journalctl -u ai-chatbot -f"
echo ""
echo "Enjoy your AI robot!"
echo ""

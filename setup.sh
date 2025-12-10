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
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
SETUP_LOG="/var/log/rpi5-ai-robot-setup.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source state management library
source "$SCRIPT_DIR/scripts/lib/setup-state.sh"

# Mode flags
FORCE_MODE=false
RECONFIGURE_MODE=false
SINGLE_STEP=""
FROM_STEP=""

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$SETUP_LOG"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$SETUP_LOG"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$SETUP_LOG"
}

info() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$SETUP_LOG"
}

# Show usage
show_usage() {
    cat << EOF
Usage: sudo ./setup.sh [OPTIONS]

Options:
  (no options)          Smart mode: skip already completed steps (default)
  --force               Force re-run all steps from scratch
  --step N              Run only step N (e.g., --step 04)
  --from-step N         Resume from step N onwards
  --reconfigure         Force reconfiguration prompts even if configs exist
  --reset-state         Clear all completion tracking and exit
  --help                Show this help message

Examples:
  sudo ./setup.sh                    # Smart mode
  sudo ./setup.sh --force            # Re-run everything
  sudo ./setup.sh --step 04          # Run only Ollama setup
  sudo ./setup.sh --from-step 06     # Resume from Piper setup
  sudo ./setup.sh --reconfigure      # Re-prompt for configurations

EOF
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_MODE=true
            shift
            ;;
        --reconfigure)
            RECONFIGURE_MODE=true
            shift
            ;;
        --step)
            SINGLE_STEP="$2"
            shift 2
            ;;
        --from-step)
            FROM_STEP="$2"
            shift 2
            ;;
        --reset-state)
            reset_state
            exit 0
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

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

# Display mode
if [ "$FORCE_MODE" = true ]; then
    # If --force is used with --step or --from-step, don't reset state
    # Just ignore completion checks for selected steps
    if [ -z "$SINGLE_STEP" ] && [ -z "$FROM_STEP" ]; then
        warning "FORCE MODE: Re-running all steps from scratch"
        reset_state
    else
        warning "FORCE MODE: Ignoring completion status for selected step(s)"
    fi
elif [ -n "$SINGLE_STEP" ]; then
    info "SINGLE STEP MODE: Running only step $SINGLE_STEP"
elif [ -n "$FROM_STEP" ]; then
    info "RESUME MODE: Starting from step $FROM_STEP"
else
    info "SMART MODE: Skipping previously completed steps"
fi

if [ "$RECONFIGURE_MODE" = true ]; then
    info "RECONFIGURE MODE: Will prompt for all configurations"
fi

echo ""

log "Setup started. Logging to: $SETUP_LOG"
log "Script directory: $SCRIPT_DIR"

# Create log file
touch "$SETUP_LOG"
chmod 644 "$SETUP_LOG"

# Initialize state tracking
init_state

# Show completed steps (if any)
COMPLETED_COUNT=$(count_completed_steps)
if [ "$COMPLETED_COUNT" -gt 0 ] && [ "$FORCE_MODE" != true ]; then
    echo ""
    echo -e "${BLUE}Previously completed steps:${NC}"
    list_completed_steps | while read line; do
        echo "  ✓ $line"
    done
    echo ""
fi

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
EXECUTED_STEPS=0

for step_script in "${STEPS[@]}"; do
    CURRENT_STEP=$((CURRENT_STEP + 1))
    
    # Extract step number (e.g., "04" from "04-ollama-setup.sh")
    STEP_NUM=$(echo "$step_script" | grep -o '^[0-9]\+')
    
    # Filter steps based on mode
    if [ -n "$SINGLE_STEP" ]; then
        # Single step mode: only run if matches
        if [ "$STEP_NUM" != "$SINGLE_STEP" ]; then
            continue
        fi
    elif [ -n "$FROM_STEP" ]; then
        # From-step mode: skip until we reach the specified step
        if [ "$STEP_NUM" -lt "$FROM_STEP" ]; then
            continue
        fi
    fi
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    log "Step $CURRENT_STEP/$TOTAL_STEPS: $step_script"
    echo "════════════════════════════════════════════════════════════"
    
    STEP_PATH="$SCRIPT_DIR/scripts/$step_script"
    
    if [ ! -f "$STEP_PATH" ]; then
        error "Step script not found: $STEP_PATH"
        exit 1
    fi
    
    # Make executable
    chmod +x "$STEP_PATH"
    
    # Check if step is already complete (smart mode only)
    # Skip this check if --force is used (even with --step)
    if [ "$FORCE_MODE" != true ] && is_step_complete "$step_script"; then
        SKIP_STATUS=$(get_step_status "$step_script")
        echo -e "${CYAN}✓ SKIPPED${NC} (completed at: $SKIP_STATUS)"
        echo "  Use --force to re-run, or --step $STEP_NUM to run this step only"
        continue
    fi
    
    # Prepare arguments for child script
    CHILD_ARGS=""
    if [ "$RECONFIGURE_MODE" = true ]; then
        CHILD_ARGS="--reconfigure"
    fi
    
    # Run step
    if ! "$STEP_PATH" $CHILD_ARGS; then
        error "Step $step_script failed!"
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                     SETUP FAILED                             ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Check the log file for details: $SETUP_LOG"
        echo ""
        echo "To retry this step only:"
        echo "  sudo ./setup.sh --step $STEP_NUM"
        echo ""
        echo "To rollback changes:"
        echo "  sudo systemctl stop ai-chatbot shatrox-buttons shatrox-display"
        echo "  sudo systemctl disable ai-chatbot shatrox-buttons shatrox-display"
        echo ""
        exit 1
    fi
    
    # Mark step as complete
    mark_step_complete "$step_script"
    echo -e "${GREEN}✓ COMPLETED${NC}"
    EXECUTED_STEPS=$((EXECUTED_STEPS + 1))
done

# Summary
echo ""
if [ $EXECUTED_STEPS -eq 0 ]; then
    echo -e "${CYAN}No steps were executed (all already completed or filtered out)${NC}"
    echo "Use --force to re-run all steps, or --step N to run a specific step"
    echo ""
    exit 0
fi

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

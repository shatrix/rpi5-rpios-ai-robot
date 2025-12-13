#!/bin/bash
################################################################################
# Deploy Updated Setup Scripts to RPi5
# Usage: ./deploy-to-rpi.sh <RPI_IP> [RPI_USER]
################################################################################

# Show usage
show_usage() {
    cat << EOF
Usage: ./deploy-to-rpi.sh <RPI_IP> [RPI_USER]

Arguments:
  RPI_IP        IP address of the Raspberry Pi 5 (required)
  RPI_USER      SSH username (default: root)

Examples:
  ./deploy-to-rpi.sh 192.168.2.134
  ./deploy-to-rpi.sh 192.168.2.134 pi
  ./deploy-to-rpi.sh 10.0.0.50 root

EOF
}

# Parse arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

if [ -z "$1" ]; then
    echo "❌ ERROR: IP address is required"
    echo ""
    show_usage
    exit 1
fi

RPI_IP="$1"
RPI_USER="${2:-root}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine deployment directory based on user
if [ "$RPI_USER" = "root" ]; then
    DEPLOY_DIR="/root/rpi5-rpios-ai-robot"
else
    DEPLOY_DIR="/home/$RPI_USER/rpi5-rpios-ai-robot"
fi

echo "==================================="
echo "Deploying to RPi5: $RPI_IP"
echo "User: $RPI_USER"
echo "Target: $DEPLOY_DIR"
echo "==================================="
echo ""

# Check connectivity
echo "→ Checking connectivity..."
if ! ping -c 1 -W 2 "$RPI_IP" &> /dev/null; then
    echo "❌ ERROR: Cannot reach RPi5 at $RPI_IP"
    exit 1
fi
echo "✓ RPi5 is reachable"
echo ""

# Deploy updated scripts
echo "→ Deploying project files to RPi5..."

# Use rsync to copy entire project structure (excluding git and tmp files)
rsync -av --delete \
    --exclude '.git' \
    --exclude '.gitignore' \
    --exclude '*.swp' \
    --exclude '*~' \
    --exclude 'deploy-to-rpi.sh' \
    "$PROJECT_DIR/" "$RPI_USER@$RPI_IP:$DEPLOY_DIR/"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Deployment failed"
    exit 1
fi

# Make all scripts executable
echo ""
echo "→ Setting permissions..."
ssh "$RPI_USER@$RPI_IP" "cd $DEPLOY_DIR && \
    chmod +x setup.sh && \
    chmod +x scripts/*.sh && \
    chmod +x scripts/lib/*.sh 2>/dev/null || true && \
    chmod +x scripts-helpers/* 2>/dev/null || true && \
    chmod +x qml/shatrox-display-start 2>/dev/null || true && \
    chmod +x qml/shatrox-touch-monitor 2>/dev/null || true && \
    chmod +x qml/shatrox-volume-monitor 2>/dev/null || true && \
    chmod +x python/*.py 2>/dev/null || true"

echo ""
echo "✓ Deployment complete!"
echo ""
echo "==================================="
echo "Next Steps on RPi5:"
echo "==================================="
echo ""
echo "1. SSH into RPi5:"
echo "   ssh $RPI_USER@$RPI_IP"
echo ""
echo "2. Navigate to project:"
echo "   cd $DEPLOY_DIR"
echo ""
echo "3. Test help message:"
echo "   ./setup.sh --help"
echo ""
if [ "$RPI_USER" != "root" ]; then
    echo "4. Run setup (requires sudo):"
    echo "   sudo ./setup.sh"
else
    echo "4. Test smart mode (should skip completed steps):"
    echo "   ./setup.sh"
fi
echo ""
echo "5. Test selective execution:"
echo "   ./setup.sh --step 04"
echo ""
echo "6. Test reconfiguration:"
echo "   ./setup.sh --reconfigure"
echo ""

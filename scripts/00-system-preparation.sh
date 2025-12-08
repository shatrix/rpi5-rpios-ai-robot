#!/bin/bash
################################################################################
# 00: System Preparation
# - Update system packages
# - Expand filesystem to use all available storage
# - Verify hardware
################################################################################

set -e

echo "=== System Preparation ==="

echo "→ Updating system packages..."
apt update
apt upgrade -y

# NOTE: Filesystem expansion skipped - not needed for NVMe/properly sized storage
# The raspi-config expansion fails on already-mounted filesystems
# Your 470GB NVMe is already fully expanded
echo "→ Filesystem expansion skipped (not needed for NVMe)"

# 3. Check available storage
echo "→ Checking storage..."
AVAILABLE_GB=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
TOTAL_GB=$(df -BG / | tail -1 | awk '{print $2}' | sed 's/G//')

echo "   Total storage: ${TOTAL_GB}GB"
echo "   Available: ${AVAILABLE_GB}GB"

MIN_REQUIRED_GB=6
if [ "$AVAILABLE_GB" -lt "$MIN_REQUIRED_GB" ]; then
    echo "⚠️  WARNING: Only ${AVAILABLE_GB}GB available."
    echo "   Minimum required: ${MIN_REQUIRED_GB}GB for AI models"
    echo "   Installation may fail due to insufficient storage!"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✓ Storage check passed: ${AVAILABLE_GB}GB available"

# 4. Verify RPi 5 hardware
echo "→ Verifying Raspberry Pi 5 hardware..."
CPU_MODEL=$(cat /proc/cpuinfo | grep "Model" | head -1 | cut -d: -f2 | xargs)

if [[ ! "$CPU_MODEL" =~ "Raspberry Pi 5" ]]; then
    echo "⚠️  WARNING: Not running on Raspberry Pi 5!"
    echo "   Detected: $CPU_MODEL"
    echo "   This setup is optimized for RPi 5. Some features may not work correctly."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Raspberry Pi 5 detected: $CPU_MODEL"
fi

# 5. Check RAM
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
echo "   Total RAM: ${TOTAL_RAM_MB}MB"

if [ "$TOTAL_RAM_MB" -lt 3800 ]; then
    echo "⚠️  WARNING: Less than 4GB RAM detected (${TOTAL_RAM_MB}MB)"
    echo "   AI models may run slowly or fail due to memory constraints."
fi

# 6. Verify 64-bit OS
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "❌ ERROR: 64-bit ARM OS required!"
    echo "   Detected: $ARCH"
    echo "   Please install Raspberry Pi OS (64-bit)"
    exit 1
fi

echo "✓ 64-bit ARM OS confirmed: $ARCH"

# 7. Check Debian version
DEBIAN_VERSION=$(cat /etc/debian_version | cut -d. -f1)
echo "   Debian version: $DEBIAN_VERSION"

if [ "$DEBIAN_VERSION" -lt 12 ]; then
    echo "⚠️  WARNING: Debian $DEBIAN_VERSION detected. Recommended: Debian 13 (Bookworm)"
fi

echo ""
echo "✓ System preparation complete"
echo ""
echo "  Storage: ${TOTAL_GB}GB total, ${AVAILABLE_GB}GB available"
echo "  RAM: ${TOTAL_RAM_MB}MB"
echo "  Hardware: $CPU_MODEL"
echo "  Architecture: $ARCH"
echo "  Debian: $DEBIAN_VERSION"
echo ""

# Note: Filesystem expansion requires reboot, but we'll do that at the very end exit 0

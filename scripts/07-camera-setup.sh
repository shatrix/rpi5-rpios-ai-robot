#!/bin/bash
################################################################################
# 07: Camera Setup
# Verify libcamera and test camera
################################################################################

set -e

echo "=== Configuring Camera ==="

# Check for rpicam-still (new command in Debian Trixie/Bookworm)
# Falls back to libcamera-still for older versions
if command -v rpicam-still &> /dev/null; then
    CAMERA_CMD="rpicam-still"
    echo "✓ rpicam-still found (Raspberry Pi OS Trixie/Bookworm)"
elif command -v libcamera-still &> /dev/null; then
    CAMERA_CMD="libcamera-still"
    echo "✓ libcamera-still found (older Raspberry Pi OS)"
else
    echo "⚠️  WARNING: Neither rpicam-still nor libcamera-still found!"
    echo "   Camera functionality will not work."
    echo "   Install with: sudo apt install rpicam-apps"
    echo ""
    echo "   Continuing setup without camera support..."
    
    # Create camera directories anyway
    mkdir -p /tmp/ai-camera
    chmod 777 /tmp/ai-camera
    
    echo "✓ Camera setup completed (camera optional)"
    exit 0
fi

# Test camera (optional, may fail if camera not connected)
echo "→ Testing camera..."
if $CAMERA_CMD -o /tmp/camera-test.jpg --nopreview -t 1000 > /dev/null 2>&1; then
    echo "✓ Camera test successful"
    rm /tmp/camera-test.jpg
else
    echo "⚠️  WARNING: Camera test failed!"
    echo "   This is expected if the camera is not yet connected."
    echo "   Make sure to connect the Camera Module 3 before use."
    echo "   Camera functionality will work after connecting and rebooting."
fi

# Create camera directories
mkdir -p /tmp/ai-camera
chmod 777 /tmp/ai-camera

echo "✓ Camera directories created"

echo ""
echo "  Camera configuration complete"
echo "  Test manually: libcamera-still -o test.jpg --nopreview"
echo ""

exit 0

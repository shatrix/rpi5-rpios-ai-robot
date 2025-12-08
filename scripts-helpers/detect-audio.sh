#!/bin/bash
################################################################################
# detect-audio.sh - Detect USB Audio device and return ALSA device string
################################################################################

# Try to find USB Audio device
USB_CARD=$(aplay -l | grep -i "USB Audio" | head -n 1 | sed -n 's/card \([0-9]\+\):.*/\1/p')

if [ -n "$USB_CARD" ]; then
    echo "plughw:${USB_CARD},0"
    exit 0
fi

# Fallback to first available card
FIRST_CARD=$(aplay -l | head -n 2 | tail -n 1 | sed -n 's/card \([0-9]\+\):.*/\1/p')
if [ -n "$FIRST_CARD" ]; then
    echo "plughw:${FIRST_CARD},0"
    exit 0
fi

# Last resort
echo "default"
exit 1

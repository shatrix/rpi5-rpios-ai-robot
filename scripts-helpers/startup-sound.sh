#!/bin/bash
# Startup sound/greeting service
# Plays a greeting message after system boot

# Wait for audio to be ready
sleep 3

# Set speaker volume to 65%
amixer -c 0 set Speaker 65% 2>/dev/null || amixer set Master 65% 2>/dev/null

# Wait for Piper TTS to be available
for i in {1..10}; do
    if command -v piper &> /dev/null; then
        break
    fi
    sleep 1
done

# Play boot greeting
/usr/local/bin/speak "Hi, boot sequence complete, system online"

exit 0

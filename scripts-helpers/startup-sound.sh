#!/bin/bash
# Startup sound/greeting service
# Plays a greeting message after system boot
# Language-aware greeting

# Wait for audio to be ready
sleep 3

# Wait for Piper TTS to be available
for i in {1..10}; do
    if command -v piper &> /dev/null; then
        break
    fi
    sleep 1
done

# Load language configuration
if [ -f "/etc/ai-chatbot/language.conf" ]; then
    LANG=$(grep "^LANGUAGE=" /etc/ai-chatbot/language.conf | cut -d= -f2)
else
    LANG="en"
fi

# Play language-appropriate boot greeting
if [ "$LANG" = "ar" ]; then
    /usr/local/bin/speak "النظام جاهز، تم تشغيل الروبوت بنجاح"
else
    /usr/local/bin/speak "Hi, boot sequence complete, system online"
fi

exit 0

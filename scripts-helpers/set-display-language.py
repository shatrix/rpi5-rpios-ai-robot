import sys
import os

# Load language config
LANGUAGE = 'en'
lang_file = '/etc/ai-chatbot/language.conf'
if os.path.exists(lang_file):
    try:
        with open(lang_file, 'r') as f:
            for line in f:
                if line.startswith('LANGUAGE='):
                    LANGUAGE = line.split('=')[1].strip()
                    break
    except Exception:
        pass

# Bilingual startup messages
STARTUP_MESSAGES = {
    'en': "╔════════════════════════════╗\n║  SHATROX AI Robot Ready  ║\n╚════════════════════════════╝\n\nPress K1 to talk\nPress K3 for camera",
    'ar': "╔═══════════════════════════════╗\n║  روبوت SHATROX الذكي جاهز  ║\n╚═══════════════════════════════╝\n\nاضغط K1 للتحدث\nاضغط K3 للكاميرا"
}

# Write appropriate message based on language
message = STARTUP_MESSAGES.get(LANGUAGE, STARTUP_MESSAGES['en'])
with open('/tmp/ai-qa-display.txt', 'w') as f:
    f.write(message)

print(f"Startup message set for language: {LANGUAGE}")

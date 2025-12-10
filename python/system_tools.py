#!/usr/bin/env python3
"""
System Tools for AI Chatbot
Defines functions that the AI can call to control the system
Supports bilingual operation (English and Arabic)
"""

import subprocess
import datetime
import json
import re
import os

# Load language configuration
LANGUAGE = 'en'  # Default to English
LANG_CONFIG_FILE = '/etc/ai-chatbot/language.conf'
if os.path.exists(LANG_CONFIG_FILE):
    try:
        with open(LANG_CONFIG_FILE, 'r') as f:
            for line in f:
                if line.startswith('LANGUAGE='):
                    LANGUAGE = line.split('=')[1].strip()
                    break
    except Exception:
        pass  # Keep default

# Bilingual response strings
STRINGS = {
    'en': {
        'volume_set': "Volume set to {percent}%",
        'volume_error': "Failed to set volume: {error}",
        'time': "The current time is {time_str}",
        'date': "Today is {date_str}",
        'shutdown': "System is shutting down in 3 2 1",
        'shutdown_msg': "Shutting down system",
        'camera_triggered': "camera_capture_triggered"
    },
    'ar': {
        'volume_set': "تم ضبط الصوت إلى {percent}%",
        'volume_error': "فشل ضبط الصوت: {error}",
        'time': "الوقت الحالي هو {time_str}",
        'date': "اليوم هو {date_str}",
        'shutdown': "إيقاف تشغيل النظام في ٣ ٢ ١",
        'shutdown_msg': "إيقاف تشغيل النظام",
        'camera_triggered': "camera_capture_triggered"
    }
}

def get_string(key, **kwargs):
    """Get localized string with formatting"""
    template = STRINGS.get(LANGUAGE, STRINGS['en']).get(key, '')
    return template.format(**kwargs) if kwargs else template


def detect_command_category(text):
    """
    STAGE 1: Detect if user input is a command CATEGORY (loose matching).
    Returns command category name or None.
    
    Supports BILINGUAL detection (English and Arabic).
    This uses loose patterns - just detects the command type, not details.
    AI will parse the actual values in Stage 2.
    """
    text_lower = text.lower().strip()
    
    # VOLUME CONTROL - English + Arabic
    # English: "set volume", "change volume", "adjust volume"
    # Arabic: "اضبط الصوت", "غير الصوت", "عدل الصوت"
    if re.search(r'(?:set|change|adjust|make|turn|increase|decrease|raise|lower)\s+(?:the\s+)?volume', text_lower):
        return 'VOLUME_COMMAND'
    if re.search(r'(?:اضبط|غير|عدل|ارفع|اخفض|زود|قلل)\s+(?:ال)?صوت', text_lower):
        return 'VOLUME_COMMAND'
    
    # TIME QUERY - English + Arabic
    # English: "what time", "tell me time"
    # Arabic: "ما الوقت", "كم الساعة", "أخبرني الوقت"
    if re.search(r'(?:what|tell).*time|time.*(?:is\s+it)', text_lower):
        return 'TIME_COMMAND'
    if re.search(r'(?:ما|كم|أخبرني)\s+.*(?:الوقت|الساعة)|(?:الوقت|الساعة).*(?:الآن|حالياً)', text_lower):
        return 'TIME_COMMAND'
    
    # DATE QUERY - English + Arabic
    # English: "what date", "what day"
    # Arabic: "ما التاريخ", "ما اليوم"
    if re.search(r'(?:what|tell).*(?:date|day)|(?:date|day).*(?:is\s+it|today)', text_lower):
        return 'DATE_COMMAND'
    if re.search(r'(?:ما|كم|أخبرني)\s+.*(?:التاريخ|اليوم)', text_lower):
        return 'DATE_COMMAND'
    
    # CAMERA/PICTURE - English + Arabic
    # English: "take picture", "use camera"
    # Arabic: "التقط صورة", "خذ صورة"
    if re.search(r'(?:take|capture|use)\s+(?:a\s+)?(?:picture|photo|image|camera)|(?:what.*see|describe.*see)', text_lower):
        return 'CAMERA_COMMAND'
    if re.search(r'(?:التقط|خذ|صور)\s+(?:صورة|لقطة)', text_lower):
        return 'CAMERA_COMMAND'
    
    # SHUTDOWN - English + Arabic
    # English: "shut down", "power off"
    # Arabic: "أطفئ", "أغلق", "أوقف التشغيل"
    if re.search(r'(?:shut\s*down|power\s+off|turn\s+off)(?:\s+(?:system|robot))?', text_lower):
        return 'SHUTDOWN_COMMAND'
    if re.search(r'(?:أطفئ|أغلق|أوقف)\s+(?:النظام|الجهاز|التشغيل)?', text_lower):
        return 'SHUTDOWN_COMMAND'
    
    return None


def set_volume(percent):
    """Set speaker volume to specified percentage (0-100)"""
    try:
        # Clamp to valid range
        percent = max(0, min(100, int(percent)))
        
        # Use 'Speaker' control (not PCM) for this hardware
        result = subprocess.run(
            ['amixer', 'set', 'Speaker', f'{percent}%'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            return get_string('volume_set', percent=percent)
        else:
            return get_string('volume_error', error=result.stderr)
    except Exception as e:
        return get_string('volume_error', error=str(e))


def take_picture():
    """Trigger camera capture and image description"""
    try:
        # This will be handled by the existing CAMERA_CAPTURE command
        # which already has full implementation in ai-chatbot.py
        return get_string('camera_triggered')
    except Exception as e:
        return f"Error triggering camera: {str(e)}"


def get_current_time():
    """Get current time"""
    try:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
        return get_string('time', time_str=time_str)
    except Exception as e:
        return f"Error getting time: {str(e)}"


def get_current_date():
    """Get current date"""
    try:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Wednesday, December 10, 2025"
        return get_string('date', date_str=date_str)
    except Exception as e:
        return f"Error getting date: {str(e)}"


def shutdown_system():
    """Shutdown the system safely"""
    try:
        # Similar to K8 button implementation
        # First speak the warning (language-aware via 'speak' wrapper)
        subprocess.run(['speak', get_string('shutdown')], timeout=10)
        
        # Then actually shutdown
        subprocess.run(['shutdown', '-h', 'now'])
        
        return get_string('shutdown_msg')
    except Exception as e:
        return f"Error shutting down: {str(e)}"


# Map of function names to actual functions
TOOL_FUNCTIONS = {
    'set_volume': set_volume,
    'take_picture': take_picture,
    'get_current_time': get_current_time,
    'get_current_date': get_current_date,
    'shutdown_system': shutdown_system,
}


# Tool definitions for Ollama (OpenAI-compatible format)
TOOL_DEFINITIONS = [
    {
        'type': 'function',
        'function': {
            'name': 'set_volume',
            'description': 'Set the speaker volume to a specific percentage between 0 and 100',
            'parameters': {
                'type': 'object',
                'properties': {
                    'percent': {
                        'type': 'integer',
                        'description': 'Volume level from 0 (mute) to 100 (maximum)',
                    },
                },
                'required': ['percent'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'take_picture',
            'description': 'Take a picture with the camera and describe what you see in the image',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_current_time',
            'description': 'Get the current time',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_current_date',
            'description': 'Get the current date (day, month, year)',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'shutdown_system',
            'description': 'Safely shutdown the robot system. ONLY use this when explicitly asked to shutdown or turn off.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
]


def execute_tool(function_name, arguments):
    """Execute a tool function by name with given arguments"""
    if function_name not in TOOL_FUNCTIONS:
        return f"Unknown function: {function_name}"
    
    func = TOOL_FUNCTIONS[function_name]
    
    try:
        # Get function signature to know which parameters it actually accepts
        import inspect
        sig = inspect.signature(func)
        valid_param_names = set(sig.parameters.keys())
        
        # Filter arguments to only include valid parameters for this function
        if isinstance(arguments, dict):
            clean_args = {k: v for k, v in arguments.items() if k in valid_param_names}
        else:
            clean_args = {}
        
        # Call function with cleaned arguments
        if clean_args:
            result = func(**clean_args)
        else:
            result = func()
        
        return result
    except Exception as e:
        import traceback
        return f"Error executing {function_name}: {str(e)}"


if __name__ == "__main__":
    # Test the tools
    print("Testing system tools...")
    print("\n1. Get time:", get_current_time())
    print("2. Get date:", get_current_date())
    print("3. Set volume to 50%:", set_volume(50))
    print("4. Take picture:", take_picture())

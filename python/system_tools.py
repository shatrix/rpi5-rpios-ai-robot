#!/usr/bin/env python3
"""
System Tools for AI Chatbot
Defines functions that the AI can call to control the system
"""

import subprocess
import datetime
import json
import re


def detect_command_category(text):
    """
    STAGE 1: Detect if user input is a command CATEGORY (loose matching).
    Returns command category name or None.
    
    This uses loose patterns - just detects the command type, not details.
    AI will parse the actual values in Stage 2.
    """
    text_lower = text.lower().strip()
    
    # Volume control - needs action word + "volume"
    # Examples: "set volume", "change volume", "adjust volume", "make volume"
    if re.search(r'(?:set|change|adjust|make|turn|increase|decrease|raise|lower)\s+(?:the\s+)?volume', text_lower):
        return 'VOLUME_COMMAND'
    
    # Time query - "time" with question words
    # Examples: "what time", "tell me time", "what's the time"
    if re.search(r'(?:what|tell).*time|time.*(?:is\s+it)', text_lower):
        return 'TIME_COMMAND'
    
    # Date query - "date" or "day" with question words
    # Examples: "what date", "what day", "tell me the date"
    if re.search(r'(?:what|tell).*(?:date|day)|(?:date|day).*(?:is\s+it|today)', text_lower):
        return 'DATE_COMMAND'
    
    # Camera/picture - action word + picture/camera/see
    # Examples: "take picture", "use camera", "what do you see"
    if re.search(r'(?:take|capture|use)\s+(?:a\s+)?(?:picture|photo|image|camera)|(?:what.*see|describe.*see)', text_lower):
        return 'CAMERA_COMMAND'
    
    # Shutdown - explicit shutdown/power off commands
    # Examples: "shut down", "power off", "turn off system"
    if re.search(r'(?:shut\s*down|power\s+off|turn\s+off)(?:\s+(?:system|robot))?', text_lower):
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
            return f"Volume set to {percent}%"
        else:
            return f"Failed to set volume: {result.stderr}"
    except Exception as e:
        return f"Error setting volume: {str(e)}"


def take_picture():
    """Trigger camera capture and image description"""
    try:
        # This will be handled by the existing CAMERA_CAPTURE command
        # which already has full implementation in ai-chatbot.py
        return "camera_capture_triggered"
    except Exception as e:
        return f"Error triggering camera: {str(e)}"


def get_current_time():
    """Get current time"""
    try:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
        return f"The current time is {time_str}"
    except Exception as e:
        return f"Error getting time: {str(e)}"


def get_current_date():
    """Get current date"""
    try:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Wednesday, December 10, 2025"
        return f"Today is {date_str}"
    except Exception as e:
        return f"Error getting date: {str(e)}"


def shutdown_system():
    """Shutdown the system safely"""
    try:
        # Similar to K8 button implementation
        # First speak the warning
        subprocess.run(['speak', 'System is shutting down in 3 2 1'], timeout=10)
        
        # Then actually shutdown
        subprocess.run(['shutdown', '-h', 'now'])
        
        return "Shutting down system"
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

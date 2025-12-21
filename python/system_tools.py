#!/usr/bin/env python3
"""
System Tools for AI Chatbot
Defines functions that the AI can call to control the system
"""

import subprocess
import datetime
import json
import re
import socket
import os

# Motor control socket path
MOTOR_SOCKET = "/tmp/shatrox-motor-control.sock"


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
    
    # MOTOR STOP - check this BEFORE shutdown to prevent "stop" from matching "shut down"
    # Examples: "stop", "halt", "freeze", "stop moving"
    # Must NOT match "stop system" which could be shutdown intent
    if re.search(r'^stop$|^halt$|^freeze$|stop\s+(?:moving|motors?|driving|it)|(?:motors?|robot)\s+stop', text_lower):
        return 'MOTOR_STOP'
    
    # Shutdown - explicit shutdown/power off commands (must include "shutdown", "power off", or "turn off")
    # Examples: "shut down", "power off", "turn off system"
    if re.search(r'shut\s*down|power\s+off|turn\s+off\s+(?:the\s+)?(?:system|robot|everything)', text_lower):
        return 'SHUTDOWN_COMMAND'
    
    # ==========================================================================
    # MOTOR CONTROL COMMANDS
    # ==========================================================================
    
    # Move forward - "go forward", "move forward", "drive forward", "forward"
    if re.search(r'(?:go|move|drive|walk|run)\s+forward|^forward$|move\s+ahead|go\s+ahead', text_lower):
        return 'MOTOR_FORWARD'
    
    # Move backward - "go back", "move backward", "reverse", "back up"
    if re.search(r'(?:go|move|drive)\s+(?:back(?:ward)?s?)|reverse|back\s*up', text_lower):
        return 'MOTOR_BACKWARD'
    
    # Turn left - "turn left", "go left", "rotate left"
    if re.search(r'(?:turn|go|rotate|spin)\s+left|left\s+turn', text_lower):
        return 'MOTOR_LEFT'
    
    # Turn right - "turn right", "go right", "rotate right"
    if re.search(r'(?:turn|go|rotate|spin)\s+right|right\s+turn', text_lower):
        return 'MOTOR_RIGHT'
    
    # (MOTOR_STOP is checked earlier, before SHUTDOWN_COMMAND)
    
    # Explore mode - "explore", "start exploring", "roam around", "wander"
    if re.search(r'explore|start\s+explor|roam(?:\s+around)?|wander|autonomous|auto\s*pilot', text_lower):
        return 'MOTOR_EXPLORE'
    
    # Distance query - "how far", "what's the distance", "check distance"
    if re.search(r'(?:how\s+far|what.*distance|check\s+distance|measure\s+distance|obstacle.*distance|distance.*obstacle)', text_lower):
        return 'DISTANCE_QUERY'
    
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


# =============================================================================
# MOTOR CONTROL FUNCTIONS
# =============================================================================

def _send_motor_command(command_dict):
    """
    Send a JSON command to the motor controller via Unix socket.
    Returns response dict or error message.
    """
    if not os.path.exists(MOTOR_SOCKET):
        return {"status": "error", "message": "Motor controller not running"}
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        sock.connect(MOTOR_SOCKET)
        sock.sendall(json.dumps(command_dict).encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        sock.close()
        return json.loads(response)
    except socket.timeout:
        return {"status": "error", "message": "Motor controller timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def motor_forward(speed=50, duration=2):
    """Move the robot forward"""
    try:
        speed = max(0, min(100, int(speed)))
        duration = max(0, float(duration))
        
        response = _send_motor_command({
            "action": "move_forward",
            "speed": speed,
            "duration": duration
        })
        
        if response.get("status") == "ok":
            if duration > 0:
                return f"Moving forward at {speed}% speed for {duration} seconds"
            else:
                return f"Moving forward at {speed}% speed"
        elif response.get("status") == "blocked":
            return "Cannot move forward - obstacle detected"
        else:
            return f"Motor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error moving forward: {str(e)}"


def motor_backward(speed=50, duration=2):
    """Move the robot backward"""
    try:
        speed = max(0, min(100, int(speed)))
        duration = max(0, float(duration))
        
        response = _send_motor_command({
            "action": "move_backward",
            "speed": speed,
            "duration": duration
        })
        
        if response.get("status") == "ok":
            if duration > 0:
                return f"Moving backward at {speed}% speed for {duration} seconds"
            else:
                return f"Moving backward at {speed}% speed"
        else:
            return f"Motor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error moving backward: {str(e)}"


def motor_left(speed=50, angle=90):
    """Turn the robot left"""
    try:
        speed = max(0, min(100, int(speed)))
        angle = max(0, min(360, float(angle)))
        
        response = _send_motor_command({
            "action": "turn_left",
            "speed": speed,
            "angle": angle
        })
        
        if response.get("status") == "ok":
            return f"Turning left {angle} degrees"
        else:
            return f"Motor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error turning left: {str(e)}"


def motor_right(speed=50, angle=90):
    """Turn the robot right"""
    try:
        speed = max(0, min(100, int(speed)))
        angle = max(0, min(360, float(angle)))
        
        response = _send_motor_command({
            "action": "turn_right",
            "speed": speed,
            "angle": angle
        })
        
        if response.get("status") == "ok":
            return f"Turning right {angle} degrees"
        else:
            return f"Motor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error turning right: {str(e)}"


def motor_stop():
    """Stop all motor movement immediately"""
    try:
        response = _send_motor_command({"action": "stop"})
        
        if response.get("status") == "ok":
            return "Motors stopped"
        else:
            return f"Motor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error stopping motors: {str(e)}"


def motor_explore():
    """
    Start autonomous exploration mode.
    The robot will move forward continuously, automatically avoiding obstacles
    by backing up and turning when obstacles are detected.
    Say 'stop' to end exploration.
    """
    try:
        # Use the explore_start command which handles everything:
        # - Sets obstacle behavior to backup_and_turn
        # - Enables explore_mode flag for auto-resume after avoidance
        # - Starts continuous forward movement
        response = _send_motor_command({"action": "explore_start"})
        
        if response.get("status") == "ok":
            return "Exploration mode started! I will move around and avoid obstacles automatically. Say 'stop' when you want me to stop exploring."
        elif response.get("status") == "blocked":
            return "Cannot start exploring - obstacle in the way. Please clear the path and try again."
        else:
            return f"Failed to start exploration: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error starting exploration: {str(e)}"


def get_distance():
    """Get the distance reading from the ultrasonic sensor"""
    try:
        response = _send_motor_command({"action": "get_distance"})
        
        if response.get("status") == "ok":
            distance = response.get("distance_cm", 0)
            if distance >= 400:  # Max sensor range
                return "No obstacle detected - path is clear"
            elif distance < 20:
                return f"Warning! Obstacle very close at {distance:.1f} centimeters"
            else:
                return f"Distance to nearest obstacle is {distance:.1f} centimeters"
        else:
            return f"Sensor error: {response.get('message', 'unknown')}"
    except Exception as e:
        return f"Error reading distance: {str(e)}"


# Map of function names to actual functions
TOOL_FUNCTIONS = {
    'set_volume': set_volume,
    'take_picture': take_picture,
    'get_current_time': get_current_time,
    'get_current_date': get_current_date,
    'shutdown_system': shutdown_system,
    # Motor control functions
    'motor_forward': motor_forward,
    'motor_backward': motor_backward,
    'motor_left': motor_left,
    'motor_right': motor_right,
    'motor_stop': motor_stop,
    'motor_explore': motor_explore,
    'get_distance': get_distance,
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
    # ==========================================================================
    # MOTOR CONTROL TOOL DEFINITIONS
    # ==========================================================================
    {
        'type': 'function',
        'function': {
            'name': 'motor_forward',
            'description': 'Move the robot forward. Use this when asked to go forward, move ahead, or drive forward.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'speed': {
                        'type': 'integer',
                        'description': 'Speed percentage from 0 to 100 (default: 50)',
                    },
                    'duration': {
                        'type': 'number',
                        'description': 'How many seconds to move (default: 2). Use 0 for continuous movement.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'motor_backward',
            'description': 'Move the robot backward. Use this when asked to go back, reverse, or move backward.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'speed': {
                        'type': 'integer',
                        'description': 'Speed percentage from 0 to 100 (default: 50)',
                    },
                    'duration': {
                        'type': 'number',
                        'description': 'How many seconds to move (default: 2)',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'motor_left',
            'description': 'Turn the robot left. Use this when asked to turn left, go left, or rotate left.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'speed': {
                        'type': 'integer',
                        'description': 'Speed percentage from 0 to 100 (default: 50)',
                    },
                    'angle': {
                        'type': 'number',
                        'description': 'Degrees to turn (default: 90)',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'motor_right',
            'description': 'Turn the robot right. Use this when asked to turn right, go right, or rotate right.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'speed': {
                        'type': 'integer',
                        'description': 'Speed percentage from 0 to 100 (default: 50)',
                    },
                    'angle': {
                        'type': 'number',
                        'description': 'Degrees to turn (default: 90)',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'motor_stop',
            'description': 'Stop all motor movement immediately. Use this when asked to stop, halt, or freeze.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'motor_explore',
            'description': 'Start autonomous exploration mode. The robot will move continuously, automatically avoiding obstacles by backing up and turning. It will keep exploring until told to stop.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_distance',
            'description': 'Get the distance reading from the ultrasonic sensor. Use this when asked about distance to obstacles or how far something is.',
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
    print("\n=== Basic System Tools ===")
    print("1. Get time:", get_current_time())
    print("2. Get date:", get_current_date())
    print("3. Set volume to 50%:", set_volume(50))
    print("4. Take picture:", take_picture())
    
    print("\n=== Motor Command Category Detection ===")
    test_phrases = [
        "go forward",
        "move backward",
        "turn left",
        "go right",
        "stop",
        "explore",
        "how far is the obstacle",
        "set volume to 70",
        "what time is it",
    ]
    for phrase in test_phrases:
        category = detect_command_category(phrase)
        print(f"  '{phrase}' -> {category}")
    
    print("\n=== Motor Control (requires motor service) ===")
    print("5. Get distance:", get_distance())
    # Uncomment to test actual motor movement:
    # print("6. Motor forward:", motor_forward(speed=30, duration=1))
    # print("7. Motor stop:", motor_stop())


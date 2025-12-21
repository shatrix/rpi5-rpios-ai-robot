#!/usr/bin/env python3
"""
SHATROX Button Monitor Service
Monitors 8 GPIO buttons and triggers LLM queries with TTS responses
"""

import gpiod
from gpiod.line import Direction, Bias, Edge
from gpiod import EdgeEvent
import time
import subprocess
import sys
import os
import threading
import socket

# ---------------------------------------------------------
# Updated GPIO mapping from user
# ---------------------------------------------------------
# Button to GPIO mapping
BUTTON_MAP = {
    5:  "K1",
    6:  "K2",
    13: "K3",
    19: "K4",
    26: "K8"
}

# Button to question mapping (K1, K2, K4, K8 use special actions)
# Button to question mapping (K1, K2, K4, K8 use special actions)
BUTTON_QUESTIONS = {
    "K1": "Voice Chat (Hold to Speak)",
    "K2": None,
    "K3": "Camera Vision",
    "K4": None,  # Fun sound button
    "K8": None,
}

INPUT_PINS = list(BUTTON_MAP.keys())
CHIP_PATH = "/dev/gpiochip4"  # RPi 5 on Raspberry Pi OS uses gpiochip4
DEBOUNCE_MS = 50  # 50ms is sufficient for mechanical bounce, 200ms is too long for quick clicks
DISPLAY_LOG = "/tmp/shatrox-display.log"
AI_CHATBOT_SOCKET = "/tmp/ai-chatbot.sock"

last_press_time = {}
k1_is_recording = False
k1_recording_start_time = None  # RELIABILITY FIX: Track when K1 recording started
K1_RECORDING_TIMEOUT = 15  # Seconds - force stop if stuck

# Track which buttons have active threads running
# Only track K1 (long-running LLM task)
# K2/K3/K4 are fire-and-forget TTS, K8 is shutdown
active_threads = {
    "K1": False,
}


def display_print(msg, end='\n'):
    """Print to stdout and to QML display log"""
    print(msg, end=end, flush=True)
    try:
        with open(DISPLAY_LOG, 'a') as f:
            f.write(msg + end)
            f.flush()
    except Exception as e:
        print(f"Warning: Could not write to display log: {e}", file=sys.stderr)


def send_ai_command(command):
    """Send command to AI chatbot socket"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(AI_CHATBOT_SOCKET)
        sock.sendall(command.encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        sock.close()
        return response
    except Exception as e:
        display_print(f"[AI] Error communicating with chatbot: {e}")
        return None



def _handle_button_press_impl(button_name, event_type):
    """Implementation of button press handling (runs in thread)"""
    global k1_is_recording, k1_recording_start_time
    
    try:
        # ----------------------------------------------
        # K1: VOICE CHAT (HOLD TO TALK)
        # ----------------------------------------------
        if button_name == "K1":
            if event_type == EdgeEvent.Type.FALLING_EDGE: # Press
                # RELIABILITY FIX: Check for stuck recording (timeout recovery)
                if k1_is_recording and k1_recording_start_time:
                    elapsed = time.time() - k1_recording_start_time
                    if elapsed > K1_RECORDING_TIMEOUT:
                        display_print(f"[K1] Recording timeout ({elapsed:.1f}s) - forcing stop")
                        send_ai_command("STOP_RECORDING")
                        k1_is_recording = False
                        k1_recording_start_time = None
                
                if not k1_is_recording:
                    # Start recording
                    display_print("[K1] Starting voice recording (hold to speak)...")
                    send_ai_command("START_RECORDING")
                    k1_is_recording = True
                    k1_recording_start_time = time.time()  # Track start time
                else:
                    # TOGGLE FALLBACK: If already recording, stop it
                    # This handles cases where release event wasn't detected
                    display_print("[K1] Stopping recording (toggle fallback)...")
                    send_ai_command("STOP_RECORDING")
                    k1_is_recording = False
                    k1_recording_start_time = None
            
            elif event_type == EdgeEvent.Type.RISING_EDGE: # Release
                if k1_is_recording:
                    display_print("[K1] Stopping voice recording...")
                    send_ai_command("STOP_RECORDING")
                    k1_is_recording = False
                    k1_recording_start_time = None
            return

        # ----------------------------------------------
        # IGNORE RELEASE EVENTS FOR OTHER BUTTONS
        # ----------------------------------------------
        if event_type == EdgeEvent.Type.RISING_EDGE: # Release
            return

        # ----------------------------------------------
        # K3: CAMERA VISION (PRESS)
        # ----------------------------------------------
        if button_name == "K3":
            display_print("[K3] Camera vision - capturing image...")
            send_ai_command("CAMERA_CAPTURE")
            return

        # ----------------------------------------------
        # K8: SHUTDOWN
        # ----------------------------------------------
        if button_name == "K8":
            display_print("[K8] System shutdown initiated...")
            subprocess.Popen([
                "speak",
                "System is shutting down in 3 2 1  "
            ]).wait()  # Wait for TTS to complete
            display_print("[K8] Shutting down now...")
            subprocess.run(["shutdown", "-h", "now"])
            return

        # ----------------------------------------------
        # K4: FUN SOUND
        # ----------------------------------------------
        if button_name == "K4":
            display_print("[K4] Playing fun sound...")
            subprocess.Popen([
                "speak",
                "zoozoo haii yaii yaii"
            ])
            return

        # ----------------------------------------------
        # K2: GREETING
        # ----------------------------------------------
        if button_name == "K2":
            display_print("[K2] Speaking greeting message...")
            subprocess.Popen([
                "speak",
                "Hi, I'm Jarvis — an AI-powered robot here to answer your questions"
            ])
            return

    finally:
        # Always mark button as inactive when thread completes
        if button_name in active_threads:
            active_threads[button_name] = False


def handle_button_press(button_name, event_type):
    """Handle a button press event by launching it in a separate thread"""
    
    # Mark this button as active (before starting thread)
    if button_name in active_threads:
        active_threads[button_name] = True
    
    # Run the button handler in a daemon thread so main loop stays responsive
    thread = threading.Thread(
        target=_handle_button_press_impl,
        args=(button_name, event_type),
        daemon=True,
        name=f"Button-{button_name}"
    )
    thread.start()


def run():
    """Main service loop"""

    line_settings = gpiod.LineSettings(
        direction=Direction.INPUT,
        bias=Bias.PULL_UP,
        edge_detection=Edge.BOTH
    )

    try:
        with gpiod.request_lines(
            CHIP_PATH,
            consumer="shatrox-buttons",
            config={tuple(INPUT_PINS): line_settings}
        ) as request:

            display_print("╔═══════════════════════════════════════════════════════════╗")
            display_print("║        SHATROX Button Service Active                      ║")
            display_print(f"║        Monitoring: {', '.join(BUTTON_MAP.values())}                            ║")
            display_print("╚═══════════════════════════════════════════════════════════╝")
            display_print("")

            while True:

                if request.wait_edge_events(timeout=None):
                    events = request.read_edge_events()

                    # Process ONLY the first real event inside this batch
                    for event in events:
                        gpio_pin = event.line_offset
                        button_name = BUTTON_MAP.get(gpio_pin, "Unknown")
                        event_type = event.event_type # 1=Rising(Release), 2=Falling(Press)

                        now = time.time() * 1000

                        # Debounce check
                        if now - last_press_time.get(button_name, 0) < DEBOUNCE_MS:
                            continue

                        last_press_time[button_name] = now
                        handle_button_press(button_name, event_type)

                        # Crucial: stop processing this batch (bounce fix)
                        break

    except OSError as e:
        display_print(f"GPIO Error: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        display_print("\n\n╔═══════════════════════════════════════════════════════════╗")
        display_print("║        Shatrox Button Service Stopped                     ║")
        display_print("╚═══════════════════════════════════════════════════════════╝")
        sys.exit(0)


if __name__ == "__main__":
    run()
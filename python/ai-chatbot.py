#!/usr/bin/env python3
"""
AI Chatbot Orchestration Service
Handles voice chat and camera vision with state machine
Modified for VOSK ASR (offline speech recognition)
"""

import os
import sys
import time
import socket
import threading
import subprocess
import configparser
import json
import signal
import wave
from pathlib import Path
from datetime import datetime
from enum import Enum

# VOSK imports
try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("ERROR: VOSK not installed. Run: pip3 install vosk")
    sys.exit(1)

# Ollama import
try:
    import ollama
except ImportError:
    print("ERROR: Ollama Python package not installed. Run: pip3 install ollama")
    sys.exit(1)

# Wake word detection and audio processing imports
try:
    from openwakeword.model import Model as WakeWordModel
    import pyaudio
    import numpy as np
    from scipy.signal import decimate
    WAKE_WORD_AVAILABLE = True
except ImportError:
    print("WARNING: OpenWakeWord not installed. Wake word detection disabled.")
    print("Install with: pip3 install openwakeword pyaudio numpy scipy")
    WAKE_WORD_AVAILABLE = False

# Voice Activity Detection for end-of-speech detection
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    print("WARNING: webrtcvad not installed. Using timer-based recording.")
    print("Install with: pip3 install webrtcvad")
    VAD_AVAILABLE = False

# System tools for function calling
try:
    from system_tools import TOOL_DEFINITIONS, execute_tool, detect_command_category, get_current_time, get_current_date
except ImportError:
    print("ERROR: system_tools.py not found. Function calling will not work.")
    TOOL_DEFINITIONS = []
    execute_tool = None
    detect_command_category = None


# Configuration
CONFIG_FILE = "/etc/ai-chatbot/config.ini"
SOCKET_PATH = "/tmp/ai-chatbot.sock"
LOG_FILE = "/var/log/robot-ai.log"
RECORDINGS_DIR = "/tmp/ai-recordings"
CAMERA_DIR = "/tmp/ai-camera"
VOSK_MODEL_PATH = "/usr/share/vosk-models/default"
QA_DISPLAY_FILE = "/tmp/ai-qa-display.txt"  # Clean Q&A for display only

class State(Enum):
    WAKE_LISTENING = "wake_listening"  # NEW: Listening for wake word
    WAKE_DETECTED = "wake_detected"   # NEW: Wake word just detected
    IDLE = "idle"
    LISTENING = "listening"            # Recording command after wake word or button
    TRANSCRIBING = "transcribing"
    ANSWERING = "answering"
    SPEAKING = "speaking"
    CAMERA = "camera"

class AIChatBot:
    def __init__(self):
        self.state = State.IDLE
        self.config = self.load_config()
        self.socket_server = None
        self.recording_process = None
        self.current_audio_file = None
        self.conversation_history = []
        self.last_interaction_time = time.time()
        self.vosk_model = None
        
        # Wake word detection attributes
        self.wake_word_enabled = self.config['wake_word'].getboolean('enabled', fallback=False)
        self.wake_word_thread = None
        self.wake_word_running = False
        self.wake_word_paused = False  # Pause wake word during TTS only
        self._wake_debug_counter = 0   # For debug logging
        
        # Audio buffer for PyAudio recording (unified for wake word + K1)
        self.audio_buffer = []
        self.recording_start_time = None
        self.recording_duration = 5.0  # Default fallback (if VAD disabled)
        self.is_recording = False
        
        # RELIABILITY FIX: Thread-safe recording state management
        self.recording_lock = threading.Lock()  # Mutex for recording state changes
        self.recording_source = None  # 'wake_word' or 'k1_button' - tracks who started recording
        
        # VAD-based end-of-speech detection
        self.vad = None
        self.last_speech_time = None
        self.speech_started = False
        
        # Current Q&A for display
        self.current_question = None
        
        self.shutdown_event = threading.Event()
        
        # Cooldown after TTS to prevent false wake word triggers
        self.tts_cooldown_until = 0  # timestamp when cooldown ends
        
        # Create directories
        Path(RECORDINGS_DIR).mkdir(parents=True, exist_ok=True)
        Path(CAMERA_DIR).mkdir(parents=True, exist_ok=True)
        
        # DEFENSIVE FIX: Clear any stale listening state from previous crashes/restarts
        # This prevents the mic indicator from being stuck on display after service restart
        try:
            with open(QA_DISPLAY_FILE, 'w') as f:
                f.write("")  # Clear the file to prevent stale "LISTENING..." state
            self.log("Cleared stale display state on startup", "INFO")
        except Exception as e:
            self.log(f"Failed to clear display state on startup: {e}", "WARN")
        
        # Load VOSK model
        self.load_vosk_model()
        
        # Initialize Ollama client (network or local)
        self.ollama_client = self.init_ollama_client()
        self.use_network_ollama = self.config['ollama']['ollama_host'] != 'local'
        
    def load_vosk_model(self):
        """Load VOSK speech recognition model"""
        self.log("Loading VOSK model...")
        try:
            if not os.path.exists(VOSK_MODEL_PATH):
                self.log(f"VOSK model not found at {VOSK_MODEL_PATH}", "ERROR")
                sys.exit(1)
            
            self.vosk_model = Model(VOSK_MODEL_PATH)
            self.log(f"VOSK model loaded from {VOSK_MODEL_PATH}")
        except Exception as e:
            self.log(f"Failed to load VOSK model: {e}", "ERROR")
            sys.exit(1)
    
    def init_ollama_client(self):
        """Initialize Ollama client (network or local)"""
        ollama_host = self.config['ollama']['ollama_host']
        
        if ollama_host != 'local':
            # Network Ollama server
            self.log(f"Using network Ollama server: {ollama_host}")
            return ollama.Client(host=f"http://{ollama_host}")
        else:
            # Local Ollama
            self.log("Using local Ollama server")
            return ollama.Client()
    
    def load_config(self):
        """Load configuration from INI file"""
        config = configparser.ConfigParser()
        
        # Defaults
        config['ollama'] = {
            'ollama_host': 'local',
            'network_vision_model': 'moondream',
            'network_text_model': 'llama3.2:3b',
            'network_timeout': '5'
        }
        config['llm'] = {
            'system_prompt': 'You are a helpful robot. Answer in 1 sentence maximum. Be direct and concise.',
            'text_model': 'llama3.2:1b',
            'vision_model': 'moondream',
            'max_tokens': '50',
            'temperature': '0.7'
        }
        config['vosk'] = {
            'model_path': VOSK_MODEL_PATH,
            'sample_rate': '16000'
        }
        config['audio'] = {
            'microphone_device': 'plughw:2,0',
            'speaker_device': 'auto',
            'sample_rate': '16000'
        }
        config['camera'] = {
            'enable': 'true',
            'resolution': '640x480'
        }
        config['behavior'] = {
            'chat_history_timeout': '300',
            'max_history_messages': '10'
        }
        config['wake_word'] = {
            'enabled': 'false',  # Will be true after setup
            'model_path': '/usr/share/openwakeword-models/hey_jarvis_v0.1.tflite',
            'threshold': '0.5',
            'feedback_sound': '/usr/share/sounds/wake.wav',
            'command_timeout': '5',
            # VAD settings for end-of-speech detection
            'vad_enabled': 'true',           # Use VAD for silence detection
            'vad_aggressiveness': '2',        # 0-3 (higher = more aggressive)
            'silence_threshold': '0.8',       # Seconds of silence to stop recording
            'max_recording_time': '10'        # Maximum recording time (safety)
        }
        
        # Load from file if exists
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            
        return config
    
    def log(self, message, level="INFO"):
        """Write to log file and stdout"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + "\n")
        except Exception as e:
            print(f"Failed to write to log: {e}")
    
    def update_display(self, status, text=""):
        """Send status update to QML display via log file"""
        try:
            display_msg = {
                "type": "chat_status",
                "state": status,
                "text": text,
                "timestamp": time.time()
            }
            
            # Write to shared log file (same as button service)
            display_log = "/tmp/shatrox-display.log"
            with open(display_log, 'a') as f:
                f.write(f"CHAT_STATUS:{json.dumps(display_msg)}\n")
                
        except Exception as e:
            self.log(f"Failed to update display: {e}", "ERROR")
    
    def update_qa_display(self, question=None, answer=None, listening=False, clear=False):
        """Update Q&A display file for current interaction only"""
        try:
            if clear or listening:
                # Clear screen or show listening indicator
                if listening:
                    # ASCII art microphone for visual feedback
                    content = """
       🎙️
      ╔═══╗
      ║   ║
      ║ ● ║
      ╚═╦═╝
        ║
      ══╩══

   LISTENING...
"""
                else:
                    content = ""
                with open(QA_DISPLAY_FILE, 'w') as f:
                    f.write(content)
                return
            
            # Build current Q&A display
            lines = []
            if question:
                lines.append(f"❓ {question}")
            if answer:
                lines.append(f"💬 {answer}")
            
            # Write to file (replaces previous content)
            with open(QA_DISPLAY_FILE, 'w') as f:
                f.write('\n\n'.join(lines))
                
        except Exception as e:
            self.log(f"Failed to update Q&A display: {e}", "ERROR")
    
    def set_state(self, new_state):
        """Change state and update display"""
        old_state = self.state
        self.state = new_state
        self.log(f"State: {old_state.value} -> {new_state.value}")
        
        # RELIABILITY FIX: Clear all recording-related states when leaving LISTENING
        # Uses mutex lock to ensure thread-safe cleanup
        if old_state == State.LISTENING and new_state != State.LISTENING:
            try:
                with self.recording_lock:
                    self.is_recording = False
                    self.recording_source = None
                self.update_qa_display(clear=True)
                self.log("Auto-cleared recording state on LISTENING exit", "DEBUG")
            except Exception as e:
                self.log(f"Failed to auto-clear recording state: {e}", "WARN")
        
        # DEFENSIVE: Clear display when entering WAKE_LISTENING or IDLE (reset states)
        if new_state in (State.WAKE_LISTENING, State.IDLE):
            try:
                self.update_qa_display(clear=True)
            except Exception:
                pass  # Silent cleanup
        
        self.update_display(new_state.value)
    
    def start_recording(self):
        """Start audio recording (K1 button triggered)"""
        # RELIABILITY FIX: Thread-safe recording with K1 priority
        with self.recording_lock:
            # K1 button takes priority - if wake word started recording, take over
            if self.is_recording:
                if self.recording_source == 'k1_button':
                    self.log("K1 start_recording ignored - K1 already recording", "DEBUG")
                    return
                else:
                    # Wake word was recording, K1 takes over (user explicitly pressed button)
                    self.log("K1 taking over from wake word recording", "INFO")
            
            self.set_state(State.LISTENING)
            
            # Show listening indicator on display
            self.update_qa_display(listening=True)
            
            # CRITICAL FIX: Disable VAD for K1 button - recording stops on button RELEASE only
            # This prevents stale VAD state from triggering early stop
            self.vad = None
            self.last_speech_time = None
            self.speech_started = False
            
            # Clear buffer and start recording
            self.audio_buffer = []
            self.recording_start_time = time.time()
            self.is_recording = True
            self.recording_source = 'k1_button'  # Track source for priority handling
            self.recording_duration = 10.0  # K1 button: record for 10 seconds max or until button release
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_audio_file = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
            
            self.log(f"Started recording (K1 button, no VAD - waits for release)")
    
    def stop_recording(self):
        """Stop audio recording and save buffer to WAV file"""
        # RELIABILITY FIX: Thread-safe recording state check
        with self.recording_lock:
            if not self.is_recording:
                self.log("Stop recording called but not currently recording")
                return
            
            # Clear recording flags atomically FIRST to prevent race conditions
            self.is_recording = False
            recording_source = self.recording_source  # Save for logging
            self.recording_source = None
            
            # CRITICAL FIX: Reset VAD state to prevent stale values in next session
            self.vad = None
            self.last_speech_time = None
            self.speech_started = False
            
            # Copy buffer reference so we can process outside lock
            audio_data = list(self.audio_buffer)
            self.audio_buffer = []
        
        # Processing happens outside the lock to avoid blocking other threads
        self.log(f"Stopped recording (was: {recording_source})")
        
        # DEFENSIVE FIX: Use try/finally to ensure cleanup always happens
        try:
            # Check if we have any audio data
            if not audio_data or len(audio_data) == 0:
                self.log("No audio data recorded", "WARN")
                self.update_qa_display(clear=True)  # Clear listening indicator
                if self.wake_word_enabled:
                    self.set_state(State.WAKE_LISTENING)
                else:
                    self.set_state(State.IDLE)
                return
            
            # Restore buffer for save function (temporary)
            self.audio_buffer = audio_data
            
            # Save buffered audio to WAV file
            try:
                self.save_audio_buffer_to_wav()
                
                # Check file size
                file_size = os.path.getsize(self.current_audio_file)
                if file_size < 1000:  # Less than 1KB
                    self.log(f"Recording too small ({file_size} bytes), no usable audio", "WARN")
                    os.remove(self.current_audio_file)
                    self.update_qa_display(clear=True)  # Clear listening indicator
                    if self.wake_word_enabled:
                        self.set_state(State.WAKE_LISTENING)
                    else:
                        self.set_state(State.IDLE)
                    return
                
                # Transcribe
                self.set_state(State.TRANSCRIBING)
                self.transcribe_audio()
                
            except Exception as e:
                self.log(f"Error saving/transcribing audio: {e}", "ERROR")
                self.update_qa_display(clear=True)  # Clear listening indicator
                if self.wake_word_enabled:
                    self.set_state(State.WAKE_LISTENING)
                else:
                    self.set_state(State.IDLE)
        
        finally:
            # DEFENSIVE FIX: Always ensure display is clean
            # This runs even if there were exceptions above
            # Double-check that listening indicator is cleared (defensive)
            try:
                # Only clear if we're not already in TRANSCRIBING state (which means transcribe succeeded)
                if self.state != State.TRANSCRIBING:
                    self.update_qa_display(clear=True)
                    self.log("Ensured listening indicator cleared in finally block", "DEBUG")
            except Exception as e:
                self.log(f"Failed to clear indicator in finally block: {e}", "WARN")
                self.set_state(State.IDLE)
    
    def save_audio_buffer_to_wav(self):
        """Convert PyAudio buffer (48kHz) to WAV file (16kHz)"""
        # Concatenate all audio chunks
        audio_48k_bytes = b''.join(self.audio_buffer)
        audio_48k = np.frombuffer(audio_48k_bytes, dtype=np.int16)
        
        # Decimate from 48kHz to 16kHz (factor of 3)
        audio_16k = decimate(audio_48k, 3)
        
        # Save to WAV file
        with wave.open(self.current_audio_file, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz
            wf.writeframes(audio_16k.astype(np.int16).tobytes())
        
        self.log(f"Saved {len(audio_48k)/48000:.1f}s of audio to {self.current_audio_file}")
    
    def transcribe_audio(self):
        """Transcribe audio with VOSK"""
        self.set_state(State.TRANSCRIBING)
        self.update_display("transcribing", "🔄 Transcribing...")
        
        try:
            # Open audio file
            wf = wave.open(self.current_audio_file, "rb")
            
            # Check format
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                self.log("Audio format must be mono PCM WAV", "ERROR")
                self.set_state(State.IDLE)
                return
            
            # Create recognizer
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
            rec.SetWords(True)
            
            # Process audio
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)
            
            # Get final result
            result = json.loads(rec.FinalResult())
            transcribed_text = result.get("text", "").strip()
            
            if transcribed_text:
                self.log(f"Transcribed: {transcribed_text}")
                self.update_display("transcribing", transcribed_text)
                self.answer_question(transcribed_text)
            else:
                self.log("No speech detected", "WARN")
                self.update_qa_display(clear=True)  # FIX: Clear listening indicator
                # Return to wake listening if enabled, otherwise IDLE
                if self.wake_word_enabled:
                    # Add cooldown to prevent wake word from immediately re-triggering
                    self.tts_cooldown_until = time.time() + 1.0
                    self.log("Setting 1s cooldown to prevent wake word re-trigger")
                    self.set_state(State.WAKE_LISTENING)
                else:
                    self.set_state(State.IDLE)
                
        except Exception as e:
            self.log(f"Transcription failed: {e}", "ERROR")
            self.update_qa_display(clear=True)  # FIX: Clear listening indicator
            self.set_state(State.IDLE)
        finally:
            # Clean up audio file
            if self.current_audio_file and os.path.exists(self.current_audio_file):
                os.remove(self.current_audio_file)
    
    def answer_question(self, question):
        """Get answer from LLM with tool calling support"""
        self.set_state(State.ANSWERING)
        self.update_display("answering", "🤔 Thinking...")
        
        # Check if we should reset history (before updating timestamp)
        timeout = int(self.config['behavior']['chat_history_timeout'])
        if time.time() - self.last_interaction_time > timeout:
            self.log("Resetting conversation history (timeout)")
            self.conversation_history = []
        
        # Update last interaction time
        self.last_interaction_time = time.time()
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": question})
        
        # Store and display current question
        self.current_question = question
        self.update_qa_display(question=question)
        
        # Limit history
        max_history = int(self.config['behavior']['max_history_messages'])
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        try:
            # STAGE 1: Detect command CATEGORY using regex (loose matching)
            command_category = None
            if detect_command_category:
                command_category = detect_command_category(question)
            
            if command_category:
                # OPTIMIZATION: Camera command can bypass LLM (no parameters, instant trigger)
                if command_category == 'CAMERA_COMMAND':
                    self.log("Camera command - executing directly (no LLM needed)")
                    self.capture_camera()
                    return
                
                # OPTIMIZATION: Motor stop/explore bypass LLM (no parameters, prevents AI confusion)
                if command_category == 'MOTOR_STOP':
                    self.log("Motor STOP command - executing directly (no LLM needed)")
                    from system_tools import motor_stop
                    result = motor_stop()
                    self.conversation_history.append({"role": "assistant", "content": result})
                    self.update_qa_display(question=self.current_question, answer=result)
                    self.speak_answer(result)
                    return
                
                if command_category == 'MOTOR_EXPLORE':
                    self.log("Motor EXPLORE command - executing directly (no LLM needed)")
                    from system_tools import motor_explore
                    result = motor_explore()
                    self.conversation_history.append({"role": "assistant", "content": result})
                    self.update_qa_display(question=self.current_question, answer=result)
                    self.speak_answer(result)
                    return
                
                # STAGE 2: For all other commands, use AI WITH tools to parse details
                # (TIME, DATE, VOLUME, SHUTDOWN all need LLM for typo handling)
                self.log(f"Command category detected: {command_category} (needs LLM parsing)")
                
                # Try network Ollama first if configured
                if self.use_network_ollama:
                    text_model = self.config['ollama']['network_text_model']
                    self.log(f"Using network Ollama for command: {text_model}")
                    
                    try:
                        response = self.ollama_client.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'You are a robot assistant. The user is giving you a system command. Use the available tools to execute it. Handle variations and typos intelligently (e.g., "too" → "to", "fifty" → 50).'
                                },
                                {
                                    'role': 'user',
                                    'content': question
                                }
                            ],
                            tools=TOOL_DEFINITIONS,
                            options={
                                'num_ctx': 2048,
                                'temperature': 0.3,
                                'num_predict': 80
                            }
                        )
                        self.log("Network Ollama success")
                    
                    except (ConnectionError, TimeoutError, Exception) as e:
                        # Network failed - fall back to local
                        self.log(f"Network Ollama failed: {e}, falling back to local", "WARN")
                        text_model = self.config['llm']['text_model']
                        
                        response = ollama.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'You are a robot assistant. The user is giving you a system command. Use the available tools to execute it. Handle variations and typos intelligently (e.g., "too" → "to", "fifty" → 50).'
                                },
                                {
                                    'role': 'user',
                                    'content': question
                                }
                            ],
                            tools=TOOL_DEFINITIONS,
                            options={
                                'num_ctx': 2048,
                                'temperature': 0.3,
                                'num_predict': 80
                            }
                        )
                        self.log(f"Local Ollama fallback success: {text_model}")
                else:
                    # Use local Ollama directly
                    text_model = self.config['llm']['text_model']
                    response = ollama.chat(
                        model=text_model,
                        messages=[
                            {
                                'role': 'system',
                                'content': 'You are a robot assistant. The user is giving you a system command. Use the available tools to execute it. Handle variations and typos intelligently (e.g., "too" → "to", "fifty" → 50).'
                            },
                            {
                                'role': 'user',
                                'content': question
                            }
                        ],
                        tools=TOOL_DEFINITIONS,
                        options={
                            'num_ctx': 2048,
                            'temperature': 0.3,
                            'num_predict': 80
                        }
                    )
                
                # Check if AI returned tool calls
                if 'tool_calls' in response.get('message', {}) and execute_tool:
                    tool_calls = response['message']['tool_calls']
                    self.log(f"AI parsed {len(tool_calls)} tool call(s)")
                    
                    tool_results = []
                    for tool_call in tool_calls:
                        func_name = tool_call.function.name
                        func_args = tool_call.function.arguments
                        
                        self.log(f"Executing: {func_name}({func_args})")
                        self.update_display("answering", f"⚙️ {func_name}...")
                        
                        # Special handling for camera
                        if func_name == 'take_picture':
                            self.log("Tool: take_picture - triggering camera")
                            self.capture_camera()
                            return  # Camera handles the rest
                        
                        # Execute other tools
                        result = execute_tool(func_name, func_args)
                        self.log(f"Result: {result}")
                        tool_results.append(result)
                    
                    # Speak combined results
                    if tool_results:
                        combined_result = ". ".join(tool_results)
                        self.conversation_history.append({"role": "assistant", "content": combined_result})
                        self.update_qa_display(question=self.current_question, answer=combined_result)
                        self.speak_answer(combined_result)
                    else:
                        self.set_state(State.IDLE)
                else:
                    # AI couldn't parse the command - fallback to best guess
                    self.log("AI couldn't parse command, asking for clarification", "WARN")
                    fallback_msg = "I detected a command but couldn't understand the details. Please try again."
                    self.conversation_history.append({"role": "assistant", "content": fallback_msg})
                    self.update_qa_display(question=self.current_question, answer=fallback_msg)
                    self.speak_answer(fallback_msg)
            
            else:
                # NOT a command - regular question, use AI WITHOUT tools
                self.log("Regular question detected (no command category)")
                
                # Try network Ollama first if configured
                if self.use_network_ollama:
                    text_model = self.config['ollama']['network_text_model']
                    self.log(f"Using network Ollama for chat: {text_model}")
                    
                    try:
                        response = self.ollama_client.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'You are a helpful robot. Give direct, concise answers. Maximum 2 sentences. No extra formatting or explanations.'
                                },
                                {
                                    'role': 'user',
                                    'content': question
                                }
                            ],
                            options={
                                'num_ctx': 2048,
                                'temperature': 0.7,
                                'num_predict': 50
                            }
                        )
                        self.log("Network Ollama success")
                    
                    except (ConnectionError, TimeoutError, Exception) as e:
                        # Network failed - fall back to local
                        self.log(f"Network Ollama failed: {e}, falling back to local", "WARN")
                        text_model = self.config['llm']['text_model']
                        
                        response = ollama.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'You are a helpful robot. Give direct, concise answers. Maximum 2 sentences. No extra formatting or explanations.'
                                },
                                {
                                    'role': 'user',
                                    'content': question
                                }
                            ],
                            options={
                                'num_ctx': 2048,
                                'temperature': 0.7,
                                'num_predict': 50
                            }
                        )
                        self.log(f"Local Ollama fallback success: {text_model}")
                else:
                    # Use local Ollama directly
                    text_model = self.config['llm']['text_model']
                    response = ollama.chat(
                        model=text_model,
                        messages=[
                            {
                                'role': 'system',
                                'content': 'You are a helpful robot. Give direct, concise answers. Maximum 2 sentences. No extra formatting or explanations.'
                            },
                            {
                                'role': 'user',
                                'content': question
                            }
                        ],
                        options={
                            'num_ctx': 2048,
                            'temperature': 0.7,
                            'num_predict': 50
                        }
                    )
                
                # Regular chat response
                answer = response['message']['content']
                answer = answer.strip()
                
                if answer and len(answer) > 10:
                    self.log(f"Answer: {answer}")
                    self.conversation_history.append({"role": "assistant", "content": answer})
                    self.update_qa_display(question=self.current_question, answer=answer)
                    self.speak_answer(answer)
                else:
                    self.log(f"No valid answer (got: {response['message']['content'][:100]})", "WARN")
                    self.set_state(State.IDLE)
                
        except Exception as e:
            self.log(f"LLM failed: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self.set_state(State.IDLE)

    
    def speak_answer(self, text):
        """Convert text to speech and play"""
        self.set_state(State.SPEAKING)
        self.update_display("speaking", text)
        
        try:
            # ⚠️ CRITICAL: Mute wake word detection during TTS to prevent audio feedback loop
            self.wake_word_paused = True
            self.log("Wake word detection PAUSED (speaking)")
            
            # Use 'speak' command (Piper TTS wrapper)
            subprocess.run(['speak', text], timeout=30)
            
            self.log("Finished speaking")
            
            # ⚠️ CRITICAL: Add cooldown to prevent TTS audio from triggering wake word
            cooldown_seconds = 1.5  # Wait 1.5 seconds before accepting wake words
            self.tts_cooldown_until = time.time() + cooldown_seconds
            self.log(f"Wake word cooldown for {cooldown_seconds}s")
            
            # ⚠️ CRITICAL: Unmute wake word detection after TTS
            self.wake_word_paused = False
            self.log("Wake word detection RESUMED")
            
            # Return to wake listening if wake word enabled, otherwise IDLE
            if self.wake_word_enabled:
                self.set_state(State.WAKE_LISTENING)
            else:
                self.set_state(State.IDLE)
            
        except subprocess.TimeoutExpired:
            self.log("TTS timeout", "ERROR")
            self.wake_word_paused = False  # Unmute on error
            self.set_state(State.WAKE_LISTENING if self.wake_word_enabled else State.IDLE)
        except Exception as e:
            self.log(f"TTS failed: {e}", "ERROR")
            self.wake_word_paused = False  # Unmute on error
            self.set_state(State.WAKE_LISTENING if self.wake_word_enabled else State.IDLE)
    
    def capture_camera(self):
        """Capture image and describe it"""
        if self.config['camera']['enable'].lower() != 'true':
            self.log("Camera disabled in config", "WARN")
            return
        
        self.set_state(State.CAMERA)
        self.update_display("camera", "📷 Capturing...")
        
        # Show Q&A message immediately
        self.update_qa_display(question="[Camera] Analyzing captured image...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(CAMERA_DIR, f"capture_{timestamp}.jpg")
        
        # Detect camera command (rpicam-still for new RPi OS, libcamera-still for old)
        camera_cmd = None
        if subprocess.run(['which', 'rpicam-still'], capture_output=True).returncode == 0:
            camera_cmd = 'rpicam-still'
        elif subprocess.run(['which', 'libcamera-still'], capture_output=True).returncode == 0:
            camera_cmd = 'libcamera-still'
        else:
            self.log("Neither rpicam-still nor libcamera-still found!", "ERROR")
            self.set_state(State.IDLE)
            return
        
        try:
            # Capture image with detected camera command
            subprocess.run([
                camera_cmd,
                '-o', image_path,
                '-t', '1000',  # 1 second delay
                '--width', '640',
                '--height', '480',
                '--rotation', '180',  # Rotate 180° for upside-down camera
                '--nopreview'
            ], timeout=10, check=True)
            
            self.log(f"Captured image: {image_path}")
        
            # Create symlink for QML display overlay
            latest_photo_link = "/tmp/shatrox-latest-photo.jpg"
            try:
                # Remove old symlink if exists
                if os.path.exists(latest_photo_link):
                    os.remove(latest_photo_link)
                # Create new symlink
                os.symlink(image_path, latest_photo_link)
                # Write trigger timestamp for QML to detect
                with open("/tmp/shatrox-photo-trigger", "w") as f:
                    f.write(f"{time.time()}\n")
                self.log("Created photo symlink for display overlay")
            except Exception as e:
                self.log(f"Failed to create photo symlink: {e}", "WARN")
            
            # Describe image with vision model
            self.describe_image(image_path)
            
        except subprocess.TimeoutExpired:
            self.log("Camera capture timeout", "ERROR")
            self.set_state(State.IDLE)
        except Exception as e:
            self.log(f"Camera capture failed: {e}", "ERROR")
            self.set_state(State.IDLE)
    
    def describe_image(self, image_path):
        """Use vision model to describe image"""
        self.set_state(State.ANSWERING)
        self.update_display("answering", "🤔 Analyzing image...")
        
        # Use consistent prompt for length control
        prompt = "Describe this image. Keep the answer to maximum 1 or 2 sentences."
        description = None
        
        try:
            # Try network Ollama first if configured
            if self.use_network_ollama:
                vision_model = self.config['ollama']['network_vision_model']
                timeout = int(self.config['ollama']['network_timeout'])
                
                self.log(f"Trying network Ollama with model: {vision_model}")
                
                try:
                    response = self.ollama_client.chat(
                        model=vision_model,
                        messages=[
                            {
                                'role': 'user',
                                'content': prompt,
                                'images': [image_path]
                            }
                        ],
                        options={
                            'num_ctx': 2048,
                            'temperature': 0.7
                        }
                    )
                    description = response['message']['content'].strip()
                    self.log(f"Network Ollama success: {description[:50]}...")
                    
                except (ConnectionError, TimeoutError, Exception) as network_error:
                    # Network failed, fall back to local
                    self.log(f"Network Ollama failed: {network_error}", "WARN")
                    self.log("Falling back to local Ollama...", "WARN")
                    
                    # Use local moondream as fallback
                    vision_model = self.config['llm']['vision_model']
                    response = ollama.chat(
                        model=vision_model,
                        messages=[
                            {
                                'role': 'user',
                                'content': prompt,
                                'images': [image_path]
                            }
                        ],
                        options={
                            'num_ctx': 2048,
                            'temperature': 0.7
                        }
                    )
                    description = response['message']['content'].strip()
                    self.log(f"Local Ollama fallback success: {description[:50]}...")
            else:
                # Use local Ollama directly
                vision_model = self.config['llm']['vision_model']
                self.log(f"Using local Ollama with model: {vision_model}")
                
                response = ollama.chat(
                    model=vision_model,
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [image_path]
                        }
                    ],
                    options={
                        'num_ctx': 2048,
                        'temperature': 0.7
                    }
                )
                description = response['message']['content'].strip()
                self.log(f"Local Ollama success: {description[:50]}...")
            
            if description:
                self.log(f"Image description: {description}")
                # Update Q&A display with answer (question was already shown at capture time)
                self.update_qa_display(answer=description)
                self.speak_answer(description)
            else:
                self.log("No description generated", "WARN")
                self.set_state(State.IDLE)
                
        except Exception as e:
            self.log(f"Vision model failed: {e}", "ERROR")
            self.set_state(State.IDLE)
    
    def wake_word_detected_handler(self):
        """Called when wake word is detected by wake word thread"""
        self.log("🔔 Wake word detected!", "INFO")
        
        # RELIABILITY FIX: Thread-safe check - K1 button has priority
        with self.recording_lock:
            if self.is_recording:
                if self.recording_source == 'k1_button':
                    # K1 button is active - don't interrupt (user explicitly pressed button)
                    self.log("Wake word ignored - K1 button recording active", "DEBUG")
                    return
                else:
                    # Already recording from previous wake word - ignore duplicate detection
                    self.log("Wake word ignored - already recording from wake word", "DEBUG")
                    return
            
            # Start recording with wake word source
            self.set_state(State.WAKE_DETECTED)
            
            # Play feedback sound to indicate wake word detected
            feedback_sound = self.config['wake_word']['feedback_sound']
            if os.path.exists(feedback_sound):
                subprocess.Popen(['aplay', feedback_sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Show visual feedback on QML display (listening indicator)
            self.update_display("wake_detected", "🔔 Listening for command...")
            self.update_qa_display(listening=True)
            
            # Initialize VAD for end-of-speech detection
            vad_enabled = self.config['wake_word'].getboolean('vad_enabled', fallback=True)
            if vad_enabled and VAD_AVAILABLE:
                aggressiveness = int(self.config['wake_word'].get('vad_aggressiveness', 2))
                self.vad = webrtcvad.Vad(aggressiveness)
                self.last_speech_time = time.time()  # Assume wake word was speech
                self.speech_started = False
                self.log(f"VAD enabled (aggressiveness={aggressiveness})")
            else:
                self.vad = None
                self.log("VAD disabled, using timer-based recording")
            
            # Start recording command (uses PyAudio buffer)
            self.audio_buffer = []
            self.recording_start_time = time.time()
            self.is_recording = True
            self.recording_source = 'wake_word'  # Track source for priority handling
            self.recording_duration = float(self.config['wake_word'].get('max_recording_time', 10))
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_audio_file = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
            
            self.set_state(State.LISTENING)
            if self.vad:
                silence_threshold = float(self.config['wake_word'].get('silence_threshold', 0.8))
                self.log(f"Recording... (stop after {silence_threshold}s silence, max {self.recording_duration}s)")
            else:
                self.log(f"Recording command for {self.recording_duration}s...")
    
    def wake_word_loop(self):
        """Wake word detection thread - runs continuously"""
        if not WAKE_WORD_AVAILABLE:
            self.log("Wake word detection not available (OpenWakeWord not installed)", "ERROR")
            return
        
        self.log("Starting wake word detection thread...")
        
        try:
            # Load wake word model
            model_path = self.config['wake_word']['model_path']
            if not os.path.exists(model_path):
                self.log(f"Wake word model not found: {model_path}", "ERROR")
                return
            
            # Extract model name from path (e.g., hey_jarvis_v0.1.tflite -> hey_jarvis_v0.1)
            model_name = os.path.basename(model_path).replace('.tflite', '')
            threshold = float(self.config['wake_word'].get('threshold', 0.5))
            
            self.log(f"Loading wake word model from {model_path}")
            oww_model = WakeWordModel(wakeword_model_paths=[model_path])
            model_name = list(oww_model.models.keys())[0]
            self.log(f"Loaded wake word model: {model_name} (threshold: {threshold})")
            
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            
            # Find USB microphone (device 0: hw:0,0)
            usb_device_index = 0
            info = audio.get_device_info_by_index(usb_device_index)
            self.log(f"Using audio device {usb_device_index}: {info['name']}")
            
            # Record at 48kHz (mic's native rate) and we'll decimate to 16kHz
            NATIVE_RATE = 48000
            TARGET_RATE = 16000
            DECIMATION_FACTOR = NATIVE_RATE // TARGET_RATE  # = 3
            
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=NATIVE_RATE,  # Use mic's native 48kHz
                input=True,
                input_device_index=usb_device_index,
                frames_per_buffer=1280 * DECIMATION_FACTOR  # Read 3x more samples (3840)
            )
            
            self.log("Wake word detection active - say wake phrase to activate")
            self.set_state(State.WAKE_LISTENING)
            self.wake_word_running = True
            
            while self.wake_word_running:
                # Always read audio from stream (never pause - needed for buffering)
                try:
                    audio_data = stream.read(1280 * DECIMATION_FACTOR, exception_on_overflow=False)
                    audio_array_48k = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # If we're recording (wake word or K1 triggered), buffer the audio
                    if self.is_recording:
                        self.audio_buffer.append(audio_data)
                        elapsed = time.time() - self.recording_start_time
                        
                        # VAD-based end-of-speech detection
                        if self.vad:
                            # Decimate to 16kHz for VAD (webrtcvad needs 8/16/32/48 kHz)
                            audio_16k = audio_array_48k[::DECIMATION_FACTOR]
                            audio_16k_bytes = audio_16k.tobytes()
                            
                            # webrtcvad needs 10/20/30ms frames at 16kHz
                            # 16kHz * 0.020s = 320 samples = 640 bytes per 20ms frame
                            FRAME_SIZE = 320  # samples per 20ms frame
                            is_speech = False
                            
                            # Check if any frame in this chunk contains speech
                            for i in range(0, len(audio_16k) - FRAME_SIZE, FRAME_SIZE):
                                frame = audio_16k_bytes[i*2:(i+FRAME_SIZE)*2]  # 2 bytes per sample
                                if len(frame) == FRAME_SIZE * 2:
                                    try:
                                        if self.vad.is_speech(frame, 16000):
                                            is_speech = True
                                            break
                                    except:
                                        pass
                            
                            if is_speech:
                                self.last_speech_time = time.time()
                                if not self.speech_started:
                                    self.speech_started = True
                                    self.log("Speech detected, listening...")
                            
                            # Check silence threshold (only after speech started)
                            silence_threshold = float(self.config['wake_word'].get('silence_threshold', 0.8))
                            silence_duration = time.time() - self.last_speech_time
                            
                            if self.speech_started and silence_duration >= silence_threshold:
                                self.log(f"End of speech detected ({silence_duration:.1f}s silence)")
                                # DEFENSIVE FIX: Wrap in try/except to ensure cleanup even if stop_recording fails
                                try:
                                    self.stop_recording()
                                except Exception as e:
                                    self.log(f"Error in stop_recording (VAD): {e}", "ERROR")
                                    self.is_recording = False
                                    self.update_qa_display(clear=True)
                                    self.set_state(State.WAKE_LISTENING if self.wake_word_enabled else State.IDLE)
                            elif elapsed >= self.recording_duration:
                                self.log(f"Max recording time reached ({elapsed:.1f}s)")
                                # DEFENSIVE FIX: Wrap in try/except to ensure cleanup even if stop_recording fails
                                try:
                                    self.stop_recording()
                                except Exception as e:
                                    self.log(f"Error in stop_recording (timeout): {e}", "ERROR")
                                    self.is_recording = False
                                    self.update_qa_display(clear=True)
                                    self.set_state(State.WAKE_LISTENING if self.wake_word_enabled else State.IDLE)
                        else:
                            # Fallback: timer-based recording (no VAD)
                            if elapsed >= self.recording_duration:
                                self.log(f"Auto-stopping recording after {elapsed:.1f}s")
                                # DEFENSIVE FIX: Wrap in try/except to ensure cleanup even if stop_recording fails
                                try:
                                    self.stop_recording()
                                except Exception as e:
                                    self.log(f"Error in stop_recording (fallback): {e}", "ERROR")
                                    self.is_recording = False
                                    self.update_qa_display(clear=True)
                                    self.set_state(State.WAKE_LISTENING if self.wake_word_enabled else State.IDLE)
                    
                    # Only do wake word detection if in WAKE_LISTENING state and not in cooldown
                    if self.state == State.WAKE_LISTENING and not self.wake_word_paused:
                        # Decimate from 48kHz to 16kHz (take every 3rd sample)
                        audio_array = audio_array_48k[::DECIMATION_FACTOR]
                        
                        # Feed to wake word model (now 16kHz, 1280 samples)
                        prediction = oww_model.predict(audio_array)
                        
                        # Check TTS cooldown - still feed audio to model (to clear buffers)
                        # but ignore predictions during cooldown period
                        if time.time() < self.tts_cooldown_until:
                            # Still in cooldown, discard predictions to clear model buffers
                            continue
                        
                        # Debug: Log predictions periodically (DISABLED - too verbose)
                        # if not hasattr(self, '_wake_debug_counter'):
                        #     self._wake_debug_counter = 0
                        # self._wake_debug_counter += 1
                        # if self._wake_debug_counter % 50 == 0:  # Every ~4 seconds
                        #     pred_str = ", ".join([f"{k}: {v:.3f}" for k, v in prediction.items()])
                        #     self.log(f"Wake word predictions: {pred_str}", "DEBUG")
                        
                        # Check if wake word detected (check all predictions for threshold)
                        max_score = max(prediction.values()) if prediction else 0
                        if max_score > threshold:
                            # Wake word detected!
                            detected_model = max(prediction.items(), key=lambda x: x[1])[0]
                            self.log(f"WAKE WORD DETECTED! Model: {detected_model}, Score: {max_score:.3f}")
                            self.wake_word_detected_handler()
                            # No blocking wait - continue reading audio for recording
                            # The recording timer will auto-stop and process the audio
                
                except Exception as e:
                    self.log(f"Wake word detection error: {e}", "ERROR")
                    time.sleep(0.1)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            audio.terminate()
            self.log("Wake word detection thread stopped")
            
        except Exception as e:
            self.log(f"Wake word thread failed: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
    
    def handle_command(self, command):
        """Handle incoming socket commands"""
        self.log(f"Received command: {command}")
        
        if command == "START_RECORDING":
            # Manual trigger from K1 button (bypass wake word)
            if self.state == State.IDLE or self.state == State.WAKE_LISTENING:
                self.start_recording()
        
        elif command == "STOP_RECORDING":
            if self.state == State.LISTENING:
                self.stop_recording()
        
        elif command == "CAMERA_CAPTURE":
            if self.state == State.IDLE or self.state == State.WAKE_LISTENING:
                self.capture_camera()
        
        elif command == "STATUS":
            return json.dumps({
                "state": self.state.value,
                "conversation_length": len(self.conversation_history),
                "wake_word_enabled": self.wake_word_enabled
            })
        
        elif command == "RESET":
            self.conversation_history = []
            self.log("Conversation history reset")
            if self.wake_word_enabled:
                self.set_state(State.WAKE_LISTENING)
            else:
                self.set_state(State.IDLE)
        
        return "OK"
    
    def socket_handler(self, conn):
        """Handle socket client connection"""
        try:
            data = conn.recv(1024).decode('utf-8').strip()
            if data:
                response = self.handle_command(data)
                conn.sendall((response or "OK").encode('utf-8'))
        except Exception as e:
            self.log(f"Socket handler error: {e}", "ERROR")
        finally:
            conn.close()
    
    def start_socket_server(self):
        """Start Unix socket server for commands"""
        # Remove existing socket if present
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        
        self.socket_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_server.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)  # Allow all users to connect
        self.socket_server.listen(5)
        
        self.log(f"Socket server listening on {SOCKET_PATH}")
        
        while True:
            try:
                conn, _ = self.socket_server.accept()
                # Handle in separate thread to not block
                thread = threading.Thread(target=self.socket_handler, args=(conn,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.socket_server:  # Only log if not shutting down
                    self.log(f"Socket server error: {e}", "ERROR")
                break
    
    def recording_watchdog(self):
        """Background thread to detect and recover from stuck recording states"""
        WATCHDOG_INTERVAL = 5  # Check every 5 seconds
        STUCK_THRESHOLD = 20   # 20 seconds is definitely stuck (max recording is 10s)
        
        # Wait for wake word loop to start (it sets wake_word_running = True)
        for _ in range(10):  # Max 5 seconds wait
            if self.wake_word_running:
                break
            time.sleep(0.5)
        
        if not self.wake_word_running:
            self.log("Recording watchdog: wake word loop not started, exiting", "WARN")
            return
        
        self.log("Recording watchdog started")
        
        while self.wake_word_running:
            time.sleep(WATCHDOG_INTERVAL)
            
            # Check if recording is stuck
            with self.recording_lock:
                if self.is_recording and self.recording_start_time:
                    elapsed = time.time() - self.recording_start_time
                    if elapsed > STUCK_THRESHOLD:
                        self.log(f"WATCHDOG: Recording stuck for {elapsed:.1f}s (source: {self.recording_source}) - forcing cleanup", "ERROR")
                        # Force clear recording state
                        self.is_recording = False
                        self.recording_source = None
                        
            # Check if display is stuck showing listening indicator when not recording
            if not self.is_recording and self.state not in (State.LISTENING, State.WAKE_DETECTED, State.TRANSCRIBING, State.ANSWERING, State.SPEAKING):
                try:
                    # Read display file and check if it shows listening
                    if os.path.exists(QA_DISPLAY_FILE):
                        with open(QA_DISPLAY_FILE, 'r') as f:
                            content = f.read()
                        if 'LISTENING' in content:
                            self.log("WATCHDOG: Stale listening indicator detected - clearing", "WARN")
                            self.update_qa_display(clear=True)
                except Exception as e:
                    pass  # Don't log file read errors in watchdog
        
        self.log("Recording watchdog stopped")
    
    def cleanup(self):
        """Cleanup resources"""
        self.log("Shutting down...")
        
        # Stop wake word thread
        if self.wake_word_thread:
            self.wake_word_running = False
            self.wake_word_thread.join(timeout=2)
        
        if self.recording_process:
            self.recording_process.terminate()
        
        if self.socket_server:
            self.socket_server.close()
        
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
    
    def run(self):
        """Main run loop"""
        self.log("AI Chatbot service started")
        self.log("="*50)
        self.log("AI Chatbot Service Started")
        self.log(f"ASR: VOSK (model: {VOSK_MODEL_PATH})")
        self.log(f"Text LLM: {self.config['llm']['text_model']} (local)")
        if self.use_network_ollama:
            self.log(f"Network Text LLM: {self.config['ollama']['network_text_model']} @ {self.config['ollama']['ollama_host']} (with fallback to local)")
            self.log(f"Network Vision LLM: {self.config['ollama']['network_vision_model']} @ {self.config['ollama']['ollama_host']} (with fallback to {self.config['llm']['vision_model']})")
        else:
            self.log(f"Vision LLM: {self.config['llm']['vision_model']} (local only)")
            # Log network Ollama host even if not using network LLMs, for info
            self.log(f"Network Ollama Host: {self.config['ollama']['ollama_host']}")
        
        # Start wake word detection if enabled
        if self.wake_word_enabled and WAKE_WORD_AVAILABLE:
            self.log("Wake word detection ENABLED")
            self.log(f"Model: {self.config['wake_word']['model_path']}")
            self.wake_word_thread = threading.Thread(target=self.wake_word_loop, daemon=True)
            self.wake_word_thread.start()
            
            # Start recording watchdog thread for stuck state recovery
            self.watchdog_thread = threading.Thread(target=self.recording_watchdog, daemon=True)
            self.watchdog_thread.start()
        else:
            if not WAKE_WORD_AVAILABLE:
                self.log("Wake word detection disabled (OpenWakeWord not installed)", "WARN")
            else:
                self.log("Wake word detection disabled (enable in config.ini)")
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup() or sys.exit(0))
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup() or sys.exit(0))
        
        try:
            self.start_socket_server()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

if __name__ == "__main__":
    bot = AIChatBot()
    bot.run()

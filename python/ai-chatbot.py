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

# Configuration
CONFIG_FILE = "/etc/ai-chatbot/config.ini"
SOCKET_PATH = "/tmp/ai-chatbot.sock"
LOG_FILE = "/var/log/robot-ai.log"
RECORDINGS_DIR = "/tmp/ai-recordings"
CAMERA_DIR = "/tmp/ai-camera"
VOSK_MODEL_PATH = "/usr/share/vosk-models/default"
QA_DISPLAY_FILE = "/tmp/ai-qa-display.txt"  # Clean Q&A for display only

class State(Enum):
    IDLE = "idle"
    LISTENING = "listening"
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
        
        # Create directories
        Path(RECORDINGS_DIR).mkdir(parents=True, exist_ok=True)
        Path(CAMERA_DIR).mkdir(parents=True, exist_ok=True)
        
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
    
    def update_qa_display(self, question=None, answer=None):
        """Update clean Q&A display file (no timestamps, just Q&A)"""
        try:
            # Read existing content
            qa_content = []
            if os.path.exists(QA_DISPLAY_FILE):
                with open(QA_DISPLAY_FILE, 'r') as f:
                    qa_content = f.read().strip().split('\n\n')
                    # Keep only last 5 Q&A pairs
                    if len(qa_content) > 5:
                        qa_content = qa_content[-5:]
            
            # Add new Q or A
            if question:
                qa_content.append(f"Q: {question}")
            elif answer:
                # Append answer to last question
                if qa_content:
                    qa_content[-1] += f"\nA: {answer}"
            
            # Write back
            with open(QA_DISPLAY_FILE, 'w') as f:
                f.write('\n\n'.join(qa_content))
                
        except Exception as e:
            self.log(f"Failed to update Q&A display: {e}", "ERROR")
    
    def set_state(self, new_state):
        """Change state and update display"""
        self.log(f"State transition: {self.state.value} -> {new_state.value}")
        self.state = new_state
        self.update_display(new_state.value)
    
    def start_recording(self):
        """Start audio recording"""
        self.set_state(State.LISTENING)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_audio_file = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
        
        # Start arecord process
        mic_device = self.config['audio']['microphone_device']
        sample_rate = self.config['audio']['sample_rate']
        
        try:
            self.recording_process = subprocess.Popen([
                'arecord',
                '-D', mic_device,
                '-f', 'S16_LE',
                '-r', sample_rate,
                '-c', '1',
                self.current_audio_file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log(f"Started recording to {self.current_audio_file}")
            self.update_display("listening", "🎤 Listening...")
            
        except Exception as e:
            self.log(f"Failed to start recording: {e}", "ERROR")
            self.set_state(State.IDLE)
    
    def stop_recording(self):
        """Stop audio recording and start transcription"""
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait(timeout=2)
            self.recording_process = None
            self.log("Stopped recording")
        
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            # Check if file has content
            if os.path.getsize(self.current_audio_file) > 1000:  # At least 1KB
                self.transcribe_audio()
            else:
                self.log("Recording too short, ignoring", "WARN")
                self.set_state(State.IDLE)
        else:
            self.set_state(State.IDLE)
    
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
                self.set_state(State.IDLE)
                
        except Exception as e:
            self.log(f"Transcription failed: {e}", "ERROR")
            self.set_state(State.IDLE)
        finally:
            # Clean up audio file
            if self.current_audio_file and os.path.exists(self.current_audio_file):
                os.remove(self.current_audio_file)
    
    def answer_question(self, question):
        """Get answer from LLM"""
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
        
        # Update Q&A display with question
        self.update_qa_display(question=question)
        
        # Limit history
        max_history = int(self.config['behavior']['max_history_messages'])
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        try:
            # Use Ollama for text chat with strict concise settings
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
                    'num_predict': 50  # Match tested config - enough for 1 concise sentence
                }
            )
            
            answer = response['message']['content']
            
            # Clean up answer - llama3.2:1b is naturally concise with good prompting
            answer = answer.strip()
            
            # Basic sanity check - must have meaningful content
            if answer and len(answer) > 10:
                self.log(f"Answer: {answer}")
                self.conversation_history.append({"role": "assistant", "content": answer})
                # Update Q&A display with answer
                self.update_qa_display(answer=answer)
                self.speak_answer(answer)
            else:
                self.log(f"No valid answer generated (got: {response['message']['content'][:100]})", "WARN")
                self.set_state(State.IDLE)
                
        except Exception as e:
            self.log(f"LLM failed: {e}", "ERROR")
            self.set_state(State.IDLE)
    
    def speak_answer(self, text):
        """Convert text to speech and play"""
        self.set_state(State.SPEAKING)
        self.update_display("speaking", text)
        
        try:
            # Use 'speak' command (Piper TTS wrapper)
            subprocess.run(['speak', text], timeout=30)
            
            self.log("Finished speaking")
            self.set_state(State.IDLE)
            
        except subprocess.TimeoutExpired:
            self.log("TTS timeout", "ERROR")
            self.set_state(State.IDLE)
        except Exception as e:
            self.log(f"TTS failed: {e}", "ERROR")
            self.set_state(State.IDLE)
    
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
    
    def handle_command(self, command):
        """Handle incoming socket commands"""
        self.log(f"Received command: {command}")
        
        if command == "START_RECORDING":
            if self.state == State.IDLE:
                self.start_recording()
        
        elif command == "STOP_RECORDING":
            if self.state == State.LISTENING:
                self.stop_recording()
        
        elif command == "CAMERA_CAPTURE":
            if self.state == State.IDLE:
                self.capture_camera()
        
        elif command == "STATUS":
            return json.dumps({
                "state": self.state.value,
                "conversation_length": len(self.conversation_history)
            })
        
        elif command == "RESET":
            self.conversation_history = []
            self.log("Conversation history reset")
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
    
    def cleanup(self):
        """Cleanup resources"""
        self.log("Shutting down...")
        
        if self.recording_process:
            self.recording_process.terminate()
        
        if self.socket_server:
            self.socket_server.close()
        
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
    
    def run(self):
        """Main run loop"""
        self.log("AI Chatbot service started")
        self.log(f"ASR: VOSK (model: {VOSK_MODEL_PATH})")
        self.log(f"Text LLM: {self.config['llm']['text_model']}")
        
        if self.use_network_ollama:
            self.log(f"Vision LLM: {self.config['ollama']['network_vision_model']} (network) with fallback to {self.config['llm']['vision_model']} (local)")
            self.log(f"Network Ollama: {self.config['ollama']['ollama_host']}")
        else:
            self.log(f"Vision LLM: {self.config['llm']['vision_model']} (local)")
        
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

#!/usr/bin/env python3
"""
SHATROX Motor Control Service
Controls Waveshare Motor Driver HAT with obstacle detection
Uses PCA9685 PWM driver and TB6612FNG H-bridge motor driver
"""

import time
import threading
import socket
import os
import sys
import json
import signal
from typing import Optional, Dict

# GPIO for ultrasonic sensor (3.3V compatible HC-SR04-P)
try:
    import gpiod
    from gpiod.line import Direction, Value
    GPIOD_AVAILABLE = True
except ImportError:
    print("ERROR: gpiod not available. Install with: pip3 install gpiod")
    GPIOD_AVAILABLE = False

# Motor driver (PCA9685 + TB6612FNG via Adafruit libraries)
try:
    import busio
    from adafruit_pca9685 import PCA9685
    from adafruit_motor import motor
    MOTOR_LIBS_AVAILABLE = True
except ImportError:
    print("ERROR: Adafruit motor libraries not available.")
    print("Install with: pip3 install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor adafruit-blinka")
    MOTOR_LIBS_AVAILABLE = False


# ============================================================================
# CONFIGURATION
# ============================================================================

# Ultrasonic Sensor GPIO Pins (HC-SR04-P on 3.3V)
SENSOR_TRIGGER_PIN = 22  # GPIO 22
SENSOR_ECHO_PIN = 23     # GPIO 23

# Motor channels on PCA9685
# Waveshare Motor Driver HAT wiring:
# - Channel A (MA1, MA2): Left side motors (parallel)
# - Channel B (MB1, MB2): Right side motors (parallel)
MOTOR_LEFT_PWM = 0    # PCA9685 channel for left motors (PWMA)
MOTOR_RIGHT_PWM = 5   # PCA9685 channel for right motors (PWMB)

# Safety configuration
OBSTACLE_DISTANCE_CM = 20  # Stop if obstacle closer than this (cm)
SENSOR_READ_INTERVAL = 0.1  # Read sensor every 100ms
MAX_SENSOR_DISTANCE = 400   # HC-SR04-P max range

# Obstacle avoidance behavior modes
OBSTACLE_BEHAVIOR_STOP = "stop_only"       # Just stop when obstacle detected
OBSTACLE_BEHAVIOR_BACKUP = "backup"        # Stop + back up
OBSTACLE_BEHAVIOR_AVOID = "backup_and_turn" # Stop + back up + turn (full avoidance)

# Avoidance timing (seconds)
BACKUP_DURATION = 1.0      # How long to back up
BACKUP_SPEED = 40          # Speed when backing up (0-100)
AVOID_TURN_DURATION = 2.0  # How long to turn when avoiding (Mecanum wheels turn quickly)
AVOID_TURN_SPEED = 100     # Speed when turning to avoid (full power for tank steering)

# Speed limits (0-100%)
DEFAULT_SPEED = 50
MAX_SPEED = 100
MIN_SPEED = 0

# Unix socket for external control
MOTOR_SOCKET = "/tmp/shatrox-motor-control.sock"

# Logging
LOG_FILE = "/var/log/shatrox-motor.log"


# ============================================================================
# MOTOR CONTROLLER CLASS
# ============================================================================

class MotorController:
    """
    Main motor control class with obstacle detection
    """
    
    def __init__(self):
        """Initialize motor driver and ultrasonic sensor"""
        
        self.running = False
        self.obstacle_detected = False
        self.current_speed = DEFAULT_SPEED
        self.sensor_thread = None
        self.socket_thread = None
        
        # Obstacle avoidance settings
        self.obstacle_behavior = OBSTACLE_BEHAVIOR_AVOID  # Default: full avoidance
        self.is_moving_forward = False  # Track if actively moving forward
        self.avoidance_in_progress = False  # Prevent re-triggering during avoidance
        self.explore_mode = False  # When True, auto-resume forward after obstacle avoidance
        
        # Initialize logging
        self.log("Motor Controller initializing...")
        
        # Initialize I2C and PCA9685
        if not MOTOR_LIBS_AVAILABLE:
            raise RuntimeError("Motor libraries not available. Cannot initialize.")
        
        try:
            # Use Waveshare's PCA9685 class directly (uses smbus)
            from WavesharePCA9685 import PCA9685
            self.pca = PCA9685(0x40, debug=False)
            self.pca.setPWMFreq(50)  # 50Hz  
            self.log("PCA9685 initialized at 50Hz (Waveshare implementation)")
        except Exception as e:
            self.log(f"ERROR: Failed to initialize PCA9685: {e}")
            raise
        
        
        # Motor channel assignments (Waveshare TB6612FNG layout)
        # Motor A (Left): PWMA=0, AIN1=1, AIN2=2
        # Motor B (Right): PWMB=5, BIN1=3, BIN2=4
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4
        
        self.log("Motor drivers initialized (TB6612FNG Waveshare)")
        
        # Initialize ultrasonic sensor GPIO
        if not GPIOD_AVAILABLE:
            raise RuntimeError("gpiod not available. Cannot initialize sensor.")
        
        try:
            # Use gpiod 2.x API
            from gpiod.line import Bias, Edge
            
            # Configure trigger pin (output)
            trigger_settings = gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=Value.INACTIVE
            )
            
            # Configure echo pin (input) - no bias, let sensor drive
            echo_settings = gpiod.LineSettings(
                direction=Direction.INPUT
            )
            
            # Request lines
            self.gpio_request = gpiod.request_lines(
                "/dev/gpiochip4",
                consumer="motor-sensor",
                config={
                    SENSOR_TRIGGER_PIN: trigger_settings,
                    SENSOR_ECHO_PIN: echo_settings
                }
            )
            
            self.log(f"Ultrasonic sensor initialized (GPIO {SENSOR_TRIGGER_PIN}/{SENSOR_ECHO_PIN})")
            
        except Exception as e:
            self.log(f"ERROR: Failed to initialize sensor GPIO: {e}")
            raise
        
        # Initial stop
        self.stop()
        self.log("Motor Controller ready")
    
    
    def log(self, message: str, level: str = "INFO"):
        """Write to log file and stdout"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line, flush=True)
        
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_line + '\n')
        except Exception:
            pass  # Ignore logging errors
    
    
    def read_distance(self) -> float:
        """
        Read distance from HC-SR04-P ultrasonic sensor
        Returns distance in centimeters, or MAX_SENSOR_DISTANCE if out of range
        """
        try:
            # Send 10us trigger pulse with proper settle time
            self.gpio_request.set_value(SENSOR_TRIGGER_PIN, Value.INACTIVE)
            time.sleep(0.002)  # 2ms settle time (important!)
            self.gpio_request.set_value(SENSOR_TRIGGER_PIN, Value.ACTIVE)
            time.sleep(0.00001)   # 10us trigger
            self.gpio_request.set_value(SENSOR_TRIGGER_PIN, Value.INACTIVE)
            
            # Wait for echo to go high (timeout 100ms)
            timeout = time.time() + 0.1
            pulse_start = time.time()
            while self.gpio_request.get_value(SENSOR_ECHO_PIN) == Value.INACTIVE:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return MAX_SENSOR_DISTANCE
            
            # Measure echo pulse duration
            pulse_start = time.time()
            
            # Wait for echo to go low (timeout 30ms for max range)
            timeout = time.time() + 0.03
            while self.gpio_request.get_value(SENSOR_ECHO_PIN) == Value.ACTIVE:
                if time.time() > timeout:
                    return MAX_SENSOR_DISTANCE
            
            pulse_end = time.time()
            
            # Calculate distance (speed of sound = 34300 cm/s)
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            # Clamp to sensor range (2cm - 400cm)
            if distance < 2:
                return 2
            elif distance > MAX_SENSOR_DISTANCE:
                return MAX_SENSOR_DISTANCE
            
            return distance
            
        except Exception as e:
            self.log(f"Sensor read error: {e}", "WARNING")
            return MAX_SENSOR_DISTANCE
    
    
    def obstacle_monitoring_loop(self):
        """Background thread to continuously monitor for obstacles"""
        self.log("Obstacle monitoring started")
        self.last_turn_was_left = False  # Alternate turn direction to avoid loops
        
        while self.running:
            try:
                distance = self.read_distance()
                
                if distance < OBSTACLE_DISTANCE_CM:
                    if not self.obstacle_detected:
                        self.log(f"OBSTACLE DETECTED at {distance:.1f}cm", "WARNING")
                        self.obstacle_detected = True
                        
                        # Only perform avoidance if we were moving forward
                        if self.is_moving_forward and not self.avoidance_in_progress:
                            self.perform_obstacle_avoidance()
                        else:
                            # Just stop if not moving forward or already avoiding
                            self.stop()
                else:
                    if self.obstacle_detected:
                        self.log(f"Obstacle cleared ({distance:.1f}cm)")
                        self.obstacle_detected = False
                
                time.sleep(SENSOR_READ_INTERVAL)
                
            except Exception as e:
                self.log(f"Obstacle monitoring error: {e}", "ERROR")
                time.sleep(1)
        
        self.log("Obstacle monitoring stopped")
    
    
    def perform_obstacle_avoidance(self):
        """
        Execute obstacle avoidance routine based on configured behavior mode.
        Called when obstacle detected while moving forward.
        """
        self.avoidance_in_progress = True
        self.is_moving_forward = False
        
        try:
            # First, always stop motors (but preserve explore_mode)
            self._stop_motors()
            self.log(f"Avoidance: behavior={self.obstacle_behavior}")
            
            if self.obstacle_behavior == OBSTACLE_BEHAVIOR_STOP:
                # Just stop - no further action
                self.log("Avoidance: stop only")
            
            elif self.obstacle_behavior == OBSTACLE_BEHAVIOR_BACKUP:
                # Back up only
                self.log(f"Avoidance: backing up for {BACKUP_DURATION}s")
                time.sleep(0.2)  # Brief pause before reversing
                self._raw_move_backward(BACKUP_SPEED, BACKUP_DURATION)
            
            elif self.obstacle_behavior == OBSTACLE_BEHAVIOR_AVOID:
                # Full avoidance: back up + turn
                self.log(f"Avoidance: backing up for {BACKUP_DURATION}s")
                time.sleep(0.2)  # Brief pause before reversing
                self._raw_move_backward(BACKUP_SPEED, BACKUP_DURATION)
                
                # Alternate turn direction to avoid getting stuck
                if self.last_turn_was_left:
                    self.log(f"Avoidance: turning RIGHT for {AVOID_TURN_DURATION}s")
                    self._raw_turn_right(AVOID_TURN_SPEED, AVOID_TURN_DURATION)
                    self.last_turn_was_left = False
                else:
                    self.log(f"Avoidance: turning LEFT for {AVOID_TURN_DURATION}s")
                    self._raw_turn_left(AVOID_TURN_SPEED, AVOID_TURN_DURATION)
                    self.last_turn_was_left = True
                
                self.log("Avoidance complete")
        
        except Exception as e:
            self.log(f"Avoidance error: {e}", "ERROR")
            self._stop_motors()
        
        finally:
            self.avoidance_in_progress = False
            
            # EXPLORE MODE: Auto-resume forward movement after avoidance
            if self.explore_mode and self.running:
                self.log("Explore mode: resuming forward movement")
                time.sleep(0.5)  # Brief pause to let sensor settle
                # Use raw forward that bypasses obstacle check (we just avoided, so try moving)
                self._raw_move_forward_continuous(speed=50)
    
    
    def _raw_move_backward(self, speed: int, duration: float):
        """Internal: move backward without obstacle checks (for avoidance)"""
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'backward')
        self.set_motor_direction(1, 'backward')
        time.sleep(duration)
        self._stop_motors()  # Don't clear explore_mode
    
    
    def _raw_move_forward_continuous(self, speed: int):
        """Internal: start continuous forward without obstacle check (for explore resume)"""
        self.is_moving_forward = True
        self.log(f"FORWARD at {speed}% (explore resume)")
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'forward')
        self.set_motor_direction(1, 'forward')
    
    
    def _raw_turn_left(self, speed: int, duration: float):
        """Internal: turn left without clearing explore_mode (for avoidance)
        MECANUM TANK STEERING: Left backward, Right forward - rotates in place
        """
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'backward')  # Left backward
        self.set_motor_direction(1, 'forward')   # Right forward
        time.sleep(duration)
        self._stop_motors()
    
    
    def _raw_turn_right(self, speed: int, duration: float):
        """Internal: turn right without clearing explore_mode (for avoidance)
        MECANUM TANK STEERING: Left forward, Right backward - rotates in place
        """
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'forward')   # Left forward
        self.set_motor_direction(1, 'backward')  # Right backward
        time.sleep(duration)
        self._stop_motors()
    
    
    def set_motor_direction(self, motor, direction):
        """
        Set motor direction using Waveshare TB6612FNG logic
        motor: 0=left(A), 1=right(B)
        direction: 'forward', 'backward', or 'stop'
        """
        if motor == 0:  # Motor A (left)
            if direction == 'forward':
                self.pca.setLevel(self.AIN1, 0)
                self.pca.setLevel(self.AIN2, 1)
            elif direction == 'backward':
                self.pca.setLevel(self.AIN1, 1)
                self.pca.setLevel(self.AIN2, 0)
            else:  # stop
                self.pca.setLevel(self.AIN1, 0)
                self.pca.setLevel(self.AIN2, 0)
        else:  # Motor B (right)
            if direction == 'forward':
                self.pca.setLevel(self.BIN1, 0)
                self.pca.setLevel(self.BIN2, 1)
            elif direction == 'backward':
                self.pca.setLevel(self.BIN1, 1)
                self.pca.setLevel(self.BIN2, 0)
            else:  # stop
                self.pca.setLevel(self.BIN1, 0)
                self.pca.setLevel(self.BIN2, 0)
    
    def set_motor_speed(self, motor, speed):
        """
        Set motor speed using PWM duty cycle (0-100%)
        motor: 0=left(A), 1=right(B)
        speed: 0-100
        """
        if speed > 100:
            speed = 100
        if speed < 0:
            speed = 0
        
        if motor == 0:  # Motor A
            self.pca.setDutycycle(self.PWMA, speed)
        else:  # Motor B
            self.pca.setDutycycle(self.PWMB, speed)
    
    def _stop_motors(self):
        """Internal: Stop motors without clearing explore_mode (for avoidance routines)"""
        try:
            self.set_motor_speed(0, 0)  # Left
            self.set_motor_speed(1, 0)  # Right
            self.set_motor_direction(0, 'stop')
            self.set_motor_direction(1, 'stop')
        except Exception as e:
            self.log(f"Stop motors error: {e}", "ERROR")
    
    def stop(self):
        """Stop all motors immediately (clears explore mode)"""
        self.log("STOP")
        self.explore_mode = False  # Clear explore mode on explicit stop
        self.is_moving_forward = False  # Clear forward movement flag
        self._stop_motors()
    
    
    def move_forward(self, speed: int = None, duration: float = 0):
        """
        Move forward at specified speed (0-100%)
        If duration > 0, move for that many seconds then stop
        If duration == 0, continue moving until stop() is called
        """
        if self.obstacle_detected:
            self.log("Cannot move forward: obstacle detected", "WARNING")
            return False
        
        speed = speed or self.current_speed
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))
        
        # Set flag BEFORE starting movement (for obstacle detection)
        self.is_moving_forward = True
        
        self.log(f"FORWARD at {speed}%")
        self.set_motor_speed(0, speed)  # Left speed first
        self.set_motor_speed(1, speed)  # Right speed first
        self.set_motor_direction(0, 'forward')  # Left direction
        self.set_motor_direction(1, 'forward')  # Right direction
        
        if duration > 0:
            time.sleep(duration)
            self.stop()  # This will clear is_moving_forward
        
        return True
    
    
    def move_backward(self, speed: int = None, duration: float = 0):
        """
        Move backward at specified speed (0-100%)
        If duration > 0, move for that many seconds then stop
        """
        speed = speed or self.current_speed
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))
        
        self.log(f"BACKWARD at {speed}%")
        self.set_motor_speed(0, speed)  # Left speed first
        self.set_motor_speed(1, speed)  # Right speed first
        self.set_motor_direction(0, 'backward')  # Left direction
        self.set_motor_direction(1, 'backward')  # Right direction
        
        if duration > 0:
            time.sleep(duration)
            self.stop()
        
        return True
    
    
    def turn_left(self, speed: int = None, angle: float = 90):
        """
        Turn left using MECANUM TANK STEERING
        Left side backward, Right side forward - rotates in place
        Mecanum wheels have angled rollers for smooth rotation
        """
        speed = speed or 100  # Full power for Mecanum
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))
        
        # Mecanum wheels: 5s per 90°
        duration = (angle / 90.0) * 5.0
        
        self.log(f"MECANUM TURN LEFT ~{angle}° at {speed}% duration:{duration:.1f}s")
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'backward')  # Left backward
        self.set_motor_direction(1, 'forward')   # Right forward
        
        time.sleep(duration)
        self.stop()
        
        return True
    
    
    def turn_right(self, speed: int = None, angle: float = 90):
        """
        Turn right using MECANUM TANK STEERING
        Left side forward, Right side backward - rotates in place
        Mecanum wheels have angled rollers for smooth rotation
        """
        speed = speed or 100  # Full power for Mecanum
        speed = max(MIN_SPEED, min(MAX_SPEED, speed))
        
        # Mecanum wheels: 5s per 90°
        duration = (angle / 90.0) * 5.0
        
        self.log(f"MECANUM TURN RIGHT ~{angle}° at {speed}% duration:{duration:.1f}s")
        self.set_motor_speed(0, speed)
        self.set_motor_speed(1, speed)
        self.set_motor_direction(0, 'forward')   # Left forward
        self.set_motor_direction(1, 'backward')  # Right backward
        
        time.sleep(duration)
        self.stop()
        
        return True
    
    
    def test_motors(self):
        """Test all motor movements"""
        self.log("=== MOTOR TEST SEQUENCE ===")
        
        self.log("Test 1: Forward 2 seconds")
        self.move_forward(speed=50, duration=2)
        time.sleep(1)
        
        self.log("Test 2: Backward 2 seconds")
        self.move_backward(speed=50, duration=2)
        time.sleep(1)
        
        self.log("Test 3: Turn left 90°")
        self.turn_left(speed=50, angle=90)
        time.sleep(1)
        
        self.log("Test 4: Turn right 90°")
        self.turn_right(speed=50, angle=90)
        time.sleep(1)
        
        self.log("=== TEST COMPLETE ===")
    
    
    def handle_command(self, command_str: str) -> Dict:
        """
        Handle incoming socket commands (JSON format)
        Returns response dictionary
        """
        try:
            command = json.loads(command_str)
            action = command.get("action", "")
            
            if action == "move_forward":
                speed = command.get("speed", self.current_speed)
                duration = command.get("duration", 0)
                success = self.move_forward(speed, duration)
                return {"status": "ok" if success else "blocked", "action": action}
            
            elif action == "move_backward":
                speed = command.get("speed", self.current_speed)
                duration = command.get("duration", 0)
                success = self.move_backward(speed, duration)
                return {"status": "ok", "action": action}
            
            elif action == "turn_left":
                speed = command.get("speed", self.current_speed)
                angle = command.get("angle", 90)
                success = self.turn_left(speed, angle)
                return {"status": "ok", "action": action}
            
            elif action == "turn_right":
                speed = command.get("speed", self.current_speed)
                angle = command.get("angle", 90)
                success = self.turn_right(speed, angle)
                return {"status": "ok", "action": action}
            
            elif action == "stop":
                self.stop()
                return {"status": "ok", "action": "stop"}
            
            elif action == "get_distance":
                distance = self.read_distance()
                return {"status": "ok", "distance_cm": distance}
            
            elif action == "test_motors":
                self.test_motors()
                return {"status": "ok", "action": "test"}
            
            elif action == "set_obstacle_behavior":
                # Set obstacle avoidance behavior mode
                behavior = command.get("behavior", "")
                valid_behaviors = [OBSTACLE_BEHAVIOR_STOP, OBSTACLE_BEHAVIOR_BACKUP, OBSTACLE_BEHAVIOR_AVOID]
                if behavior in valid_behaviors:
                    self.obstacle_behavior = behavior
                    self.log(f"Obstacle behavior set to: {behavior}")
                    return {"status": "ok", "behavior": behavior}
                else:
                    return {"status": "error", "message": f"Invalid behavior. Use: {valid_behaviors}"}
            
            elif action == "get_obstacle_behavior":
                return {"status": "ok", "behavior": self.obstacle_behavior}
            
            elif action == "explore_start":
                # Start exploration mode: continuous forward with auto-resume after avoidance
                if self.obstacle_detected:
                    return {"status": "blocked", "message": "Cannot start exploring - obstacle detected"}
                
                self.obstacle_behavior = OBSTACLE_BEHAVIOR_AVOID  # Ensure full avoidance
                self.explore_mode = True
                self.log("EXPLORE MODE: Started")
                self.move_forward(speed=50, duration=0)  # Start continuous forward
                return {"status": "ok", "action": "explore_start", "message": "Exploration started"}
            
            elif action == "explore_stop":
                # Stop exploration mode
                self.explore_mode = False
                self.stop()
                self.log("EXPLORE MODE: Stopped")
                return {"status": "ok", "action": "explore_stop", "message": "Exploration stopped"}
            
            elif action == "get_status":
                # Get full motor controller status
                distance = self.read_distance()
                return {
                    "status": "ok",
                    "distance_cm": distance,
                    "obstacle_detected": self.obstacle_detected,
                    "obstacle_behavior": self.obstacle_behavior,
                    "is_moving_forward": self.is_moving_forward,
                    "avoidance_in_progress": self.avoidance_in_progress,
                    "explore_mode": self.explore_mode
                }
            
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    
    def socket_handler(self, conn):
        """Handle individual socket connection"""
        try:
            data = conn.recv(1024).decode('utf-8')
            if data:
                response = self.handle_command(data)
                conn.sendall(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.log(f"Socket handler error: {e}", "ERROR")
        finally:
            conn.close()
    
    
    def socket_server_loop(self):
        """Background thread for Unix socket server"""
        
        # Remove old socket if exists
        if os.path.exists(MOTOR_SOCKET):
            os.remove(MOTOR_SOCKET)
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(MOTOR_SOCKET)
        os.chmod(MOTOR_SOCKET, 0o666)  # Allow all users
        sock.listen(5)
        
        self.log(f"Socket server listening on {MOTOR_SOCKET}")
        
        while self.running:
            try:
                sock.settimeout(1.0)  # Check running flag periodically
                try:
                    conn, _ = sock.accept()
                    # Handle in separate thread to stay responsive
                    threading.Thread(
                        target=self.socket_handler,
                        args=(conn,),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
            except Exception as e:
                self.log(f"Socket server error: {e}", "ERROR")
                time.sleep(1)
        
        sock.close()
        if os.path.exists(MOTOR_SOCKET):
            os.remove(MOTOR_SOCKET)
        
        self.log("Socket server stopped")
    
    
    def start(self):
        """Start motor control service"""
        self.log("Starting motor control service...")
        self.running = True
        
        # Start obstacle monitoring thread
        self.sensor_thread = threading.Thread(
            target=self.obstacle_monitoring_loop,
            daemon=True,
            name="ObstacleMonitor"
        )
        self.sensor_thread.start()
        
        # Start socket server thread
        self.socket_thread = threading.Thread(
            target=self.socket_server_loop,
            daemon=True,
            name="SocketServer"
        )
        self.socket_thread.start()
        
        self.log("Motor control service started")
    
    
    def shutdown(self):
        """Shutdown motor control service"""
        self.log("Shutting down motor control service...")
        self.running = False
        
        # Stop motors
        self.stop()
        
        # Wait for threads
        if self.sensor_thread and self.sensor_thread.is_alive():
            self.sensor_thread.join(timeout=2)
        
        if self.socket_thread and self.socket_thread.is_alive():
            self.socket_thread.join(timeout=2)
        
        # Release GPIO
        try:
            if hasattr(self, 'gpio_request'):
                self.gpio_request.release()
        except Exception:
            pass
        
        # Release PCA9685
        try:
            if hasattr(self, 'pca'):
                self.pca.deinit()
        except Exception:
            pass
        
        self.log("Motor control service stopped")


# ============================================================================
# MAIN
# ============================================================================

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutdown signal received...")
    if 'controller' in globals():
        controller.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Demo mode: run test sequence
        controller = MotorController()
        print("\n=== MOTOR DEMO MODE ===\n")
        
        print("Testing sensor...")
        distance = controller.read_distance()
        print(f"Current distance: {distance:.1f}cm\n")
        
        input("Press Enter to run motor test sequence (or Ctrl+C to exit)...")
        controller.test_motors()
        
        controller.shutdown()
        
    else:
        # Service mode: run continuously
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║        SHATROX Motor Control Service                     ║")
        print("║        Waveshare Motor Driver HAT + HC-SR04-P            ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        
        controller = MotorController()
        controller.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            controller.shutdown()

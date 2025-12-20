#!/bin/bash
################################################################################
# Motor Control Test Utility
# Quick test script for Waveshare Motor Driver HAT and ultrasonic sensor
################################################################################

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        SHATROX Motor Control Test Utility                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Function to send command to motor controller
send_motor_command() {
    local command="$1"
    echo "$command" | nc -U /tmp/shatrox-motor-control.sock 2>/dev/null || \
        python3 -c "
import socket, json
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/tmp/shatrox-motor-control.sock')
sock.sendall('$command'.encode())
response = sock.recv(1024).decode()
sock.close()
print(response)
"
}

# Check if motor service is running
if ! systemctl is-active --quiet shatrox-motor-control; then
    echo "⚠️  Motor control service is not running"
    echo ""
    read -p "Start motor service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start shatrox-motor-control
        sleep 2
    else
        echo "❌ Cannot test without motor service running"
        exit 1
    fi
fi

echo "✓ Motor service is running"
echo ""

# Main menu
while true; do
    echo "──────────────────────────────────────────────────────────"
    echo "Motor Control Test Menu:"
    echo "──────────────────────────────────────────────────────────"
    echo "  1) Test distance sensor"
    echo "  2) Move forward (2 seconds)"
    echo "  3) Move backward (2 seconds)"
    echo "  4) Turn left (90°)"
    echo "  5) Turn right (90°)"
    echo "  6) STOP motors"
    echo "  7) Run full motor test sequence"
    echo "  8) Check I2C devices"
    echo "  9) View motor service logs"
    echo "  0) Exit"
    echo "──────────────────────────────────────────────────────────"
    read -p "Select option: " choice
    echo ""
    
    case $choice in
        1)
            echo "→ Reading distance sensor..."
            send_motor_command '{"action":"get_distance"}'
            echo ""
            ;;
        2)
            echo "→ Moving forward for 2 seconds..."
            send_motor_command '{"action":"move_forward","speed":50,"duration":2}'
            echo ""
            ;;
        3)
            echo "→ Moving backward for 2 seconds..."
            send_motor_command '{"action":"move_backward","speed":50,"duration":2}'
            echo ""
            ;;
        4)
            echo "→ Turning left 90°..."
            send_motor_command '{"action":"turn_left","speed":50,"angle":90}'
            echo ""
            ;;
        5)
            echo "→ Turning right 90°..."
            send_motor_command '{"action":"turn_right","speed":50,"angle":90}'
            echo ""
            ;;
        6)
            echo "→ STOPPING all motors..."
            send_motor_command '{"action":"stop"}'
            echo ""
            ;;
        7)
            echo "→ Running full test sequence..."
            send_motor_command '{"action":"test_motors"}'
            echo "✓ Test complete (check motor service logs for details)"
            echo ""
            ;;
        8)
            echo "→ Scanning I2C bus..."
            i2cdetect -y 1
            echo ""
            echo "Motor HAT (PCA9685) should appear at address 0x40"
            echo ""
            ;;
        9)
            echo "→ Last 30 lines of motor service log:"
            echo ""
            journalctl -u shatrox-motor-control -n 30 --no-pager
            echo ""
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "❌ Invalid option"
            echo ""
            ;;
    esac
done

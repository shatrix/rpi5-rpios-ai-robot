#!/bin/bash
################################################################################
# 11: Motor Control Setup
# Install Waveshare Motor Driver HAT and ultrasonic sensor support
################################################################################

set -e

echo "=== Setting up Motor Control ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ============================================================================
# Verify I2C is enabled
# ============================================================================

echo "→ Verifying I2C interface..."

if ! grep -q "dtparam=i2c_arm=on" /boot/firmware/config.txt; then
    echo "⚠️  I2C not enabled in config.txt"
    echo "   This should have been configured in step 02-hardware-config.sh"
    echo "   Re-run: sudo ./setup.sh --step 02"
    exit 1
fi

echo "✓ I2C is enabled"

# ============================================================================
# Test I2C bus
# ============================================================================

echo "→ Testing I2C bus..."

if ! command -v i2cdetect &> /dev/null; then
    echo "❌ ERROR: i2cdetect not found. Install i2c-tools first."
    exit 1
fi

# Check if I2C bus 1 is available
if ! ls /dev/i2c-1 &> /dev/null; then
    echo "⚠️  /dev/i2c-1 not found. I2C may not be loaded."
    echo "   Loading i2c-dev kernel module..."
    modprobe i2c-dev || true
    
    if ! ls /dev/i2c-1 &> /dev/null; then
        echo "❌ ERROR: I2C bus not available. Reboot may be required."
        exit 1
    fi
fi

# Ensure i2c-dev loads on boot
if [ ! -f /etc/modules-load.d/i2c.conf ]; then
    echo "i2c-dev" > /etc/modules-load.d/i2c.conf
    echo "✓ Added i2c-dev to auto-load on boot"
fi

echo "✓ I2C bus available"

# Scan for devices (Motor HAT should appear at 0x40 or configured address)
echo ""
echo "→ Scanning I2C bus for devices..."
i2cdetect -y 1 || echo "⚠️  Note: Motor HAT may not be detected until Python libraries are installed"
echo ""

# ============================================================================
# Install Python motor control libraries
# ============================================================================

echo "→ Installing motor control Python libraries..."

# Install from requirements.txt (which includes motor libraries)
cd "$SCRIPT_DIR/python"

if ! command -v pip3 &> /dev/null; then
    echo "❌ ERROR: pip3 not found"
    exit 1
fi

# Install motor-specific dependencies
echo "  Installing motor control Python libraries..."
pip3 install --break-system-packages \
    adafruit-blinka>=8.0.0 \
    adafruit-circuitpython-pca9685>=3.4.0 \
    adafruit-circuitpython-motor>=3.4.0 \
    adafruit-extended-bus>=1.0.0

echo "✓ Motor control libraries installed"

# ============================================================================
# Verify motor controller script
# ============================================================================

echo "→ Verifying motor controller..."

if [ ! -f "$SCRIPT_DIR/python/motor_controller.py" ]; then
    echo "❌ ERROR: motor_controller.py not found"
    exit 1
fi

chmod +x "$SCRIPT_DIR/python/motor_controller.py"

echo "✓ Motor controller script ready"

# ============================================================================
# Test ultrasonic sensor GPIO
# ============================================================================

echo "→ Verifying ultrasonic sensor GPIO pins..."

# Check that GPIO 22 and 23 are available (not used by other services)
if command -v gpioinfo &> /dev/null; then
    echo "✓ Sensor GPIO pins: GPIO 22 (trigger) / GPIO 23 (echo)"
else
    echo "⚠️  gpioinfo not available, skipping GPIO verification"
fi

# ============================================================================
# Create motor configuration directory
# ============================================================================

echo "→ Creating motor control directories..."

mkdir -p /etc/motor-control
mkdir -p /var/log

# Create simple config file
cat > /etc/motor-control/config.ini << 'EOF'
[motor]
# Motor speed limits (0-100%)
default_speed = 50
max_speed = 100

[sensor]
# Ultrasonic sensor GPIO pins (HC-SR04-P)
trigger_pin = 22
echo_pin = 23

# Obstacle detection distance (cm)
obstacle_distance = 20

# Sensor read interval (seconds)
read_interval = 0.1

[safety]
# Enable obstacle detection
enable_obstacle_detection = true

# Auto-stop on obstacle
auto_stop = true
EOF

chmod 644 /etc/motor-control/config.ini

echo "✓ Configuration created: /etc/motor-control/config.ini"

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                Motor Control Setup Complete               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  - I2C Bus: /dev/i2c-1 (PCA9685 at 0x40)"
echo "  - Sensor Trigger: GPIO 22"
echo "  - Sensor Echo: GPIO 23"
echo "  - Obstacle Distance: 20cm"
echo ""
echo "Next steps:"
echo "  1. Complete setup: sudo ./setup.sh"
echo "  2. Reboot to load I2C modules: sudo reboot"
echo "  3. Test motors: sudo bash scripts-helpers/test-motors.sh"
echo ""

exit 0

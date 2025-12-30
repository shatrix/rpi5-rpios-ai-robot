# Hardware Connections Guide

Complete hardware wiring reference for the RPi5 AI Robot project.

---

## Quick Reference Summary

| Component | Interface | Connection |
|-----------|-----------|------------|
| **Display** | SPI | GPIO Header (SPI0) |
| **Camera** | CSI | Camera Port (CSI-2) |
| **Microphone** | USB | USB Port |
| **Speakers** | USB | USB Port (via USB Audio) |
| **Buttons (5x)** | GPIO | GPIO 5, 6, 13, 19, 26 |
| **Motor HAT** | I2C | GPIO 2 (SDA), GPIO 3 (SCL) |
| **Ultrasonic Sensors (2x)** | GPIO | Left: GPIO 22/23, Right: GPIO 16/12 |
| **Battery** | Power | Motor HAT Terminal |
| **Active Cooler** | PWM | GPIO Header (5V/GND/PWM) |

---

## Detailed Connections

### 1. Display - 3.5" SPI Touch Screen (piscreen)

**Interface:** SPI0 + GPIO

| Display Pin | RPi5 Pin | GPIO/Function |
|-------------|----------|---------------|
| VCC | Pin 2 | 5V Power |
| GND | Pin 6 | Ground |
| MISO | Pin 21 | GPIO 9 (SPI0_MISO) |
| MOSI | Pin 19 | GPIO 10 (SPI0_MOSI) |
| SCLK | Pin 23 | GPIO 11 (SPI0_SCLK) |
| CS | Pin 24 | GPIO 8 (SPI0_CE0) |
| DC | Pin 18 | GPIO 24 |
| RST | Pin 22 | GPIO 25 |
| LED | Pin 12 | GPIO 18 (PWM) |
| TOUCH_CS | Pin 26 | GPIO 7 (SPI0_CE1) |
| TOUCH_IRQ | Pin 11 | GPIO 17 |

> [!NOTE]
> The display uses the `piscreen` overlay configured in `/boot/firmware/config.txt`:
> ```
> dtoverlay=piscreen,speed=18000000,drm,rotate=0
> dtparam=spi=on
> ```

> [!CAUTION]
> **Piscreen GPIO Conflicts - AVOID THESE PINS:**
> The piscreen overlay and ADS7846 touch controller cause conflicts with certain GPIO pins. Using these pins for other purposes may cause phantom touch events or display issues:
> - **GPIO 4 (Pin 7)** - Causes phantom touch events when used
> - **GPIO 17 (Pin 11)** - Reserved for Touch IRQ
> - **GPIO 7 (Pin 26)** - Reserved for Touch CS (SPI0_CE1)
> - **GPIO 8-11, 24, 25** - Reserved for display SPI and control
> 
> **Safe GPIO pins for sensors/peripherals:** GPIO 5, 6, 12, 13, 16, 19, 20, 21, 22, 23, 26, 27

---

### 2. Camera - Raspberry Pi Camera Module 3 (IMX708)

**Interface:** CSI-2 (Camera Serial Interface)

| Camera | RPi5 Connection |
|--------|-----------------|
| FFC Cable (22-pin) | CAM0 or CAM1 Port |

> [!TIP]
> The CSI connector is a zero-insertion-force (ZIF) socket. Gently lift the plastic latch, insert the flat ribbon cable with silver contacts facing the PCB, then close the latch.

**Configuration:**
```
camera_auto_detect=1
```

---

### 3. Microphone - USB Microphone

**Interface:** USB

| Connection | RPi5 Port |
|------------|-----------|
| USB Plug | Any USB-A Port |

> [!NOTE]
> The system auto-detects USB audio devices. No additional configuration needed.

---

### 4. Speakers - USB Audio Speakers

**Interface:** USB (Audio)

| Connection | Details |
|------------|---------|
| USB Plug | Any USB-A Port |
| Audio Output | Speakers integrated or 3.5mm jack on USB adapter |

> [!IMPORTANT]
> Both microphone and speakers often use a single USB audio adapter with combined input/output.

**ALSA Configuration:** `/etc/asound.conf`

---

### 5. Buttons - GPIO Push Buttons (5 Active)

**Interface:** GPIO Digital Input with internal pull-up

| Button | GPIO Pin | Physical Pin | Function |
|--------|----------|--------------|----------|
| **K1** | GPIO 5 | Pin 29 | Voice Chat (Hold to Speak) |
| **K2** | GPIO 6 | Pin 31 | Play Greeting |
| **K3** | GPIO 13 | Pin 33 | Camera Vision Capture |
| **K4** | GPIO 19 | Pin 35 | Fun Sound |
| **K8** | GPIO 26 | Pin 37 | System Shutdown |

**Wiring (per button):**
```
GPIO Pin ──┬── Button ── GND
           │
        (internal pull-up enabled)
```

> [!NOTE]
> Uses GPIO chip `/dev/gpiochip4` on Raspberry Pi OS. Internal pull-up resistors are enabled via software.

---

### 6. Motor HAT - Waveshare Motor Driver HAT

**Interface:** I2C (PCA9685) + TB6612FNG H-Bridge

| HAT Pin | RPi5 Pin | GPIO/Function |
|---------|----------|---------------|
| VCC (Logic) | Pin 1 | 3.3V |
| GND | Pin 9 | Ground |
| SDA | Pin 3 | GPIO 2 (I2C1_SDA) |
| SCL | Pin 5 | GPIO 3 (I2C1_SCL) |

**I2C Address:** `0x40`

**Motor Channel Mapping (PCA9685):**

| Channel | Function | Description |
|---------|----------|-------------|
| CH0 | PWMA | Left Motors Speed |
| CH1 | AIN1 | Left Motors Direction 1 |
| CH2 | AIN2 | Left Motors Direction 2 |
| CH3 | BIN1 | Right Motors Direction 1 |
| CH4 | BIN2 | Right Motors Direction 2 |
| CH5 | PWMB | Right Motors Speed |

> [!IMPORTANT]
> The Motor HAT sits on top of the RPi5 as a **stacking HAT**. It connects to the full 40-pin GPIO header.

---

### 7. DC Motors (4x) with 48mm Mecanum Wheels

**Interface:** Connected to Motor HAT terminals

| Motor Position | HAT Terminal | Connection |
|----------------|--------------|------------|
| Left Front | MA+ / MA- | Motor A channel |
| Left Rear | MA+ / MA- | Motor A channel (parallel) |
| Right Front | MB+ / MB- | Motor B channel |
| Right Rear | MB+ / MB- | Motor B channel (parallel) |

> [!TIP]
> Left motors are wired in parallel to Channel A. Right motors are wired in parallel to Channel B. This creates tank-style differential drive with Mecanum wheels for smooth in-place rotation.

---

### 8. Ultrasonic Sensors - HC-SR04-P (3.3V Compatible) x2

**Interface:** GPIO Digital I/O

The robot uses **two ultrasonic sensors** for improved obstacle avoidance: one mounted on the left-front and one on the right-front.

#### Left Sensor (mounted left-front)
| Sensor Pin | RPi5 Pin | GPIO |
|------------|----------|------|
| VCC | Pin 1 or 17 | 3.3V (shared) |
| GND | Pin 14 | Ground (shared) |
| Trigger | Pin 15 | GPIO 22 |
| Echo | Pin 16 | GPIO 23 |

#### Right Sensor (mounted right-front)
| Sensor Pin | RPi5 Pin | GPIO |
|------------|----------|------|
| VCC | Pin 1 or 17 | 3.3V (shared) |
| GND | Pin 14 | Ground (shared) |
| Trigger | Pin 36 | GPIO 16 |
| Echo | Pin 32 | GPIO 12 |

> [!CAUTION]
> Use the **HC-SR04-P** (3.3V version), NOT the standard HC-SR04 (5V). The 5V version can damage Raspberry Pi GPIO pins!

**Range:** 2cm - 400cm  
**Safety Distance:** 20cm (configurable)  
**Smart Avoidance:** Left obstacle → turn right, Right obstacle → turn left

---

### 9. Battery - 7.2V Rechargeable Pack

**Interface:** Power terminals on Motor HAT

| Battery Terminal | HAT Connection |
|------------------|----------------|
| Positive (+) | VIN+ (Motor Power) |
| Negative (-) | VIN- (Motor Ground) |

> [!IMPORTANT]
> - Battery powers **only the motors** (via Motor HAT)  
> - RPi5 requires separate power (USB-C)  
> - Recommended: 7.2V NiMH or 2S LiPo (7.4V)

---

### 10. Active Cooler (Official RPi5)

**Interface:** GPIO Header + Dedicated connector

| Cooler | RPi5 Connection |
|--------|-----------------|
| 4-pin Fan | Dedicated fan header on RPi5 |

**Fan Temperature Thresholds** (configured in `/boot/firmware/config.txt`):
- Level 0: 40°C
- Level 1: 60°C
- Level 2: 70°C

---

## Visual Wiring Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RASPBERRY PI 5 GPIO HEADER                          │
│                              (Top View)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    3.3V (1) ●──[Sensor VCC]──●                 ● (2) 5V ──[Display VCC]     │
│   SDA2 (3) ●──[I2C Motor HAT]                  ● (4) 5V                     │
│   SCL3 (5) ●──[I2C Motor HAT]                  ● (6) GND ──[Display GND]    │
│   GPIO4 (7) ●                                  ● (8)                        │
│     GND (9) ●──[Motor HAT GND]                 ●(10)                        │
│  GPIO17(11) ●──[Touch IRQ]                     ●(12) GPIO18 ──[Display LED] │
│  GPIO27(13) ●                                  ●(14) GND ──[Sensor GND]     │
│  GPIO22(15) ●──[Sensor TRIGGER]                ●(16) GPIO23 ──[Sensor ECHO] │
│    3.3V(17) ●                                  ●(18) GPIO24 ──[Display DC]  │
│  GPIO10(19) ●──[SPI MOSI]                      ●(20) GND                    │
│   GPIO9(21) ●──[SPI MISO]                      ●(22) GPIO25 ──[Display RST] │
│  GPIO11(23) ●──[SPI SCLK]                      ●(24) GPIO8 ──[Display CS]   │
│     GND(25) ●                                  ●(26) GPIO7 ──[Touch CS]     │
│   GPIO0(27) ●                                  ●(28)                        │
│   GPIO5(29) ●──[Button K1]                     ●(30) GND                    │
│   GPIO6(31) ●──[Button K2]                     ●(32)                        │
│  GPIO13(33) ●──[Button K3]                     ●(34) GND                    │
│  GPIO19(35) ●──[Button K4]                     ●(36)                        │
│  GPIO26(37) ●──[Button K8]                     ●(38)                        │
│     GND(39) ●                                  ●(40)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        ┌───────────────────┐                                │
│                        │   3.5" DISPLAY    │                                │
│                        │    (SPI + GPIO)   │                                │
│                        └─────────┬─────────┘                                │
│                                  │ SPI0                                     │
│                                  ▼                                          │
│  ┌──────────────┐      ┌─────────────────────┐      ┌──────────────┐        │
│  │ USB AUDIO    │      │                     │      │   CAMERA     │        │
│  │ ┌─────────┐  │      │    RASPBERRY PI 5   │      │   MODULE 3   │        │
│  │ │   MIC   │  │◄────►│                     │◄─────│   (CSI-2)    │        │
│  │ └─────────┘  │ USB  │   ┌─────────────┐   │ CSI  └──────────────┘        │
│  │ ┌─────────┐  │      │   │   SoC +     │   │                              │
│  │ │ SPEAKER │  │      │   │   4GB RAM   │   │                              │
│  │ └─────────┘  │      │   └─────────────┘   │                              │
│  └──────────────┘      │         │           │                              │
│                        │         │GPIO       │                              │
│                        └─────────┼───────────┘                              │
│                                  │                                          │
│           ┌──────────────────────┼──────────────────────┐                   │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐            │
│  │  MOTOR HAT      │   │ BUTTONS (5x)    │   │ HC-SR04-P       │            │
│  │  (I2C 0x40)     │   │ K1:GPIO5        │   │ ULTRASONIC      │            │
│  │                 │   │ K2:GPIO6        │   │                 │            │
│  │ ┌────┐ ┌────┐   │   │ K3:GPIO13       │   │ TRIG: GPIO22    │            │
│  │ │ MA │ │ MB │   │   │ K4:GPIO19       │   │ ECHO: GPIO23    │            │
│  │ └──┬─┘ └─┬──┘   │   │ K8:GPIO26       │   │                 │            │
│  └────┼─────┼──────┘   └─────────────────┘   └─────────────────┘            │
│       │     │                                                               │
│       ▼     ▼                                                               │
│  ┌─────────────────┐                                                        │
│  │  4x DC MOTORS   │◄────── 7.2V BATTERY                                    │
│  │ (2 Left/2 Right)│                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GPIO Pin Summary Table

| Physical Pin | GPIO | Function | Used By |
|--------------|------|----------|---------|
| 1 | 3.3V | Power | HC-SR04-P VCC (shared) |
| 2 | 5V | Power | Display VCC |
| 3 | GPIO 2 | I2C1 SDA | Motor HAT |
| 5 | GPIO 3 | I2C1 SCL | Motor HAT |
| 6 | GND | Ground | Display |
| 7 | GPIO 4 | ⚠️ AVOID | Piscreen conflict |
| 9 | GND | Ground | Motor HAT |
| 11 | GPIO 17 | Input | Touch IRQ (piscreen) |
| 12 | GPIO 18 | PWM | Display LED |
| 14 | GND | Ground | HC-SR04-P (shared) |
| 15 | GPIO 22 | Output | HC-SR04-P Left Trigger |
| 16 | GPIO 23 | Input | HC-SR04-P Left Echo |
| 18 | GPIO 24 | Output | Display DC |
| 19 | GPIO 10 | SPI0 MOSI | Display |
| 21 | GPIO 9 | SPI0 MISO | Display |
| 22 | GPIO 25 | Output | Display RST |
| 23 | GPIO 11 | SPI0 SCLK | Display |
| 24 | GPIO 8 | SPI0 CE0 | Display CS |
| 26 | GPIO 7 | SPI0 CE1 | Touch CS (piscreen) |
| 29 | GPIO 5 | Input | Button K1 |
| 31 | GPIO 6 | Input | Button K2 |
| 32 | GPIO 12 | Input | HC-SR04-P Right Echo |
| 33 | GPIO 13 | Input | Button K3 |
| 35 | GPIO 19 | Input | Button K4 |
| 36 | GPIO 16 | Output | HC-SR04-P Right Trigger |
| 37 | GPIO 26 | Input | Button K8 |

---

## Parts List

| Component | Model/Specification | Quantity |
|-----------|---------------------|----------|
| Raspberry Pi 5 | 4GB RAM (minimum) | 1 |
| SPI Touch Display | 3.5" piscreen compatible | 1 |
| Camera Module | Raspberry Pi Camera Module 3 (IMX708) | 1 |
| USB Audio Adapter | With mic input + speaker output | 1 |
| Microphone | USB or via USB audio adapter | 1 |
| Speakers | Powered speakers (USB or 3.5mm) | 1 set |
| Motor Driver HAT | Waveshare (PCA9685 + TB6612FNG) | 1 |
| DC Motors | Geared motors with 48mm Mecanum wheels | 4 |
| Ultrasonic Sensor | HC-SR04-P (3.3V version) | 2 |
| Push Buttons | Momentary SPST | 5 |
| Battery Pack | 7.2V NiMH or 2S LiPo | 1 |
| Active Cooler | Official RPi5 Active Cooler | 1 |
| SD Card / NVMe | 16GB+ (32GB recommended) | 1 |
| Robot Chassis | Tank/differential drive compatible | 1 |
| Wires & Connectors | Various | As needed |

---

## Troubleshooting Connections

### I2C Issues (Motor HAT not detected)
```bash
# Check I2C is enabled and Motor HAT is visible at 0x40
sudo i2cdetect -y 1
```

### SPI Issues (Display not working)
```bash
# Verify SPI is enabled
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1
```

### GPIO Issues (Buttons not responding)
```bash
# Check GPIO chip (should be gpiochip4 on RPi OS)
gpioinfo gpiochip4
```

### Ultrasonic Sensor Issues
```bash
# Test sensor reading
sudo python3 -c "from motor_controller import MotorController; mc=MotorController(); print(f'Distance: {mc.read_distance():.1f}cm')"
```

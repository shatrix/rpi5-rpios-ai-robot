#!/bin/bash
################################################################################
# 01: System Dependencies
# Install all required system packages (bilingual support)
################################################################################

set -e

echo "=== Installing System Dependencies ==="

echo "→ Installing Python and development tools..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential

echo "→ Installing camera support (rpicam-apps)..."
# Raspberry Pi OS Trixie/Bookworm uses rpicam-apps (not libcamera-apps)
apt install -y \
    rpicam-apps \
    libcamera-tools

echo "→ Installing audio support (ALSA)..."
apt install -y \
    alsa-utils \
    libasound2-dev

echo "→ Installing Qt5 and QML for display..."
apt install -y \
    qtbase5-dev \
    qtdeclarative5-dev \
    qmlscene \
    qtquickcontrols2-5-dev \
    qml-module-qtquick2 \
    qml-module-qtquick-controls2 \
    qml-module-qtquick-window2 \
    libqt5gui5

echo "→ Installing utilities..."
apt install -y \
    curl \
    wget \
    git \
    unzip \
    systemd

echo "→ Installing bilingual TTS support..."
# espeak-ng-data for Piper (English)
# espeak-ng for Arabic TTS (ARM ONNX workaround)
apt install -y \
    espeak-ng-data \
    espeak-ng \
    libespeak-ng1

echo "→ Installing Arabic fonts..."
# Google Noto fonts for better Arabic rendering in QML
apt install -y \
    fonts-noto-core \
    fonts-noto-ui-core

echo "✓ All system dependencies installed (bilingual support enabled)"
exit 0

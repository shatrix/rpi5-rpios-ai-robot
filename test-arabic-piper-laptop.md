# Testing Piper Arabic Voice on Laptop

## Quick Test Instructions

### 1. Install Piper (Linux x86_64)

```bash
# Download Piper for x86_64
cd /tmp
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz
tar -xzf piper_linux_x86_64.tar.gz
cd piper
```

### 2. Download Arabic Voice

```bash
# Download the same Arabic voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx.json
```

### 3. Test Arabic Voice

```bash
# Test with Arabic text
echo "مرحباً بك" | ./piper --model ar_JO-kareem-medium.onnx --output_file test-arabic.wav

# If successful, play it
aplay test-arabic.wav
# Or on Ubuntu/Debian:
paplay test-arabic.wav
```

### 4. Compare with English Voice

```bash
# Download English voice for comparison
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json

# Test English
echo "Hello test" | ./piper --model en_US-ryan-medium.onnx --output_file test-english.wav
aplay test-english.wav
```

## Expected Results

**If Arabic works on laptop but not RPi5:**
- Issue is ARM-specific ONNX runtime incompatibility
- Need to use espeak for Arabic temporarily

**If Arabic ALSO crashes on laptop:**
- Arabic voice model is broken
- Report bug to Piper developers
- Use espeak for Arabic

## One-Line Quick Test

```bash
cd /tmp && \
wget -q https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz && \
tar -xzf piper_linux_x86_64.tar.gz && \
cd piper && \
wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx && \
echo "مرحباً" | ./piper --model ar_JO-kareem-medium.onnx --output_file test.wav && \
aplay test.wav
```

Let me know what happens!

#!/usr/bin/env python3
"""
Arabic Language Support - Verification Test Script
Tests all bilingual components on the Raspberry Pi 5
"""

import os
import sys

def test_language_config():
    """Test 1: Verify language configuration file exists and is readable"""
    print("=" * 60)
    print("TEST 1: Language Configuration")
    print("=" * 60)
    
    config_file = '/etc/ai-chatbot/language.conf'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            content = f.read()
        print(f"✓ Config file exists: {config_file}")
        print(f"  Content: {content.strip()}")
        
        # Extract language
        for line in content.split('\n'):
            if line.startswith('LANGUAGE='):
                lang = line.split('=')[1].strip()
                print(f"  Active language: {lang}")
                return lang
    else:
        print(f"✗ Config file NOT found: {config_file}")
        return None
    print()

def test_system_tools_import():
    """Test 2: Import system_tools and verify language loading"""
    print("=" * 60)
    print("TEST 2: System Tools Import & Language Detection")
    print("=" * 60)
    
    try:
        sys.path.insert(0, '/root/rpi5-rpios-ai-robot/python')
        from system_tools import LANGUAGE, detect_command_category, get_string
        
        print(f"✓ system_tools.py imported successfully")
        print(f"  Loaded language: {LANGUAGE}")
        print(f"  get_string test: {get_string('time', time_str='12:00 PM')}")
        print()
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        print()
        return False

def test_arabic_regex():
    """Test 3: Test Arabic command detection regex patterns"""
    print("=" * 60)
    print("TEST 3: Arabic Command Detection (Regex)")
    print("=" * 60)
    
    try:
        from system_tools import detect_command_category
        
        test_cases = [
            # English commands
            ("what time is it", "TIME_COMMAND"),
            ("set volume to 50", "VOLUME_COMMAND"),
            ("what is the date", "DATE_COMMAND"),
            ("take a picture", "CAMERA_COMMAND"),
            ("shutdown system", "SHUTDOWN_COMMAND"),
            
            # Arabic commands
            ("ما هو الوقت", "TIME_COMMAND"),
            ("اضبط الصوت", "VOLUME_COMMAND"),
            ("ما هو التاريخ", "DATE_COMMAND"),
            ("التقط صورة", "CAMERA_COMMAND"),
            ("أطفئ النظام", "SHUTDOWN_COMMAND"),
            
            # Non-commands
            ("hello how are you", None),
            ("مرحبا كيف حالك", None),
        ]
        
        passed = 0
        failed = 0
        
        for text, expected in test_cases:
            result = detect_command_category(text)
            if result == expected:
                print(f"  ✓ '{text}' → {result}")
                passed += 1
            else:
                print(f"  ✗ '{text}' → {result} (expected {expected})")
                failed += 1
        
        print(f"\n  Results: {passed} passed, {failed} failed")
        print()
        return failed == 0
    except Exception as e:
        print(f"✗ Test failed: {e}")
        print()
        return False

def test_button_strings():
    """Test 4: Verify button service can load language-aware strings"""
    print("=" * 60)
    print("TEST 4: Button Service Language Strings")
    print("=" * 60)
    
    try:
        sys.path.insert(0, '/root/rpi5-rpios-ai-robot/python')
        from shatrox_buttons import LANGUAGE, get_button_string
        
        print(f"✓ shatrox-buttons.py language: {LANGUAGE}")
        print(f"  Greeting: {get_button_string('greeting')}")
        print(f"  Shutdown: {get_button_string('shutdown')}")
        print()
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        print()
        return False

def test_vosk_models():
    """Test 5: Check VOSK model files"""
    print("=" * 60)
    print("TEST 5: VOSK ASR Models")
    print("=" * 60)
    
    model_dir = "/usr/share/vosk-models"
    en_model = f"{model_dir}/vosk-model-small-en-us-0.15"
    ar_model = f"{model_dir}/vosk-model-ar-mgb2-0.4"
    default_link = f"{model_dir}/default"
    
    en_exists = os.path.exists(en_model)
    ar_exists = os.path.exists(ar_model)
    default_exists = os.path.exists(default_link)
    
    print(f"  English model: {'✓' if en_exists else '✗'} {en_model}")
    print(f"  Arabic model: {'✓' if ar_exists else '✗'} {ar_model}")
    print(f"  Default symlink: {'✓' if default_exists else '✗'} {default_link}")
    
    if default_exists:
        target = os.readlink(default_link)
        print(f"    → Points to: {target}")
    
    print()
    return en_exists and ar_exists and default_exists

def test_piper_voices():
    """Test 6: Check Piper voice files"""
    print("=" * 60)
    print("TEST 6: Piper TTS Voices")
    print("=" * 60)
    
    voice_dir = "/usr/share/piper-voices"
    en_voice = f"{voice_dir}/en_US-ryan-medium.onnx"
    ar_voice = f"{voice_dir}/ar_JO-kareem-medium.onnx"
    default_link = f"{voice_dir}/default.onnx"
    
    en_exists = os.path.exists(en_voice)
    ar_exists = os.path.exists(ar_voice)
    default_exists = os.path.exists(default_link)
    
    print(f"  English voice: {'✓' if en_exists else '✗'} {en_voice}")
    print(f"  Arabic voice: {'✓' if ar_exists else '✗'} {ar_voice}")
    print(f"  Default symlink: {'✓' if default_exists else '✗'} {default_link}")
    
    if default_exists:
        target = os.readlink(default_link)
        print(f"    → Points to: {target}")
    
    print()
    return en_exists and ar_exists and default_exists

def test_ollama_models():
    """Test 7: Check Ollama models"""
    print("=" * 60)
    print("TEST 7: Ollama LLM Models")
    print("=" * 60)
    
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("  Installed models:")
            for line in result.stdout.split('\n'):
                if 'llama3.2:1b' in line:
                    print(f"    ✓ {line.strip()}")
                elif 'qwen-arabic' in line:
                    print(f"    ✓ {line.strip()}")
                elif 'moondream' in line:
                    print(f"    ✓ {line.strip()}")
            print()
            return True
        else:
            print(f"  ✗ ollama list failed: {result.stderr}")
            print()
            return False
    except Exception as e:
        print(f"  ✗ Error running ollama: {e}")
        print()
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   Arabic Language Support - Verification Tests              ║")
    print("║   Raspberry Pi 5                                             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    results = {
        'Language Config': test_language_config() is not None,
        'System Tools Import': test_system_tools_import(),
        'Arabic Regex Detection': test_arabic_regex(),
        'Button Strings': test_button_strings(),
        'VOSK Models': test_vosk_models(),
        'Piper Voices': test_piper_voices(),
        'Ollama Models': test_ollama_models(),
    }
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("✓ All tests PASSED! Arabic support is fully configured.")
        return 0
    else:
        print("✗ Some tests FAILED. Review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

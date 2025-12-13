# Verification Guide for RPI5 AI Robot Fixes

## Test 1: Camera Command (Should be Instant)

**Say:** "Hey Jarvis" → wait for ding → "take a picture"

**Expected:**
- Camera should trigger **immediately** (< 0.5 seconds)
- No delay waiting for AI
- Image description follows

**Logs to check:**
```bash
ssh shatrix@192.168.2.134
sudo journalctl -u ai-chatbot -f | grep -i camera
```
Should show: "Camera command - executing directly (no LLM needed)"

---

## Test 2: Time/Date Commands (Should Use AI for Typo Fixing)

**Try these variations:**

### Test 2a: Correct pronunciation
- "Hey Jarvis" → "what time is it"
- Expected: Works normally

### Test 2b: Typos/variations  
- "Hey Jarvis" → "what's the time"
- "Hey Jarvis" → "tell me the date"

**Expected:**
- Should work even with variations
- Slight delay (~2-3 seconds) for LLM processing is normal

**Logs to check:**
```bash
sudo journalctl -u ai-chatbot -f | grep -E "TIME_COMMAND|DATE_COMMAND"
```
Should show: "Command category detected: TIME_COMMAND (needs LLM parsing)"

---

## Test 3: Volume Command (AI Should Fix Typos)

**Say:** "Hey Jarvis" → "set volume too fifty"
(Note: "too" instead of "to")

**Expected:**
- AI should understand "too" = "to" 
- Volume should set to 50%
- Response: "Volume set to 50%"

**Alternative tests:**
- "change volume two sixty" (two → to, sixty → 60)
- "set volume fifty percent"

**Logs to check:**
```bash
sudo journalctl -u ai-chatbot -f | grep -i volume
```
Should show: 
1. "Command category detected: VOLUME_COMMAND (needs LLM parsing)"
2. "Executing: set_volume(...)"
3. "Result: Volume set to XX%"

---

## Test 4: Mic Indicator Cleanup

**Test 4a: Timeout cleanup**
1. Say "Hey Jarvis"
2. Wait for ding sound
3. **Stay completely silent** (don't say anything)
4. Wait ~10 seconds

**Expected:**
- Mic indicator appears when listening
- After ~10s silence timeout, mic indicator **should disappear**
- Display returns to normal idle state

**Test 4b: No speech detected**
1. Say "Hey Jarvis"
2. Say something very quietly (whisper or background noise)
3. System detects no clear speech

**Expected:**
- Mic indicator should clear automatically
- System returns to wake_listening state

**Logs to check:**
```bash
sudo journalctl -u ai-chatbot -f | grep -E "No speech|clear"
```
Should show: "No speech detected" followed by state returning to wake_listening

---

## Test 5: Quick Test Script

Run this on the RPI5 to monitor all activities:

```bash
ssh shatrix@192.168.2.134
sudo journalctl -u ai-chatbot -f --no-pager | grep --line-buffered -E "CAMERA|TIME_COMMAND|DATE_COMMAND|VOLUME|executing directly|needs LLM|No speech"
```

Then test each scenario above and watch the logs.

---

## Expected Log Patterns

### Camera (Direct execution):
```
Command category detected: CAMERA_COMMAND
Camera command - executing directly (no LLM needed)
```

### Time/Date (LLM processing):
```
Command category detected: TIME_COMMAND (needs LLM parsing)
AI parsed 1 tool call(s)
Executing: get_current_time({})
```

### Volume (LLM fixing typos):
```
Command category detected: VOLUME_COMMAND (needs LLM parsing)
AI parsed 1 tool call(s)
Executing: set_volume({'level': 50})
Result: Volume set to 50%
```

### Cleanup on timeout:
```
No speech detected
State transition: transcribing -> wake_listening
```

---

## Quick Summary

| Test | What to Say | Expected Result |
|------|-------------|-----------------|
| Camera | "take a picture" | Instant (<0.5s) |
| Time | "what time is it" | LLM processes (~2s) |
| Volume + typo | "set volume too fifty" | Works, sets to 50% |
| Mic cleanup | Silent for 10s | Mic icon clears |

---

## Current Status Check

Right now, check if mic indicator is stuck:
```bash
ssh shatrix@192.168.2.134
cat /tmp/ai-qa-display.txt
```

- If output is empty → Display should be clear ✓
- If output shows mic ASCII art → Indicator is stuck ✗

To manually clear (if needed):
```bash
ssh shatrix@192.168.2.134
sudo systemctl restart ai-chatbot
```

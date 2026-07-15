# AGENTS.md

## Repo Shape
- Source of truth is the repo, not the installed copies on the Pi.
- `python/` holds the runtime daemons, `scripts/` is the install flow, `services/` is systemd, `qml/` is the display app, and `scripts-helpers/` holds user-facing utilities.
- `scripts/08-install-services.sh` copies files into `/usr/local/bin`, `/usr/share/shatrox`, `/etc/systemd/system`, and `/etc/ai-chatbot`; edit the repo files and rerun the installer instead of patching installed paths directly.

## Docs To Read
- `README.md` is the high-level setup and runtime overview.
- `VERIFICATION_GUIDE.md` lists the expected behavior and log patterns for hands-on checks after changes.
- `docs/HARDWARE_CONNECTIONS.md` is the pinout and wiring source of truth; it also lists the piscreen GPIOs already reserved by the display stack.

## Core Rules

- Read files before claiming facts. Do not infer behavior from names or memory.
- Keep changes minimal and tied to the request. No opportunistic refactors.
- Preserve unrelated work, public interfaces, file layout, and existing style.
- Never expose secrets in output, logs, commits, or examples.
- Default to ASCII unless the repository already requires otherwise.
- Do not add features, abstractions, config, error handling, comments, or docs the task does not require.
- Only remove dead code or docs made obsolete by your change.

## Setup Flow
- Run `sudo ./setup.sh` from the repo root on Raspberry Pi OS.
- Step order matters. Use `sudo ./setup.sh --step N` or `--from-step N` for focused reruns.
- `--force` only resets step tracking when used without `--step` or `--from-step`.
- Step completion is tracked in `/var/lib/rpi5-ai-robot/setup-state.json`; smart skipping depends on `jq`.
- `./setup.sh --help` is the authoritative option list.

## Important Paths
- Hardware config is written to `/boot/firmware/config.txt`.
- Audio config is written to `/etc/asound.conf`.
- Chatbot config is `/etc/ai-chatbot/config.ini`.
- VOSK models live under `/usr/share/vosk-models`, Piper voices under `/usr/share/piper-voices`, and wake-word models under `/usr/share/openwakeword-models`.
- The motor controller socket is `/tmp/shatrox-motor-control.sock` and the AI chatbot socket is `/tmp/ai-chatbot.sock`.
- `python/requirements.txt` is not the full install set; setup step 10 also installs `pysilero-vad==1.0.0` and `webrtc-noise-gain==1.2.3`.

## Runtime Notes
- The systemd services run as root and execute the installed scripts in `/usr/local/bin`.
- The main service entrypoints are `ai-chatbot.py`, `shatrox-buttons.py`, and `motor_controller.py`.
- `shatrox-buttons.py` talks to the chatbot over the Unix socket; `motor_controller.py` serves motor commands over its own Unix socket.
- The motor setup expects I2C to be enabled and the Waveshare HAT at address `0x40`; the ultrasonic sensor pins are fixed in `python/motor_controller.py` and `scripts/11-motor-setup.sh`.
- Avoid repurposing piscreen-reserved GPIOs from the hardware guide (`GPIO 4, 7, 8-11, 17, 24, 25`) when changing buttons or sensors.

## Verification
- There is no centralized package test runner in this repo; verify changes with the smallest relevant setup step or service-level command.
- Check services with `sudo systemctl status ai-chatbot shatrox-buttons shatrox-display shatrox-motor-control` and logs with `sudo journalctl -u <service> -f`.
- Motor changes: `sudo bash scripts-helpers/test-motors.sh`.
- Camera setup uses `rpicam-still` when available, falling back to `libcamera-still`.
- To copy repo changes to a Pi, use `./deploy-to-rpi.sh <RPI_IP> [username]`.

## Destructive Actions (require approval)
- Deleting files outside scope, rewriting git history, force push, hard reset, destructive database/infrastructure operations, firmware/hardware writes, or changing system state outside the repository.

## Git
- Do not commit, branch, tag, or push unless asked. Review status first, never stage unrelated files or secrets, and prefer small atomic commits.

## Communication
- No filler language. No apologies. No leading narration ("I'll now...").
- Be brief and concrete: state what changed, why, and how it was verified.
- Separate facts from assumptions. When blocked, state the blocker and the next decision. When reviewing, lead with findings ordered by severity and say explicitly when none are confirmed.

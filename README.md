# EEG Dinosaur Runner

An Arduino-based EEG interface for a Python/Pygame dinosaur runner. The Arduino reads a TGAM-compatible module, checks packets, detects blink candidates from raw-signal amplitude, and sends attention, meditation and signal-quality indicators to the game.

## Overview

```text
TGAM module -- UART, 57600 baud --> Arduino UNO / Nano
Arduino -- USB serial, 57600 baud --> Python reader --> Pygame game
```

| Input | Game behavior |
| --- | --- |
| Blink candidate | Jump when signal quality is acceptable |
| Effective attention >= 80 | Sprint for 2.5 seconds with collision immunity; 7-second cooldown |
| Meditation >= 65 | Reduce speed to 75% and enable a one-hit shield; 8-second shield cooldown |
| Keyboard | Jump, duck, pause and restart |

Attention affects sprint triggering; ordinary attention-based speed bonuses are disabled in this implementation. The HUD displays EEG indicators, connection state, blink count and game modes.

## Files

```text
arduino/arduino.ino          Firmware: packet parsing and blink detection
dinosaur/main.py            Game and HUD
dinosaur/config.py          Ports, thresholds and demo settings
dinosaur/eeg_serial_reader.py  Serial reader and simulator
dinosaur/eeg_control.py      Control helpers
dinosaur/Assets/             Game sprites
requirements.txt            Python dependencies
CITATION.cff                Software citation metadata
LICENSE                     License for the listed original files
THIRD_PARTY_NOTICES.md       Game attribution and license scope
```

## Installation

Use Python 3.9 or later and a graphical desktop. The hardware setup requires Arduino IDE and an UNO/Nano-compatible AVR board.

```bash
git clone https://github.com/Rocky-Bai-hust/EEG-dinosaur-runner.git
cd EEG-dinosaur-runner
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on Linux/macOS, then install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Hardware setup

| Connection | Destination |
| --- | --- |
| TGAM TX | Arduino D0/RX |
| TGAM GND | Arduino GND |
| TGAM RX | Leave disconnected |
| Arduino USB | Computer |

Verify the module's supply voltage and UART logic compatibility with its vendor specifications.

1. Disconnect TGAM TX from D0/RX before uploading.
2. Open `arduino/arduino.ino` in Arduino IDE, select the board and port, and upload.
3. Reconnect TGAM TX and close the serial monitor.
4. Update `dinosaur/config.py`:

```python
SERIAL_ENABLED = True
SIMULATE_EEG = False
SERIAL_PORT = "COM7"  # Replace with your actual port.
SERIAL_BAUD = 57600
```

Run from the repository root:

```bash
python dinosaur/main.py
```

Press any key at the menu. The default startup gate requires a connected reader and SIG=0 for 2 seconds. During gameplay, EEG input requires SIG <= 10; the firmware's blink gate uses SIG <= 50.

The supplied sketch implements the wired route. HC-05 pairing and configuration are not included.

## Run without hardware

For keyboard-only play, set:

```python
SERIAL_ENABLED = False
IN_GAME_BAD_SIGNAL_AUTOPILOT = False
```

For simulated EEG, set:

```python
SERIAL_ENABLED = True
SIMULATE_EEG = True
```

Then run `python dinosaur/main.py`. Simulation generates random indicators and blink candidates.

| Key | Action |
| --- | --- |
| Up / Space | Jump |
| Down | Duck |
| Q | Pause / resume |
| R while paused | Restart |
| Escape on the connection screen | Return to menu |

## Serial format

The Arduino sends newline-terminated text at 57600 baud:

```text
ATT:65,MED:48,SIG:0,BLINK:1,COUNT:3
```

`ATT` and `MED` are module indicators, typically 0–100. `SIG` is poor-signal quality, with lower values indicating better contact. `BLINK:1` latches a one-shot jump candidate; `COUNT` is the cumulative candidate count.

The firmware handles fixed 4-byte raw and 32-byte digest payload layouts. Blink detection uses an absolute raw-amplitude threshold of 1050 and a 350 ms refractory interval.

## Configuration and limitations

The default demonstration settings enable adaptive jump clearance, automatic jumps during bad signal, and a successful-pass bonus to effective attention. Disable `ENABLE_MIN_JUMP_CLEARANCE`, `IN_GAME_BAD_SIGNAL_AUTOPILOT` and `ENABLE_FOCUS_SUCCESS_ASSIST` when evaluating unassisted EEG control.

- If the connection screen remains open, check the port, baud rate and SIG. Close any application using the serial port.
- The reader has no inactivity timeout or automatic reconnect; a silent link may retain stale values. Restart after restoring the connection.
- Blink detection is an amplitude heuristic and can react to artifacts.
- Hardware performance has not been independently validated for this release. No EEG dataset or quantitative benchmark is included.

For reproducible use, record the exact commit, software versions, hardware model, thresholds and assistance flags. Use GitHub's **Cite this repository** metadata to cite the software.

## Attribution and license

The game derives from [MaxRohowsky/chrome-dinosaur](https://github.com/MaxRohowsky/chrome-dinosaur). The [MIT license](LICENSE) covers the listed original files only. The game code and sprites have unresolved upstream licensing and are excluded from that grant; see [third-party notices](THIRD_PARTY_NOTICES.md).

"""Launch EEG Dinosaur Runner without editing the saved configuration."""
import argparse
import importlib.util
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--keyboard", action="store_true", help="Play without hardware (default).")
    modes.add_argument("--simulate", action="store_true", help="Generate synthetic EEG input; no serial port is opened.")
    modes.add_argument("--eeg", action="store_true", help="Use real EEG hardware over serial.")
    parser.add_argument("--port", help="Arduino serial port, required with --eeg (e.g. COM7).")
    args = parser.parse_args()
    if args.eeg and not args.port:
        parser.error("--eeg requires --port")
    if args.port and not args.eeg:
        parser.error("--port is only valid with --eeg")

    game_dir = Path(__file__).resolve().parent / "dinosaur"
    sys.path.insert(0, str(game_dir))
    spec = importlib.util.spec_from_file_location("config", game_dir / "config.py")
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    config.SERIAL_ENABLED = args.eeg or args.simulate
    config.SIMULATE_EEG = args.simulate
    if args.eeg:
        config.SERIAL_PORT = args.port
    elif not args.simulate:
        config.IN_GAME_BAD_SIGNAL_AUTOPILOT = False
        config.ENABLE_MIN_JUMP_CLEARANCE = False
        config.ENABLE_FOCUS_SUCCESS_ASSIST = False
    sys.modules["config"] = config

    try:
        runpy.run_path(str(game_dir / "main.py"), run_name="__main__")
    except ModuleNotFoundError as exc:
        if exc.name != "pygame":
            raise
        parser.exit(1, "Pygame is missing. Run: python -m pip install -r requirements.txt\n")


if __name__ == "__main__":
    main()

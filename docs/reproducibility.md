# Reproducibility and validation

## Release provenance

The five implementation source files and game assets are copied byte-for-byte from the supplied project source. The original STM32-oriented README is replaced by repository-level documentation reflecting the Arduino sketch and current configuration. The historical preview, bytecode caches, course reports, slides, enrollment spreadsheet and video are excluded.

No publication identifier, participant dataset or quantitative evaluation accompanies this software. Reference documents describe classroom demonstrations; those descriptions are not treated as independently reproduced benchmarks.

## Record an experiment configuration

Record the repository commit, Python/dependency versions, OS, Arduino board/core/bootloader, module model/firmware, transport, baud rate, signal thresholds, blink amplitude/refractory settings and every assist flag. Keep identifying participant records outside the public repository.

Use `python --version` and `python -m pip freeze` to capture the desktop environment. Random game obstacles and simulator values are not seeded by default. Scores are not deterministic measurements.

## Demonstration assists

The supplied configuration enables all of the following:

| Setting | Consequence |
| --- | --- |
| ENABLE_MIN_JUMP_CLEARANCE | Jump velocity adapts to speed / clearance |
| IN_GAME_BAD_SIGNAL_AUTOPILOT | Bad-signal/offline runs can automatically jump selected obstacles |
| ENABLE_FOCUS_SUCCESS_ASSIST | Successful unassisted passes add +5 effective attention, capped at +50 |

Before assessing EEG control performance, disable these assists in the experimental clone and explicitly report the resulting settings. Effective attention can trigger sprint even when raw ATT is below 80. Keyboard input remains available and should be recorded or controlled during evaluations. `DEBUG_MODE=1` suppresses death; `ENABLE_EEG_TEST_HOTKEYS=True` overrides real EEG with synthetic states.

## Automated checks

Run `python -m unittest discover -s tests -v` and `python -m compileall -q dinosaur tests`. Checks exercise parser edge cases, event latching, snapshot isolation, gate boundaries and speed bounds. They require neither hardware nor Pygame display initialization. The CI workflow repeats these checks; firmware and interactive game behavior require separate validation.

## Manual end-to-end checklist

1. Keyboard-only: disable serial and autopilot; start, jump, duck, pause/resume, collide and restart.
2. Simulation: enable serial and simulation; verify the simulator banner, changing HUD values and blink count.
3. Hardware: upload the sketch, set the actual port, confirm frames at 57600 baud and close the monitor before launching the game.
4. Startup gate: confirm connected SIG=0 for 2 seconds allows entry; poor signal should reset the countdown.
5. Blink: compare emitted BLINK frames / COUNT increments with visible jumps, while noting the heuristic's possible false triggers.
6. Shield/sprint: inspect thresholds, cooldowns and collision behavior.
7. Signal loss: compare behavior with autopilot enabled and disabled. Test explicit serial errors and silent links separately.
8. Pause: confirm score and obstacles freeze and resume without consuming game cooldown time.

## Known limitations

- No inactivity timeout, robust port reconnect, field-range validation or firmware packet-read timeout.
- Fixed packet layouts; no general TGAM protocol implementation.
- No implemented attention speed tiers or sliding-window smoothing, despite older descriptions.
- Restart paths recursively invoke game/menu functions; long repeated sessions may accumulate stack frames.
- No measured blink accuracy, latency, repeatability, baseline comparison or participant sample size.
- The game and sprites have unresolved upstream licensing; see third-party notices.

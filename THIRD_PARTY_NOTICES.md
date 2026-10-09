# Third-party notices

## Python dinosaur game and sprites

The original local game archive identifies MaxRohowsky as its author. Its upstream is <https://github.com/MaxRohowsky/chrome-dinosaur> (also previously reachable through the maxontech account).

`dinosaur/main.py` extends that game; `dinosaur/Assets/` contains sprites from the supplied game archive. These portions are excluded from this repository's MIT grant. No explicit license file was found in the supplied archive, and the upstream root LICENSE lookup returned 404 during preparation on 2026-10-09. Attribution alone does not resolve permission to reuse or redistribute. Obtain upstream permission or replace these portions before asserting a fully permissively licensed distribution.

The visual design resembles Chrome's dinosaur game. This project is independent and does not imply endorsement by Google, Chromium, the upstream game author or hardware vendors. No ownership of those names or artwork is claimed.

## Dependencies

Pygame and pyserial are installed separately through `requirements.txt`; their source is not vendored. Consult their own distributions for license notices. Arduino board cores are likewise installed through Arduino tooling, not redistributed here.

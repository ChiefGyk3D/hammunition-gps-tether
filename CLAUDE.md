# Hammunition GPS tether — Claude Code Context

Serves gpsd's position as NMEA on 127.0.0.1 (10110), the browser map's
`/position` SSE stream (10111) and an optional unix socket for GeoClue. A
separable component of [Hammunition](https://github.com/Renegade-Penguin/Hammunition):
its own repository and releases; the engine installs it as a catalog unit.

Binary: `hammunition-gps-tether`. Package: `hammunition_gps_tether` (src
layout). Licence GPL-3.0-or-later. Copyright Renegade Penguin LLC.

## Invariants

- **Loopback only.** The TCP listeners bind 127.0.0.1 whatever the flags; the
  position is unauthenticated.
- **Standard library only**, and never root (the CLI refuses it).
- **No engine import.** The engine's GeoClue files are read, never written, here.
- Flags and the printed banner are quoted by Hammunition's docs: change them
  together with the engine.
- The decision numbers (D-061, D-069, D-071) are the engine's, in its
  `docs/DECISIONS.md`.

## Standing rules (from the parent project)

- `make check` reproduces CI; checks live in the suite.
- A check must be falsifiable: break what it watches, see it red, restore.
- The suite blocks every socket but loopback (`tests/conftest.py`).
- `mypy --strict` and ruff are gates.
- Never pin an action from memory: `git ls-remote --tags`, pin the commit.
- No callsign, grid square, hostname or serial anywhere; coordinates in tests
  are synthetic; placeholders are `N0CALL` and `FN31pr`.

## Layout

```
src/hammunition_gps_tether/   tether (the server), cli, geoclue (constants + reader)
systemd/                      the user unit
tests/                        test_tether, test_cli, test_repo, conftest
```

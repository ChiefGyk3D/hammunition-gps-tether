<!--
SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

Notable changes, newest first. Versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Code scanning, second pass: the Semgrep marker on the deliberate 0660 GeoClue socket `chmod` (D-069) is the bare `# nosemgrep` on the matched line.

### Added

- Fuzzing: Atheris targets under `fuzz/` for gpsd's JSON stream, the NMEA sentence
  builder, the `GET /position` request head and the command-line values, run by
  GYST's `python-fuzz.yml` (v1.10.0) from `ci.yml` on pull requests and weekly;
  `tests/test_fuzz_targets.py` keeps them honest. See the README.

### Fixed

- `--gpsd [ADDR%SCOPE]` refused nothing in a scope id: Python's `IPv6Address` accepts any character but `%` after the `%`, so a host with `\r`, NUL or DEL passed the bracket branch while the plain-host branch refused whitespace. Whitespace and control characters are now refused by name; `fe80::1%eth0` still works. Found by the CI fuzz job on PR #7.
- Found by the fuzz targets: a gpsd time at the calendar's edge with an offset
  (`0001-01-01T00:00:00+05:00`) raised `OverflowError` and ended the tether's loop;
  it now takes the system clock like any unreadable time. A speed that overflows
  to infinity in knots printed `inf` in the RMC sentence; the field is now empty.
  A `GET /position` whose `Origin` ended in a non-ASCII digit (`http://127.0.0.1:\u00b2`)
  passed the loopback check and then raised `UnicodeEncodeError` while the response
  was built, ending the loop; it is refused with 403.

### Changed

- The GYST callers (`ci.yml`, `security.yml`) move from v1.5.0 to v1.10.0; every
  input they pass still exists there (diffed).

- CodeQL sweep: the tests import the module once, an IPv6 test can no longer reach
  its assertions without a gpsd, and the two swallowed errors say why. Adds
  `SECURITY.md` and Dependabot for actions and pip.

## [0.1.1] - 2026-10-02

### Changed

- Every refusal (a port or socket already in use, run as root, an unusable
  `--gpsd` or option value) now exits 3; an uncaught crash still exits 1 and
  argparse's usage error 2. The user unit's `RestartPreventExitStatus` is 3, not
  1, so systemd stops retrying refusals and keeps retrying crashes.
- Clarify the README's pip/pipx service and Hammunition engine install paths.

## [0.1.0] - 2026-10-01

### Added

- The first release: the GPS tether, moved out of Hammunition (`hammunition maps
  gps-tether`) into its own project. NMEA on 127.0.0.1:10110, the browser map's
  `GET /position` event stream on 127.0.0.1:10111, and an optional unix socket
  for GeoClue. Same flags: `--gpsd`, `--port`, `--position-port`,
  `--nmea-socket`, `--no-nmea-socket`.
- `systemd/hammunition-gps-tether.service`, a user unit, and `make install-user`.
- SIGTERM stops it like Ctrl-C, so a service stop removes the unix socket.

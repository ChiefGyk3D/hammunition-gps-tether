<!--
SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

Notable changes, newest first. Versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

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

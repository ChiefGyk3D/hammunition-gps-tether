# Security Policy

## Supported versions

The latest tagged release is supported (currently v0.1.1). Fixes land on
`main` and ship in the next tag; older tags are not patched.

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue or pull
request. Use GitHub's private vulnerability reporting on this repository:
[Report a vulnerability](https://github.com/Renegade-Penguin/hammunition-gps-tether/security/advisories/new).

Please include the flags you ran it with, what you expected and what
happened, and the steps to reproduce it. Do not include a callsign, grid
square, hostname, coordinates or any other station detail you want kept
private.

## What is in scope

- The tether under `src/hammunition_gps_tether/`: its listeners, the request
  parser, the unix socket and its ownership and mode, and the refusal to run
  as root.
- The shipped systemd unit under `systemd/`.
- Anything that lets a client reach the position from off the machine: the TCP
  listeners are bound to 127.0.0.1 by design, and the position is
  unauthenticated, so a bind elsewhere is a vulnerability.

The unix socket is mode 0660 in GeoClue's group by design, so GeoClue can read
the position. Vulnerabilities in gpsd, GeoClue or the Hammunition engine belong
with those projects.

## What to expect

The tether has a sole maintainer. Expect an acknowledgement within a week and a
fix or a written assessment as soon as practical after that. There is no bug
bounty. Reporters are credited in the changelog entry for the fix unless they
ask not to be.

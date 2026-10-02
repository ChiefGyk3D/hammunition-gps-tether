# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""The ``hammunition-gps-tether`` command.

Serves gpsd's position as NMEA on 127.0.0.1 only (D-061), the browser map's
``GET /position`` stream (D-071) and, optionally, a unix socket for GeoClue
(D-069). Moved from ``hammunition maps gps-tether`` in the engine.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from collections.abc import Sequence

from hammunition_gps_tether import __version__, geoclue, tether

EXIT_OK = 0
EXIT_FAILED = 1


def run(args: argparse.Namespace) -> int:
    """Serve gpsd's position until Ctrl-C or SIGTERM; the exit status."""

    try:
        port = tether.PORT if args.port is None else tether.serve_port(args.port)
        gpsd = tether.GPSD if args.gpsd is None else tether.gpsd_address(args.gpsd)
        position_port = (
            tether.POSITION_PORT
            if args.position_port is None
            else tether.serve_port(args.position_port, flag="--position-port")
        )
        if position_port == port:
            raise ValueError(
                f"--port {port} and --position-port {position_port} are the same port; "
                f"the map's position stream is on {tether.POSITION_PORT} unless "
                f"--position-port names another"
            )
        if args.nmea_socket is not None and args.no_nmea_socket:
            raise ValueError("--nmea-socket and --no-nmea-socket ask for opposite things")
    except ValueError as exc:
        print(f"error: {exc}.", file=sys.stderr)
        return EXIT_FAILED
    if os.geteuid() == 0:
        print(
            "error: the GPS tether reads gpsd as any user can; run it as yourself, not as root.",
            file=sys.stderr,
        )
        return EXIT_FAILED
    try:
        listener = tether.listen(port)
    except OSError as exc:
        print(
            f"error: cannot listen on {tether.HOST} port {port}: "
            f"{exc.strerror or exc}. Is another tether already running? "
            f"--port N serves another port.",
            file=sys.stderr,
        )
        return EXIT_FAILED
    try:
        http = tether.listen(position_port)
    except OSError as exc:
        listener.close()
        print(
            f"error: cannot listen on {tether.HOST} port {position_port} for the map's "
            f"position: {exc.strerror or exc}. --position-port N serves it on another port.",
            file=sys.stderr,
        )
        return EXIT_FAILED

    def log(line: str) -> None:
        print(line, file=sys.stderr, flush=True)

    socket_path: str | None = args.nmea_socket
    if socket_path is None and not args.no_nmea_socket and geoclue.configured():
        socket_path = geoclue.SOCKET
    unix = None
    if socket_path is not None:
        try:
            unix = tether.listen_unix(socket_path, group=geoclue.GROUP, log=log)
        except (OSError, ValueError) as exc:
            why = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
            if args.nmea_socket is not None:
                listener.close()
                http.close()
                print(f"error: cannot listen on {socket_path}: {why}.", file=sys.stderr)
                return EXIT_FAILED
            hint = (
                f" Its directory comes from {geoclue.TMPFILES}; `sudo systemd-tmpfiles "
                f"--create {geoclue.TMPFILES}` makes it."
                if isinstance(exc, FileNotFoundError)
                else ""
            )
            log(
                f"Not serving GeoClue: cannot listen on {socket_path} ({why}).{hint} "
                f"QMapShack and the map are served as usual."
            )
            socket_path = None
    print(
        tether.instructions(port, gpsd=gpsd, position_port=position_port, nmea_socket=socket_path),
        flush=True,
    )

    try:
        _accept_sigterm()
        tether.serve(
            listener, http=http, unix=None if unix is None else unix[0], gpsd=gpsd, log=log
        )
    except KeyboardInterrupt:
        log("Stopped.")
    finally:
        listener.close()
        http.close()
        if unix is not None and socket_path is not None:
            tether.close_unix(unix[0], socket_path, unix[1])
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hammunition-gps-tether",
        description="Serve gpsd's position as NMEA on 127.0.0.1:10110 for QMapShack's GPS "
        "TCP/IP source (D-061), and to the browser map on 127.0.0.1:10111 (D-071).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--gpsd",
        metavar="HOST[:PORT]",
        default=None,
        help="the gpsd to read: another machine's, an IPv6 address in brackets "
        "(default 127.0.0.1:2947)",
    )
    p.add_argument(
        "--port",
        metavar="N",
        default=None,
        help="serve on 127.0.0.1 port N, 1024 to 65535, when 10110 is taken (default 10110)",
    )
    p.add_argument(
        "--position-port",
        metavar="N",
        default=None,
        help="serve the browser map's position stream (GET /position) on 127.0.0.1 port N "
        "(default 10111, D-071)",
    )
    p.add_argument(
        "--nmea-socket",
        metavar="PATH",
        default=None,
        help="also serve NMEA on a unix socket at PATH, mode 0660, for GeoClue (D-069); "
        "the default is /run/hammunition-gps/nmea.sock once `hammunition hardware apply` "
        "has set GeoClue up, and off otherwise",
    )
    p.add_argument(
        "--no-nmea-socket",
        action="store_true",
        help="do not serve GeoClue's socket, even where `hammunition hardware apply` has set it up",
    )
    return p


def _term(signum: int, frame: object) -> None:
    """SIGTERM (systemd's stop) ends the tether like Ctrl-C: socket removed, exit 0.

    A second SIGTERM during the cleanup is ignored, so the cleanup finishes.
    """
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise KeyboardInterrupt


def _accept_sigterm() -> None:
    """Let a SIGTERM held back since startup arrive, now that the ``try`` that cleans up is open."""
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if threading.current_thread() is threading.main_thread():
        # Held back until `run` is inside the try that closes what it opened: a
        # SIGTERM during startup then stops the tether cleanly instead of
        # tracebacking past an open socket.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        signal.signal(signal.SIGTERM, _term)
    return run(args)

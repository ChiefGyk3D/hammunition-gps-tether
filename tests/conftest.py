# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""Suite-wide guarantees.

**No test reaches past loopback.** Every socket connect to anywhere but
127.0.0.0/8, ::1 or a unix path is blocked for the whole suite, so a test that
tries fails with a clear message and the suite cannot quietly depend on the
internet. (The pattern is Hammunition's own ``tests/conftest.py``.)

**No test reads the host's GeoClue files.** A machine where the engine's
``hardware apply`` has run holds the real drop-in, and the tether would then
serve the real socket by default; every path points at a place that does not
exist unless a test makes it.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


class NetworkBlocked(RuntimeError):
    """A test tried to open a non-loopback connection."""


def _loopback(address: Any) -> bool:
    if not isinstance(address, tuple) or not address:
        return True  # AF_UNIX: a filesystem path, not the network
    host = address[0]
    if not isinstance(host, str):
        return False
    return host in {"127.0.0.1", "::1", "localhost"} or host.startswith("127.")


@pytest.fixture(autouse=True, scope="session")
def _no_network() -> Iterator[None]:
    def guard(self: socket.socket, address: Any) -> Any:
        if not _loopback(address):
            raise NetworkBlocked(f"the test suite blocked a connection to {address!r}")
        return _real_connect(self, address)

    def guard_ex(self: socket.socket, address: Any) -> Any:
        if not _loopback(address):
            raise NetworkBlocked(f"the test suite blocked a connection to {address!r}")
        return _real_connect_ex(self, address)

    socket.socket.connect = guard  # type: ignore[assignment,method-assign]
    socket.socket.connect_ex = guard_ex  # type: ignore[assignment,method-assign]
    try:
        yield
    finally:
        socket.socket.connect = _real_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = _real_connect_ex  # type: ignore[method-assign]


@pytest.fixture(autouse=True)
def geoclue_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every GeoClue path under this test's tmp_path, absent until the test writes it."""
    from hammunition_gps_tether import geoclue

    root = tmp_path / "host-geoclue"
    for name in ("DROPIN", "TMPFILES", "SOCKET"):
        monkeypatch.setattr(geoclue, name, str(root) + getattr(geoclue, name))
    return root

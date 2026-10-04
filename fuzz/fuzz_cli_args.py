# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fuzz target: the values the command line hands the tether.

``serve_port`` and ``gpsd_address`` check what an operator (or a unit file)
types for ``--port``, ``--position-port`` and ``--gpsd``. Each raises
``ValueError`` with a message naming the flag, or returns a value in range:
a port from 1024 to 65535, and for gpsd a non-empty host with no whitespace
and a port from 1 to 65535. Nothing else may escape, and nothing is opened.
"""

import sys

import atheris

with atheris.instrument_imports():
    from hammunition_gps_tether import tether

_PIECES = (
    "[",
    "]",
    "::1",
    "127.0.0.1",
    "localhost",
    ":",
    "2947",
    "99999",
    "0",
    "-",
    " ",
    "1023",
    "65535",
    "²",
)


def _text(fdp: atheris.FuzzedDataProvider) -> str:
    if fdp.ConsumeBool():
        return fdp.ConsumeUnicodeNoSurrogates(48)
    return "".join(
        _PIECES[fdp.ConsumeIntInRange(0, len(_PIECES) - 1)]
        for _ in range(fdp.ConsumeIntInRange(0, 6))
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = _text(fdp)
    try:
        port = tether.serve_port(text)
    except ValueError as exc:
        assert "--port" in str(exc)
    else:
        assert 1024 <= port <= 65535, (text, port)
    try:
        host, number = tether.gpsd_address(text)
    except ValueError as exc:
        assert "--gpsd" in str(exc)
    else:
        assert host and not any(c.isspace() for c in host), (text, host)
        assert 1 <= number <= 65535, (text, number)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

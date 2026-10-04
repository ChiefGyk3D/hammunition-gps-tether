# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fuzz target: the request head of ``GET /position`` (D-071).

The tether parses this request itself, on a loopback port a web page can reach,
so it is the one place hostile bytes meet it from a browser. ``position_response``
takes whatever head a client sent and must answer, never raise; it may start the
event stream only for a loopback ``Host`` (DNS rebinding) and a loopback or absent
``Origin``; and what it echoes into ``Access-Control-Allow-Origin`` must be a
loopback origin that cannot carry a line break. The head is built half from
near-valid pieces, so the interesting branches are reached.
"""

import re
import sys

import atheris

with atheris.instrument_imports():
    from hammunition_gps_tether import tether

_ORIGIN = re.compile(rb"http://(127\.0\.0\.1|localhost)(:[0-9]+)?")
_HOSTS = ("127.0.0.1", "localhost", "LOCALHOST", "127.0.0.1.evil.example", "[::1]")
_ORIGINS = (
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:\xb2",
    "http://evil.example",
    "null",
    "",
)
_TARGETS = ("/position", "/position?x=1", "/", "/position/../x", "/POSITION")


def _pick(fdp: atheris.FuzzedDataProvider, options: tuple[str, ...]) -> str:
    if fdp.ConsumeIntInRange(0, 5) == 0:
        return fdp.ConsumeUnicodeNoSurrogates(12)
    return options[fdp.ConsumeIntInRange(0, len(options) - 1)]


def _head(fdp: atheris.FuzzedDataProvider, port: int) -> bytes:
    if fdp.ConsumeBool():
        return fdp.ConsumeBytes(1024)
    method = "GET" if fdp.ConsumeIntInRange(0, 6) else _pick(fdp, ("POST", "get", "HEAD"))
    lines = [f"{method} {_pick(fdp, _TARGETS)} HTTP/1.1"]
    if fdp.ConsumeIntInRange(0, 9):
        lines.append(
            f"Host: {_pick(fdp, _HOSTS)}:{port if fdp.ConsumeIntInRange(0, 5) else port + 1}"
        )
    if fdp.ConsumeBool():
        lines.append(f"Origin: {_pick(fdp, _ORIGINS)}")
    if fdp.ConsumeBool():
        lines.append(f"Accept: {_pick(fdp, ('text/event-stream', '*/*'))}")
    for _ in range(fdp.ConsumeIntInRange(0, 2)):
        lines.append(fdp.ConsumeUnicodeNoSurrogates(20))
    return "\r\n".join(lines).encode("latin-1", errors="replace") + b"\r\n\r\n"


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    port = fdp.ConsumeIntInRange(1024, 65534)
    head = _head(fdp, port)
    response, streaming = tether.position_response(head, port)
    assert response.startswith(b"HTTP/1.1 ")
    block, _, _ = response.partition(b"\r\n\r\n")
    for line in block.split(b"\r\n")[1:]:
        if line.lower().startswith(b"access-control-allow-origin:"):
            assert _ORIGIN.fullmatch(line.split(b": ", 1)[1]), line
    if streaming:
        assert response.startswith(b"HTTP/1.1 200 ")
        hosts = [
            line.partition(b":")[2].strip().lower()
            for line in head.split(b"\r\n")[1:]
            if line.lower().startswith(b"host:")
        ]
        assert hosts and hosts[-1] in (
            f"127.0.0.1:{port}".encode(),
            f"localhost:{port}".encode(),
        ), head
    else:
        assert not response.startswith(b"HTTP/1.1 200 ")


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

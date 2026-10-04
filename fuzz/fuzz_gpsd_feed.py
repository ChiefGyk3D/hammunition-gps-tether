# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fuzz target: gpsd's JSON stream, as the tether reads it.

``Feed.push`` takes whatever bytes arrive from the gpsd socket, in whatever
chunks, and must never raise: gpsd may be another machine's, a proxy, or not
gpsd at all. Every sentence it hands back is NMEA that QMapShack and GeoClue
will parse, so it must be ASCII with a correct checksum and no ``inf`` or
``nan``; and the position it keeps must be an event the map can print.
Half the input is structured (a TPV or SKY object with fuzzed fields), so the
sentence builder is reached and not only the JSON parser's refusals.
"""

import json
import re
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from hammunition_gps_tether import tether

_SENTENCE = re.compile(rb"\$([A-Z0-9,.\-]+)\*([0-9A-F]{2})\r\n")


def _num(fdp: atheris.FuzzedDataProvider) -> Any:
    pick = fdp.ConsumeIntInRange(0, 9)
    if pick == 0:
        return fdp.ConsumeFloat()
    if pick == 1:
        return fdp.ConsumeIntInRange(-(2**70), 2**70)
    if pick == 2:
        return fdp.ConsumeUnicodeNoSurrogates(6)
    if pick == 3:
        return fdp.ConsumeBool()
    if pick == 4:
        return None
    if pick == 5:
        return [fdp.ConsumeFloat()]
    return round(fdp.ConsumeFloatInRange(-200.0, 200.0), 6)


def _message(fdp: atheris.FuzzedDataProvider) -> bytes:
    kind = ("TPV", "SKY", "TPV", fdp.ConsumeUnicodeNoSurrogates(4))[fdp.ConsumeIntInRange(0, 3)]
    msg: dict[str, Any] = {"class": kind}
    for key in (
        "mode",
        "lat",
        "lon",
        "speed",
        "track",
        "altMSL",
        "alt",
        "geoidSep",
        "status",
        "hdop",
        "uSat",
    ):
        if fdp.ConsumeBool():
            msg[key] = _num(fdp)
    if fdp.ConsumeBool():
        msg["time"] = (
            "2026-10-04T12:34:56.789Z",
            "2026-10-04T12:34:56+05:30",
            "0001-01-01T00:00:00+05:00",
            "9999-12-31T23:59:59-05:00",
            fdp.ConsumeUnicodeNoSurrogates(30),
        )[fdp.ConsumeIntInRange(0, 4)]
    if fdp.ConsumeBool():
        msg["satellites"] = [
            {"used": fdp.ConsumeBool()} for _ in range(fdp.ConsumeIntInRange(0, 5))
        ]
    return json.dumps(msg).encode() + b"\n"


def check_sentences(out: list[bytes]) -> None:
    for line in out:
        match = _SENTENCE.fullmatch(line)
        assert match, f"not an NMEA sentence: {line!r}"
        assert match[2].decode() == tether.checksum(match[1].decode()), line
        assert b"inf" not in line.lower() and b"nan" not in line.lower(), line


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    feed = tether.Feed()
    if fdp.ConsumeBool():
        chunks = [_message(fdp) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    else:
        raw = fdp.ConsumeBytes(2048)
        cut = fdp.ConsumeIntInRange(0, len(raw))
        chunks = [raw[:cut], raw[cut:]]
    for chunk in chunks:
        check_sentences(feed.push(chunk))
    if feed.position is not None:
        event = tether.position_event(feed.position)
        assert event.startswith(b"data: ") and event.endswith(b"\n\n")
        assert json.loads(event[6:])["lat"] == feed.position["lat"]


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

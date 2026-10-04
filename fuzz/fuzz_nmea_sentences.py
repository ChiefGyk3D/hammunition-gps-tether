# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fuzz target: the NMEA sentence builder and its coordinate and time inputs.

``sentences`` takes a gpsd TPV dict whose values may be anything JSON can
carry. It returns ``$GPRMC`` and ``$GPGGA`` or nothing, and never raises. The
degrees-and-minutes conversion must give minutes under 60 and a valid
hemisphere for every finite coordinate in range, and the time fields must be
``hhmmss.ss`` and ``ddmmyy`` for any ISO 8601 string, including one at the
edge of the calendar with an offset. The clock is the system's; nothing else is
touched.
"""

import re
import sys

import atheris

with atheris.instrument_imports():
    from hammunition_gps_tether import tether

_HMS = re.compile(r"\d{6}\.\d{2}")
_DMY = re.compile(r"\d{6}")
_SENTENCE = re.compile(r"\$([A-Z0-9,.\-]+)\*([0-9A-F]{2})\r\n")


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    text = fdp.ConsumeUnicodeNoSurrogates(40)
    hms, dmy = tether._time_fields(text)
    assert _HMS.fullmatch(hms) and _DMY.fullmatch(dmy), (text, hms, dmy)

    lat = fdp.ConsumeFloatInRange(-90.0, 90.0)
    lon = fdp.ConsumeFloatInRange(-180.0, 180.0)
    for value, width, pos, neg in ((lat, 2, "N", "S"), (lon, 3, "E", "W")):
        digits, hemisphere = tether._degrees_minutes(value, width, pos, neg)
        degrees, minutes = digits[:width], digits[width:]
        assert re.fullmatch(rf"\d{{{width}}}[0-5]\d\.\d{{4}}", digits), (value, digits)
        assert hemisphere in (pos, neg)
        assert int(degrees) <= (90 if width == 2 else 180), (value, digits)
        assert float(minutes) < 60

    tpv = {
        "mode": fdp.ConsumeIntInRange(0, 3),
        "lat": lat,
        "lon": lon,
        "time": text if fdp.ConsumeBool() else "2026-10-04T12:00:00Z",
        "speed": fdp.ConsumeFloat(),
        "track": fdp.ConsumeFloat(),
        "altMSL": fdp.ConsumeFloat(),
        "geoidSep": fdp.ConsumeFloat(),
        "status": fdp.ConsumeIntInRange(0, 3),
    }
    out = tether.sentences(tpv, satellites=fdp.ConsumeIntInRange(0, 99), hdop=fdp.ConsumeFloat())
    assert len(out) in (0, 2)
    for line in out:
        match = _SENTENCE.fullmatch(line.decode("ascii"))
        assert match, line
        assert match[2] == tether.checksum(match[1]), line
        assert "inf" not in match[1].lower() and "nan" not in match[1].lower(), line


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

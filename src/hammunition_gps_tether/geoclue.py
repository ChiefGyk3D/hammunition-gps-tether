# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""The few GeoClue facts the tether needs (D-069 in Hammunition's DECISIONS.md).

The Hammunition engine's ``hardware apply`` writes GeoClue's drop-in and the
tmpfiles line that makes the socket's directory. This module only reads the
drop-in to decide whether the socket is on by default; it writes nothing.
"""

from __future__ import annotations

from pathlib import Path

#: Read after ``/etc/geoclue/geoclue.conf``; present once ``hardware apply`` ran.
DROPIN = "/etc/geoclue/conf.d/90-hammunition-gps.conf"

#: Makes the socket's directory at every boot (``/run`` is a tmpfs).
TMPFILES = "/etc/tmpfiles.d/hammunition-gps.conf"

#: Where the tether listens for GeoClue when the drop-in is in place.
SOCKET = "/run/hammunition-gps/nmea.sock"

#: The group GeoClue's daemon runs as.
GROUP = "geoclue"

#: First line of every file the engine writes; ours is recognised by it.
HEADER = "# Written by `hammunition hardware apply` (D-069)."


def configured() -> bool:
    """Whether the engine has told GeoClue to read the tether's socket."""
    try:
        text = Path(DROPIN).read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return False
    return text.startswith(HEADER)

# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""The repository's own promises: one version, one unit file, the README's flags."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from hammunition_gps_tether import __version__, cli

ROOT = Path(__file__).resolve().parent.parent


def test_the_version_is_one_number() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "hammunition_gps_tether", "--version"],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONPATH": str(ROOT / "src")},
    ).stdout
    assert out.strip() == f"hammunition-gps-tether {__version__}"
    assert re.search(
        rf"^## \[{re.escape(__version__)}\]", (ROOT / "CHANGELOG.md").read_text(), re.M
    )


def test_the_user_unit_has_what_a_user_service_needs() -> None:
    unit = (ROOT / "systemd" / "hammunition-gps-tether.service").read_text()
    assert re.search(r"^Description=\S", unit, re.M)
    assert re.search(r"^ExecStart=\S*hammunition-gps-tether$", unit, re.M)
    assert "Restart=on-failure" in unit and "RestartSec=5" in unit
    assert "WantedBy=default.target" in unit
    assert re.search(r"^RestartPreventExitStatus=3$", unit, re.M), "refusals exit 3, crashes 1"
    assert "User=" not in unit, "a user unit runs as the user; User= is for system units"


def test_the_readme_documents_every_flag() -> None:
    readme = (ROOT / "README.md").read_text()
    flags = {
        option
        for action in cli.build_parser()._actions
        for option in action.option_strings
        if option.startswith("--") and option != "--help"
    }
    assert flags >= {"--gpsd", "--port", "--position-port", "--nmea-socket"}
    for flag in sorted(flags):
        assert f"`{flag}" in readme, f"README does not document {flag}"

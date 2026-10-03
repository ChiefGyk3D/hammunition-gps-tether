# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

"""The ``hammunition-gps-tether`` command: options, refusals, the GeoClue socket.

Moved from the engine's ``tests/test_maps_tools.py``; every listener is a
stand-in or a loopback socket on a random port.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hammunition_gps_tether import cli


def _tether_calls(
    monkeypatch: pytest.MonkeyPatch, *, fail: BaseException | None = None
) -> list[str]:
    """Stand-ins for the listener and the server; no socket is opened."""

    import hammunition_gps_tether.tether as tether

    calls: list[str] = []

    class Listener:
        def close(self) -> None:
            calls.append("closed")

    def listen(port: int = tether.PORT) -> socket.socket:
        calls.append(f"listen {port}")
        if isinstance(fail, OSError):
            raise fail
        return Listener()  # type: ignore[return-value]

    def serve(listener: object, **kwargs: object) -> None:
        gpsd = kwargs.get("gpsd", tether.GPSD)
        calls.append("serve" if gpsd == tether.GPSD else f"serve gpsd {gpsd}")
        if fail is not None:
            raise fail

    monkeypatch.setattr(tether, "listen", listen)
    monkeypatch.setattr(tether, "serve", serve)
    return calls


def test_gps_tether_prints_where_to_connect_and_serves_until_ctrl_c(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    calls = _tether_calls(monkeypatch, fail=KeyboardInterrupt())
    assert cli.main([]) == cli.EXIT_OK
    assert calls == ["listen 10110", "listen 10111", "serve", "closed", "closed"]
    out = capsys.readouterr().out
    assert "host 127.0.0.1, port 10110" in out
    assert "http://127.0.0.1:10111/position" in out


def test_gps_tether_names_a_port_already_in_use(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import errno

    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    calls = _tether_calls(monkeypatch, fail=OSError(errno.EADDRINUSE, "Address already in use"))
    assert cli.main([]) == 3
    assert calls == ["listen 10110"]
    err = capsys.readouterr().err
    assert "Address already in use" in err and "127.0.0.1 port 10110" in err


def test_gps_tether_refuses_root(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    calls = _tether_calls(monkeypatch)
    assert cli.main([]) == 3
    assert calls == []
    assert "not as root" in capsys.readouterr().err


def test_gps_tether_takes_another_port_and_a_remote_gpsd(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    calls = _tether_calls(monkeypatch, fail=KeyboardInterrupt())
    argv = ["--port", "10112", "--gpsd", "[2001:db8::7]:3000"]
    assert cli.main(argv) == cli.EXIT_OK
    assert calls == [
        "listen 10112",
        "listen 10111",
        "serve gpsd ('2001:db8::7', 3000)",
        "closed",
        "closed",
    ]
    out = capsys.readouterr().out
    assert "host 127.0.0.1, port 10112" in out
    assert "gpsd at [2001:db8::7] port 3000" in out


@pytest.mark.parametrize(
    ("argv", "words"),
    [
        (["--port", "1023"], "--port 1023"),
        (["--port", "65536"], "--port 65536"),
        (["--port", "ten"], "--port ten"),
        (["--gpsd", "::1"], "in brackets"),
        (["--gpsd", "pi.local:0"], "1 to 65535"),
        (["--gpsd", ""], "needs a host"),
        (["--position-port", "80"], "--position-port 80"),
        (["--port", "10111"], "are the same port"),
    ],
)
def test_gps_tether_refuses_a_bad_option_by_name_and_opens_nothing(
    argv: list[str],
    words: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    calls = _tether_calls(monkeypatch)
    assert cli.main([*argv]) == 3
    assert calls == []
    assert words in capsys.readouterr().err


def test_gps_tether_reaches_a_fake_gpsd_through_the_gpsd_option(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole command, end to end: a fake gpsd on a random loopback port
    named with --gpsd, the tether on a spare --port, a real client."""
    import socket
    import threading
    import time

    import hammunition_gps_tether.tether as tether
    from tests.test_tether import FIX_3D, FakeGpsd, _json

    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    gpsd = FakeGpsd(_json({"class": "VERSION"}, FIX_3D), repeat=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        position_port = probe.getsockname()[1]  # not 10111: a live tether may hold it
    stop = threading.Event()
    real_serve = tether.serve
    bound: list[tuple[str, int]] = []

    def serve(listener: socket.socket, **kwargs: object) -> None:
        bound.append(listener.getsockname())
        real_serve(listener, stop=stop, poll=0.02, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(tether, "serve", serve)
    argv = ["--gpsd", f"127.0.0.1:{gpsd.address[1]}", "--port", str(port)]
    argv += ["--position-port", str(position_port), "--no-nmea-socket"]
    result: list[int] = []
    thread = threading.Thread(target=lambda: result.append(cli.main(argv)), daemon=True)
    thread.start()
    try:
        for _ in range(250):
            if bound:
                break
            time.sleep(0.02)
        assert bound == [("127.0.0.1", port)], "still loopback only"
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            assert client.makefile("rb").readline().startswith(b"$GPRMC,140509.25,A,")
    finally:
        stop.set()
        thread.join(timeout=5)
        gpsd.close()
    assert result == [cli.EXIT_OK]
    assert gpsd.received == [tether.WATCH]
    assert f"gpsd at 127.0.0.1 port {gpsd.address[1]}" in capsys.readouterr().out


def _socket_calls(
    monkeypatch: pytest.MonkeyPatch, *, unix_fails: BaseException | None = None
) -> list[str]:
    """Stand-ins for both listeners, the server and the socket's removal."""

    import hammunition_gps_tether.tether as tether

    calls: list[str] = []

    class Listener:
        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            calls.append(f"closed {self.name}")

    def listen(port: int = tether.PORT) -> socket.socket:
        calls.append(f"listen {port}")
        return Listener(str(port))  # type: ignore[return-value]

    def listen_unix(path: str, **kwargs: object) -> tuple[socket.socket, tuple[int, int]]:
        calls.append(f"listen_unix {path}")
        if unix_fails is not None:
            raise unix_fails
        return Listener("unix"), (1, 2)  # type: ignore[return-value]

    def close_unix(listener: object, path: str, identity: tuple[int, int]) -> None:
        calls.append(f"close_unix {path} {identity}")

    def serve(listener: object, **kwargs: object) -> None:
        calls.append("serve with unix" if kwargs.get("unix") is not None else "serve")
        raise KeyboardInterrupt

    monkeypatch.setattr(tether, "listen", listen)
    monkeypatch.setattr(tether, "listen_unix", listen_unix)
    monkeypatch.setattr(tether, "close_unix", close_unix)
    monkeypatch.setattr(tether, "serve", serve)
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    return calls


def _our_dropin() -> None:
    from hammunition_gps_tether import geoclue

    Path(geoclue.DROPIN).parent.mkdir(parents=True)
    Path(geoclue.DROPIN).write_text(geoclue.HEADER + "\n")


def test_without_the_geoclue_files_no_socket_is_served(
    monkeypatch: pytest.MonkeyPatch, geoclue_files: Path
) -> None:
    calls = _socket_calls(monkeypatch)
    assert cli.main([]) == cli.EXIT_OK
    assert not any("unix" in call for call in calls)


def test_with_the_geoclue_files_the_socket_is_served_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], geoclue_files: Path
) -> None:
    """The launcher runs `hammunition-gps-tether` with no option; the
    drop-in's presence is what turns the socket on, so the menu entry needs no
    second form."""
    from hammunition_gps_tether import geoclue

    _our_dropin()
    calls = _socket_calls(monkeypatch)
    assert cli.main([]) == cli.EXIT_OK
    assert calls == [
        "listen 10110",
        "listen 10111",
        f"listen_unix {geoclue.SOCKET}",
        "serve with unix",
        "closed 10110",
        "closed 10111",
        f"close_unix {geoclue.SOCKET} (1, 2)",
    ]
    assert geoclue.SOCKET in capsys.readouterr().out


def test_no_nmea_socket_leaves_it_off_with_the_files_in_place(
    monkeypatch: pytest.MonkeyPatch, geoclue_files: Path
) -> None:
    _our_dropin()
    calls = _socket_calls(monkeypatch)
    assert cli.main(["--no-nmea-socket"]) == cli.EXIT_OK
    assert not any("unix" in call for call in calls)


def test_an_explicit_socket_is_served_without_the_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = _socket_calls(monkeypatch)
    path = str(tmp_path / "n.sock")
    assert cli.main(["--nmea-socket", path]) == cli.EXIT_OK
    assert f"listen_unix {path}" in calls and "serve with unix" in calls


def test_an_explicit_socket_that_cannot_be_made_stops_the_tether(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    calls = _socket_calls(monkeypatch, unix_fails=FileNotFoundError(2, "No such file or directory"))
    path = str(tmp_path / "missing" / "n.sock")
    assert cli.main(["--nmea-socket", path]) == 3
    assert "serve" not in " ".join(calls)
    assert "closed 10110" in calls and "closed 10111" in calls
    assert path in capsys.readouterr().err


def test_the_default_socket_failing_is_a_note_and_tcp_still_serves(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], geoclue_files: Path
) -> None:
    """After a reboot before systemd-tmpfiles ran, say: QMapShack keeps working."""
    _our_dropin()
    calls = _socket_calls(monkeypatch, unix_fails=FileNotFoundError(2, "No such file or directory"))
    assert cli.main([]) == cli.EXIT_OK
    assert "serve" in calls
    err = capsys.readouterr().err
    assert "systemd-tmpfiles --create" in err and "GeoClue" in err


def test_both_socket_options_at_once_are_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _socket_calls(monkeypatch)
    argv = ["--nmea-socket", "/x/n.sock", "--no-nmea-socket"]
    assert cli.main(argv) == 3
    assert calls == []
    assert "--no-nmea-socket" in capsys.readouterr().err


def test_sigterm_stops_the_real_program_cleanly_and_removes_the_socket(short_dir: Path) -> None:
    """systemd stops a service with SIGTERM: exit 0, the unix socket gone, no traceback."""
    import signal
    import subprocess
    import sys

    def spare() -> int:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    path = short_dir / "nmea.sock"
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hammunition_gps_tether",
            "--port",
            str(spare()),
            "--position-port",
            str(spare()),
            "--nmea-socket",
            str(path),
        ],
        env={"PYTHONPATH": str(root / "src")},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(250):
            if path.exists():
                break
            time.sleep(0.02)
        assert path.exists(), "the tether never made its socket"
        time.sleep(0.2)  # inside serve(), where a SIGTERM held back since startup is let in
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=10)
    finally:
        proc.kill()
    assert proc.returncode == 0, err
    assert "Traceback" not in err and "Stopped." in err
    assert not path.exists()
    assert "port" in out


# The exit codes a unit's RestartPreventExitStatus=3 reads: 0 stopped cleanly,
# 1 an uncaught crash (retried), 2 usage (argparse's own), 3 a refusal (not retried).


def _run_cli(*argv: str, prelude: str = "") -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parent.parent
    code = f"import sys\n{prelude}\nfrom hammunition_gps_tether import cli\nsys.exit(cli.main(sys.argv[1:]))\n"
    return subprocess.run(
        [sys.executable, "-c", code, *argv],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PYTHONPATH": str(root / "src"), "PATH": os.environ.get("PATH", "")},
    )


def test_the_refusal_code_is_three() -> None:
    assert cli.EXIT_REFUSED == 3
    assert cli.EXIT_OK == 0


def test_a_port_really_in_use_exits_3_with_one_line() -> None:
    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        port = held.getsockname()[1]
        done = _run_cli("--port", str(port), "--no-nmea-socket")
    assert done.returncode == 3, done.stderr
    assert len(done.stderr.strip().splitlines()) == 1
    assert "cannot listen" in done.stderr and "Traceback" not in done.stderr


def test_a_position_port_really_in_use_exits_3() -> None:
    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        taken = held.getsockname()[1]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        done = _run_cli("--port", str(free), "--position-port", str(taken), "--no-nmea-socket")
    assert done.returncode == 3, done.stderr
    assert "position" in done.stderr and "Traceback" not in done.stderr


def test_a_live_unix_socket_exits_3(short_dir: Path) -> None:
    short = short_dir / "n.sock"
    with socket.socket(socket.AF_UNIX) as held:
        held.bind(str(short))
        held.listen(1)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        with socket.socket() as probe2:
            probe2.bind(("127.0.0.1", 0))
            free2 = probe2.getsockname()[1]
        done = _run_cli(
            "--port", str(free), "--position-port", str(free2), "--nmea-socket", str(short)
        )
    assert done.returncode == 3, done.stderr
    assert "another tether" in done.stderr and "Traceback" not in done.stderr


def test_a_bad_gpsd_spec_exits_3() -> None:
    done = _run_cli("--gpsd", "::1")
    assert done.returncode == 3 and "in brackets" in done.stderr


def test_an_unknown_flag_keeps_argparses_exit_2() -> None:
    done = _run_cli("--no-such-flag")
    assert done.returncode == 2 and "usage:" in done.stderr


def test_an_uncaught_crash_exits_1_so_the_unit_retries_it() -> None:
    prelude = (
        "import os\n"
        "os.geteuid = lambda: 1000\n"
        "import hammunition_gps_tether.tether as t\n"
        "def boom(*a, **k):\n    raise RuntimeError('bug')\n"
        "t.serve = boom\n"
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free = probe.getsockname()[1]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free2 = probe.getsockname()[1]
    done = _run_cli(
        "--port", str(free), "--position-port", str(free2), "--no-nmea-socket", prelude=prelude
    )
    assert done.returncode == 1 and "RuntimeError: bug" in done.stderr

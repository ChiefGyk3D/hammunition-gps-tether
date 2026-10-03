# Hammunition GPS tether

Serves your GPS receiver's position, from [gpsd](https://gpsd.io/), as NMEA on
127.0.0.1 only, for programs that cannot talk to gpsd themselves: QMapShack's
*GPS TCP/IP* source, [Hammunition](https://github.com/ChiefGyk3D/Hammunition)'s
offline browser map, and GeoClue (so CoMaps knows where you are). Standard
library only, runs as you, never as root, GPL-3.0-or-later.

It was `hammunition maps gps-tether` inside the engine; it is its own project
now so it can run as a service and be released on its own. The engine installs it.

## What it serves

| Where | What | Read by |
|---|---|---|
| `127.0.0.1:10110` (TCP) | NMEA 0183, `$GPRMC` and `$GPGGA`, one pair per gpsd fix | QMapShack, anything that reads NMEA from a TCP host |
| `127.0.0.1:10111` (HTTP) | `GET /position`, a server-sent event stream | the offline browser map (`hammunition reference serve`) |
| the `--nmea-socket` unix socket | the same NMEA, mode 0660, in GeoClue's group | GeoClue's network-NMEA source, so CoMaps |

Loopback only, whatever the options say. A position is where you are and it is
served without authentication; another machine reaches it with `ssh -L`. Any number
of clients may connect at once and each gets every sentence. One gpsd watch is opened
when the first client connects and closed when the last leaves. A client that stops
reading is dropped alone. With no fix, it says so plainly instead of sending nothing.

## Run it

```
hammunition-gps-tether
```

Ctrl-C stops it. Options:

- `--gpsd HOST[:PORT]` reads a gpsd on another machine (an IPv6 address goes in
  brackets). Default `127.0.0.1:2947`.
- `--port N` serves NMEA on port N, 1024 to 65535, when 10110 is taken.
- `--position-port N` serves `/position` on port N. Default 10111.
- `--nmea-socket PATH` also serves a unix socket at PATH for GeoClue. The default
  is `/run/hammunition-gps/nmea.sock` once `hammunition hardware apply` has set
  GeoClue up, and off otherwise.
- `--no-nmea-socket` leaves the socket off even where that has been done.
- `--version`.

It prints where to connect. In QMapShack: Realtime, Add source, *GPS TCP/IP*;
host `127.0.0.1`, port `10110`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | stopped cleanly (Ctrl-C or SIGTERM) |
| 1 | an uncaught crash, a bug; the unit retries it every 5 s |
| 2 | a usage error: an unknown flag or a missing value (argparse's own) |
| 3 | a refusal, with its one-line message: port 10110 or 10111 or the unix socket already in use, run as root, an unusable `--gpsd`, `--port` or `--position-port` value, opposite socket options; the unit does not retry it |

## Run it as a service

`systemd/hammunition-gps-tether.service` is a user unit (`Restart=on-failure`
and `RestartPreventExitStatus=3`, started at login). It runs `%h/.local/bin/hammunition-gps-tether`, where
`pipx install` or `pip install --user` puts the program. This unit is for a
pip/pipx installation; the engine's install does not use it.

```
make install-user
systemctl --user daemon-reload && systemctl --user enable --now hammunition-gps-tether.service
```

`make install-user` only copies the unit and prints the second line; it does not
enable or start anything. The service and a tether started by hand cannot share
port 10110. A stop (SIGTERM) removes the unix socket, as Ctrl-C does.

## How the engine installs it

Hammunition's catalog installs the sha256-pinned tag tarball as a binary source
tree at `/usr/local/share/hammunition/gps-tether`; nothing is built or installed
with pip. It runs in place with
`/usr/bin/env PYTHONPATH=/usr/local/share/hammunition/gps-tether/src /usr/bin/python3 -P -m hammunition_gps_tether`.
The engine renders its own `hammunition-gps-tether.service` user unit in
`~/.config/systemd/user/` with that `ExecStart`; it has the same name as this
repository's unit and also listens on port 10110, so use one installation, not
both. The engine's install enables its unit but does not start it: it starts at
the next login, or now with
`systemctl --user start hammunition-gps-tether.service`. The install also writes
a mode-0600 row to `~/.config/hammunition/devctl-services.yaml`, the service
list used by `hammunition services` and the tray. `hammunition maps gps-tether`
runs the installed tree (or a pip-installed executable); if neither is present,
it refuses and points to `hammunition install gps-tether`. The root-owned
GeoClue files (a `conf.d` drop-in and a tmpfiles line for the socket's
directory) are written by `hammunition hardware apply`, not by this program,
which only reads the drop-in to decide whether the socket is on by default.

## Develop

```
make venv
make check
```

`make check` is ruff, `mypy --strict` and pytest, which CI runs too. The suite
blocks every socket but loopback; every coordinate in it is synthetic.

## Credits

The tether comes from [Hammunition](https://github.com/ChiefGyk3D/Hammunition)
(Renegade Penguin LLC), where its decisions are recorded (D-061, D-069, D-071).

---

## 💝 Support This Project

If you find Hammunition useful, consider supporting continued development.
Everything is also collected at **[support.chiefgyk3d.com](https://support.chiefgyk3d.com)**.

### Recurring Support

<div align="center">
<table>
  <tr>
    <td align="center" width="150">
      <a href="https://patreon.com/chiefgyk3d" title="Patreon">
        <img src="media/icons/patreon.svg" width="36" height="36" alt="Patreon"><br>
        <sub><b>Patreon</b></sub>
      </a>
    </td>
    <td align="center" width="150">
      <a href="https://streamelements.com/chiefgyk3d/tip" title="StreamElements">
        <img src="media/streamelements.png" width="36" height="36" alt="StreamElements"><br>
        <sub><b>StreamElements</b></sub>
      </a>
    </td>
    <td align="center" width="150">
      <a href="https://shop.chiefgyk3d.com/" title="Merch Store">
        <img src="media/icons/merch.svg" width="36" height="36" alt="Merch"><br>
        <sub><b>Merch Store</b></sub>
      </a>
    </td>
  </tr>
</table>
</div>

### Cryptocurrency Tips

<div align="center">
<table>
  <tr>
    <td><img src="media/icons/bitcoin.svg" width="28" height="28" alt="Bitcoin">&nbsp;<b>Bitcoin</b><br><code>bc1qztdzcy2wyavj2tsuandu4p0tcklzttvdnzalla</code></td>
  </tr>
  <tr>
    <td><img src="media/icons/monero.svg" width="28" height="28" alt="Monero">&nbsp;<b>Monero</b><br><code>84Y34QubRwQYK2HNviezeH9r6aRcPvgWmKtDkN3EwiuVbp6sNLhm9ffRgs6BA9X1n9jY7wEN16ZEpiEngZbecXseUrW8SeQ</code></td>
  </tr>
  <tr>
    <td><img src="media/icons/ethereum.svg" width="28" height="28" alt="Ethereum">&nbsp;<b>Ethereum</b><br><code>0x554f18cfB684889c3A60219BDBE7b050C39335ED</code></td>
  </tr>
  <tr>
    <td><img src="media/icons/solana.svg" width="28" height="28" alt="Solana">&nbsp;<b>Solana</b><br><code>5T8h3HbyvHgLxwXgchRYbHSqRjZyAr8J7uwjLN9Fh8Jh</code></td>
  </tr>
</table>
</div>

---

## 👤 Author & Socials

<div align="center">
<table>
  <tr>
    <td align="center" width="90"><a href="https://social.chiefgyk3d.com/@chiefgyk3d" title="Mastodon"><img src="media/icons/mastodon.svg" width="30" height="30" alt="Mastodon"><br><sub>Mastodon</sub></a></td>
    <td align="center" width="90"><a href="https://bsky.app/profile/chiefgyk3d.com" title="Bluesky"><img src="media/icons/bluesky.svg" width="30" height="30" alt="Bluesky"><br><sub>Bluesky</sub></a></td>
    <td align="center" width="90"><a href="https://twitch.tv/chiefgyk3d" title="Twitch"><img src="media/icons/twitch.svg" width="30" height="30" alt="Twitch"><br><sub>Twitch</sub></a></td>
    <td align="center" width="90"><a href="https://www.youtube.com/channel/UCvFY4KyqVBuYd7JAl3NRyiQ" title="YouTube"><img src="media/icons/youtube.svg" width="30" height="30" alt="YouTube"><br><sub>YouTube</sub></a></td>
    <td align="center" width="90"><a href="https://kick.com/chiefgyk3d" title="Kick"><img src="media/icons/kick.svg" width="30" height="30" alt="Kick"><br><sub>Kick</sub></a></td>
    <td align="center" width="90"><a href="https://www.tiktok.com/@chiefgyk3d" title="TikTok"><img src="media/icons/tiktok.svg" width="30" height="30" alt="TikTok"><br><sub>TikTok</sub></a></td>
    <td align="center" width="90"><a href="https://www.instagram.com/chiefgyk3d" title="Instagram"><img src="media/icons/instagram.svg" width="30" height="30" alt="Instagram"><br><sub>Instagram</sub></a></td>
    <td align="center" width="90"><a href="https://www.threads.net/@chiefgyk3d" title="Threads"><img src="media/icons/threads.svg" width="30" height="30" alt="Threads"><br><sub>Threads</sub></a></td>
    <td align="center" width="90"><a href="https://discord.chiefgyk3d.com" title="Discord"><img src="media/icons/discord.svg" width="30" height="30" alt="Discord"><br><sub>Discord</sub></a></td>
    <td align="center" width="90"><a href="https://matrix-invite.chiefgyk3d.com" title="Matrix"><img src="media/icons/matrix.svg" width="30" height="30" alt="Matrix"><br><sub>Matrix</sub></a></td>
  </tr>
</table>
</div>

<div align="center"><sub>Made with ❤️ by <a href="https://github.com/ChiefGyk3D">ChiefGyk3D</a></sub></div>

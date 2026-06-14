# Remote access hardening

Tethys is a LAN-only appliance that drives physical water pumps. To reach it from
outside the LAN while travelling **without opening the LAN to the internet**, the
intended path is an encrypted overlay network (Tailscale or WireGuard) plus the
application-level hardening described here. This document covers the hardening
(shipped) and points at the transport (operator setup, not code).

> **Do not port-forward Tethys.** Forwarding 8000/5001 puts a pump controller
> directly in front of the internet. Use a VPN/overlay instead — it opens **no**
> inbound ports and encrypts the traffic.

---

## What changed in the app

1. **`DEBUG` is off by default.** Driven by the `TETHYS_DEBUG` env var
   (`"1"` = on). The systemd units set it from the installer's `--debug` flag,
   which now defaults to a production-safe install.
2. **Django `SECRET_KEY`s moved to `globals/secrets.py`** (git-ignored) as
   `API_SECRET_KEY` and `WEB_SECRET_KEY` — unique per install, never committed.
3. **`ALLOWED_HOSTS` is extensible** via the `TETHYS_ALLOWED_HOSTS` env var
   (comma-separated), appended to the base list. Needed once `DEBUG` is off and
   you reach the Pi by a new name (e.g. its Tailscale name).
4. **Reads now require the API key too.** Previously only mutating requests
   (POST/PUT/PATCH/DELETE) needed `X-API-Key`; now every request does, except the
   CORS preflight (`OPTIONS`). The key is the access control; the VPN tunnel is
   the transport encryption.
5. **`/api/initializeDatabase/` is a key-gated `POST`** (was an open `GET` that
   seeded the database).

### Consequence: the dashboard needs the key set

Because reads are gated, a browser with **no API key stored shows no data**. Open
the web UI → **Settings** → paste the API key once (it is kept in the browser's
local storage). The key is printed by the installer; you can also read it from
`globals/secrets.py` (`TETHYS_API_KEY`).

---

## Configuration reference

### Environment variables (read by both Django settings)

| Variable | Default | Meaning |
|---|---|---|
| `TETHYS_DEBUG` | unset (off) | `"1"` runs Django with `DEBUG=True`. Dev only. |
| `TETHYS_ALLOWED_HOSTS` | empty | Comma-separated extra hostnames appended to `ALLOWED_HOSTS`, e.g. `tethys.<tailnet>.ts.net`. |

The base `ALLOWED_HOSTS` is always `tethys.local`, `localhost`, `127.0.0.1`.

### Secrets (`code/master/globals/secrets.py`, git-ignored)

```python
TETHYS_API_KEY = "..."   # access control for every API request
API_SECRET_KEY = "..."   # Django secret for the API app
WEB_SECRET_KEY = "..."   # Django secret for the web app
```

Generate a value with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Upgrading an existing install:** older `secrets.py` files have only
`TETHYS_API_KEY`. The installer appends the two missing Django keys automatically;
to do it by hand, append `API_SECRET_KEY` and `WEB_SECRET_KEY` lines using the
command above.

### Installer flags

```bash
# Production-safe install (DEBUG off), reachable via a Tailscale name:
./install.sh --allowed-hosts="tethys.<tailnet>.ts.net"

# Developer install (TS toolchain + source maps + Django DEBUG on):
./install.sh --debug=true
```

`installServices.sh` accepts the same `--debug` / `--allowed-hosts` flags and
substitutes them into the systemd units (`TETHYS_DEBUG`, `TETHYS_ALLOWED_HOSTS`).
To change them on an existing box, edit the `Environment=` lines in
`/etc/systemd/system/tethys-{api,web}.service` and `daphne.service`, then
`sudo systemctl daemon-reload && sudo systemctl restart tethys-api tethys-web daphne`.

---

## Setting up the transport (Tailscale) — operator step, not code

1. Install Tailscale on the Pi: `curl -fsSL https://tailscale.com/install.sh | sh`
   then `sudo tailscale up`. Authenticate in the browser link it prints.
2. Install Tailscale on your laptop/phone and sign into the **same** tailnet.
3. Note the Pi's tailnet name (`tailscale status`), e.g.
   `tethys.<tailnet>.ts.net`, and add it via `--allowed-hosts=` (re-run the
   service install) or the `Environment=` edit above.
4. From a tailnet device, browse to `http://tethys.<tailnet>.ts.net:8000` and set
   the API key in Settings.

No router ports are opened: Tailscale makes outbound connections and NAT-punches.
Self-hosted WireGuard is the equivalent zero-third-party alternative (it forwards
a single UDP port that exposes only the key-gated WireGuard daemon, never Tethys).

---

## Out of scope / known gaps

- **TLS for the app itself** is unnecessary under the VPN (the tunnel encrypts);
  reads and writes are key-gated regardless.
- The installer's `initializeDatabase` call still targets port `5000` while the
  API gunicorn binds `5001` — a pre-existing discrepancy, left unchanged here.

#!/usr/bin/env python3
"""BG500 (APC Back-UPS Pro 500) -> Home Assistant add-on poller.

Logs into the UPS network management card web UI, scrapes the
Quick UPS Status + per-outlet loads + Recent Device Events from
home.htm, and pushes sensor states into Home Assistant via the
Supervisor core API proxy (SUPERVISOR_TOKEN is injected by the
Supervisor; no long-lived token needed).

Pure Python stdlib. Options come from /data/options.json.
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

OPTIONS_PATH = "/data/options.json"


def load_options():
    opts = {
        "ups_host": "",
        "ups_username": "apc",
        "ups_password": "apc",
        "poll_interval": 60,
    }
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH) as fh:
            opts.update(json.load(fh))
    # env overrides (handy for local testing)
    for key in list(opts):
        env = os.environ.get(key.upper())
        if env is not None:
            opts[key] = type(opts[key])(env)
    return opts


def log(msg):
    print(f"[bg500-poller] {msg}", flush=True)


def fetch_status_page(opts):
    """Log in to the NMC and return the home.htm HTML."""
    if not opts.get("ups_host"):
        raise RuntimeError(
            "ups_host is not configured - set it to your UPS management "
            "card's IP or hostname in the add-on Configuration tab"
        )
    base = f"http://{opts['ups_host']}"
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", "bg500-poller")]

    with opener.open(base + "/", timeout=25) as resp:
        login_page = resp.read().decode("utf-8", "replace")
    m = re.search(r'action="(/NMC/[^"]+/Forms/login1)"', login_page.replace("\r", "").replace("\n", ""))
    if not m:
        raise RuntimeError("login form action not found")
    form = m.group(1)

    data = urllib.parse.urlencode(
        {
            "login_username": opts["ups_username"],
            "login_password": opts["ups_password"],
            "submit": "Log On",
        }
    ).encode()
    req = urllib.request.Request(base + form, data=data)
    with opener.open(req, timeout=25) as resp:
        final_url = resp.geturl()
        html = resp.read().decode("utf-8", "replace")
    m = re.match(r".*/NMC/([^/]+)/home\.htm$", final_url)
    if not m:
        raise RuntimeError(f"login failed, landed on {final_url}")
    session_base = f"{base}/NMC/{m.group(1)}"

    # log out to free the session (best effort)
    try:
        opener.open(session_base + "/logout.htm", timeout=10).read()
    except Exception:
        pass
    return html


def _one(pattern, text, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


def parse(html):
    """Turn home.htm HTML into a list of (entity_id, state, attributes)."""
    html = html.replace("\r", "").replace("\n", "")

    batt_sec = _one(r"<!-- Table of BatteryCapacity -->(.*?)<!-- End of BatteryCapacity -->", html, re.S)
    load_sec = _one(r"<!-- Table of Load -->(.*?)<!-- End of Load -->", html, re.S)
    input_sec = _one(r"<!-- Table of Input Voltage -->(.*?)<!-- End of Input Voltage -->", html, re.S)
    if not (batt_sec and load_sec and input_sec):
        raise RuntimeError("status sections not found (not logged in?)")

    capacity = _one(r"([\d.]+)&nbsp;%", batt_sec)
    runtime = _one(r"(\d+)\s*minutes?", batt_sec)
    energy = _one(r"([\d.]+)&nbsp;kWh", load_sec)
    input_v = _one(r'<td[^>]*>([\d.]+)&nbsp;<span id="langVAC">', input_sec)
    health = _one(r"langBatteryLifeStatus.*?<td[^>]*>\s*([^<]*?)\s*</td>", html, re.S)
    ups_state = _one(r"<li>(UPS is [^<]*)</li>", html)
    alarm_title = _one(r'title="([^"]*)"><img src="images/(?:good|warning|critical)\.gif"', html)
    ev = re.search(
        r'<tr class="clr">\s*<td[^>]*>&nbsp;&nbsp;(\d{4}-\d{2}-\d{2})</td>'
        r"\s*<td[^>]*>(\d{2}:\d{2}:\d{2})</td>\s*<td[^>]*>([^<]*)</td>",
        html,
    )

    for name, val in [("capacity", capacity), ("runtime", runtime),
                      ("energy", energy), ("input", input_v)]:
        if val is None:
            raise RuntimeError(f"parse failed for {name}")

    health = (health or "unknown").replace("&nbsp;", "").strip()
    ups_state = ups_state or "unknown"
    alarm_title = alarm_title or "unknown"
    alarm = "none" if re.search(r"no alarms? present", alarm_title, re.I) else "active"
    last_event = f"{ev.group(1)} {ev.group(2)} \u2014 {ev.group(3)}" if ev else "unknown"
    input_v_f = float(input_v)
    on_battery = "on" if input_v_f < 50 else "off"

    # Per-outlet loads: the page's total is a JS-accumulated placeholder
    # (server renders 0.0 W); each outlet row carries its real draw in a
    # parseFloat() call. Sum them for the total.
    outlets = []
    for m in re.finditer(
        r'<td class="dataName">([^<]+)</td><td>([^<]*)</td>'
        r'<td><script[^>]*>s=\s*parseFloat\(([\d.]+)\+""\)',
        html,
    ):
        outlets.append({"name": m.group(1), "state": m.group(2), "watts": float(m.group(3))})
    if not outlets:
        raise RuntimeError("no outlet rows parsed")
    load_w = round(sum(o["watts"] for o in outlets), 1)

    entities = [
        ("sensor.bg500_battery_capacity", capacity,
         {"unit_of_measurement": "%", "device_class": "battery",
          "state_class": "measurement", "friendly_name": "BG500 Battery Capacity"}),
        ("sensor.bg500_runtime_remaining", runtime,
         {"unit_of_measurement": "min", "device_class": "duration",
          "friendly_name": "BG500 Runtime Remaining"}),
        ("sensor.bg500_load", load_w,
         {"unit_of_measurement": "W", "device_class": "power",
          "state_class": "measurement", "friendly_name": "BG500 Load"}),
        ("sensor.bg500_input_voltage", input_v,
         {"unit_of_measurement": "V", "device_class": "voltage",
          "state_class": "measurement", "friendly_name": "BG500 Input Voltage"}),
        ("sensor.bg500_energy_total", energy,
         {"unit_of_measurement": "kWh", "device_class": "energy",
          "state_class": "total_increasing", "friendly_name": "BG500 Energy Total"}),
        ("sensor.bg500_battery_health", health,
         {"friendly_name": "BG500 Battery Health"}),
        ("sensor.bg500_ups_state", ups_state,
         {"friendly_name": "BG500 UPS State"}),
        ("sensor.bg500_alarm", alarm,
         {"friendly_name": "BG500 Alarm", "detail": alarm_title}),
        ("sensor.bg500_last_event", last_event,
         {"friendly_name": "BG500 Last Event"}),
        ("binary_sensor.bg500_on_battery", on_battery,
         {"friendly_name": "BG500 On Battery"}),
    ]
    for o in outlets:
        slug = re.sub(r"[^a-z0-9]+", "_", o["name"].lower())
        entities.append((
            f"sensor.bg500_load_{slug}", round(o["watts"], 1),
            {"unit_of_measurement": "W", "device_class": "power",
             "state_class": "measurement",
             "friendly_name": f"BG500 Load {o['name']}",
             "outlet_state": o["state"]},
        ))
    return entities


def push(entities):
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    api = os.environ.get("HASS_API_BASE", "http://supervisor/core/api")
    for eid, state, attrs in entities:
        body = json.dumps({"state": str(state), "attributes": attrs}).encode()
        req = urllib.request.Request(
            f"{api}/states/{eid}", data=body, method="POST",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"POST {eid} -> HTTP {resp.status}")


def main():
    opts = load_options()
    interval = int(opts["poll_interval"])
    log(f"polling {opts['ups_host']} every {interval}s")
    while True:
        try:
            entities = parse(fetch_status_page(opts))
            push(entities)
            by_id = {e[0]: e[1] for e in entities}
            log(f"ok: load={by_id['sensor.bg500_load']}W "
                f"batt={by_id['sensor.bg500_battery_capacity']}% "
                f"in={by_id['sensor.bg500_input_voltage']}V "
                f"on_battery={by_id['binary_sensor.bg500_on_battery']}")
        except Exception as exc:  # keep the loop alive; next cycle retries
            log(f"poll failed: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())

# Changelog

## 1.0.3 — 2026-10-21

- Diagnostics: fetch and push are now logged as separate stages (with
  the failing URL/entity and response body), and startup logs whether
  SUPERVISOR_TOKEN is present — to pin down a 401 seen in the field.

## 1.0.2 — 2026-10-21

- Fix startup failure (`python3: not found` in the s6 init log): the
  Docker `python` image keeps python3 in `/usr/local/bin`, which the
  Supervisor's s6 environment doesn't have on PATH. Build from the
  official Home Assistant base-python image
  (`ghcr.io/home-assistant/*-base-python:3.13-alpine3.20`) instead —
  tags verified to exist for aarch64, amd64 and armv7.

## 1.0.1 — 2026-10-21

- Fix add-on build: the `ghcr.io/home-assistant/*-base-python:3.12`
  images don't exist; build from the multi-arch `python:3.12-alpine`
  image instead.
- `ups_host` no longer has a default value — it must be set in the
  add-on configuration (the add-on logs a clear error until it is).

## 1.0.0 — 2026-10-21

- Initial release.
- Polls the BG500 (APC Back-UPS Pro 500) management card web UI:
  battery capacity, runtime remaining, input voltage, lifetime energy,
  battery health, UPS state, alarm state, last device event.
- Per-outlet load sensors (Master, Backup, Smart Outlet 1,
  Smart Outlet 2) plus their sum as the total load — the card's web UI
  computes the total with JavaScript, so it is summed here instead.
- `binary_sensor.bg500_on_battery` derived from input voltage.
- Configurable UPS host, credentials and poll interval.

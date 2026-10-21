# Changelog

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

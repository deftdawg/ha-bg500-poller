# BG500 UPS Poller

Monitor an **APC Back-UPS Pro 500 ("BG500")** UPS from Home Assistant —
battery capacity, runtime, load (total and per-outlet), input voltage,
energy, alarms and on-battery state — polled from the management card's
web UI every 60s.

Runs on the Home Assistant host itself, so outage monitoring keeps
working while the power is out. No long-lived access token required.

See the **Documentation** tab for configuration and the full entity
list.

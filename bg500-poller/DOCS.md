# BG500 UPS Poller

Polls the web UI of an **APC Back-UPS Pro 500 ("BG500")** network
management card (AP9537) and publishes the UPS's power stats into Home
Assistant as sensors, so you can alert on power outages and automate
load-shedding while the battery drains.

Running as an add-on means the polling lives on the Home Assistant host
itself — which is normally on UPS power — so monitoring keeps working
through an outage, unlike a poller running on some other machine that
loses power with the rest of the house.

## How it works

Every poll cycle the add-on:

1. Logs in to the management card's web UI (form login, session cookie).
2. Scrapes the status page: battery capacity, runtime remaining, input
   voltage, lifetime energy, battery health, UPS state, alarm state,
   the most recent device event, and the per-outlet loads from the
   Quick Outlet Status table. (The page's headline load figure is
   accumulated by JavaScript in the browser, so the add-on sums the
   per-outlet values itself.)
3. Pushes the values into Home Assistant as entity states, using the
   Supervisor-injected token. No long-lived access token is stored.
4. Logs out and waits for the next cycle.

The card's SNMP agent exposes no UPS data (only the card's own
configuration MIBs), and its web UI login flow can't be reproduced
with Home Assistant's REST/Scrape integrations — hence this add-on.

## Configuration

```yaml
ups_host: 192.168.1.19
ups_username: apc
ups_password: apc
poll_interval: 60
```

| Option | Default | Description |
| --- | --- | --- |
| `ups_host` | `192.168.1.19` | IP address or hostname of the UPS management card **(set this to your UPS)** |
| `ups_username` | `apc` | Management card user name |
| `ups_password` | `apc` | Management card password |
| `poll_interval` | `60` | Seconds between polls, 15–600 |

## Entities

| Entity | Unit / values |
| --- | --- |
| `binary_sensor.bg500_on_battery` | `on` = on battery (mains lost), `off` = on mains |
| `sensor.bg500_battery_capacity` | % |
| `sensor.bg500_runtime_remaining` | min |
| `sensor.bg500_load` | W (total, sum of outlets) |
| `sensor.bg500_load_master` | W |
| `sensor.bg500_load_backup` | W |
| `sensor.bg500_load_smart_outlet_1` | W |
| `sensor.bg500_load_smart_outlet_2` | W |
| `sensor.bg500_input_voltage` | V |
| `sensor.bg500_energy_total` | kWh (lifetime, `total_increasing`) |
| `sensor.bg500_battery_health` | e.g. `Battery OK` |
| `sensor.bg500_ups_state` | e.g. `UPS is online.` |
| `sensor.bg500_alarm` | `none` / `active` (`detail` attribute has the card's wording) |
| `sensor.bg500_last_event` | Most recent event from the card's home-page event list (may read `unknown` when the list is empty) |

Per-outlet sensors also carry an `outlet_state` attribute (`On`/`Off`).

## Example automations

Outage alert:

```yaml
automation:
  - alias: "BG500: Power outage alert"
    triggers:
      - trigger: state
        entity_id: binary_sensor.bg500_on_battery
        to: "on"
    actions:
      - service: notify.mobile_app_phone
        data:
          title: "Power outage"
          message: >-
            BG500 on battery at {{ states('sensor.bg500_battery_capacity') }}%
            (~{{ states('sensor.bg500_runtime_remaining') }} min runtime).
```

Low-battery load-shedding trigger:

```yaml
automation:
  - alias: "BG500: Low battery — shed loads"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.bg500_battery_capacity
        below: 40
    conditions:
      - condition: state
        entity_id: binary_sensor.bg500_on_battery
        state: "on"
    actions:
      - service: switch.turn_off
        target:
          entity_id: switch.non_essential_loads
```

## Troubleshooting

- **Log shows "login failed"** — check `ups_host`, `ups_username` and
  `ups_password` against the card's web UI in a browser.
- **Log shows "poll failed: ... parse failed"** — the card's firmware
  page layout may have changed; open an issue with the log lines.
- **Entities show stale values** — the add-on pushes on every cycle;
  if Home Assistant restarts, values reappear within one poll interval.

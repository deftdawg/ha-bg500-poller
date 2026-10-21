# BG500 UPS Add-ons for Home Assistant

A Home Assistant add-on repository for monitoring an **APC Back-UPS Pro 500
("BG500")** uninterruptible power supply through its network management
card — including during a power outage, because the add-on runs on the
Home Assistant host itself.

## Add this repository

1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Top-right **⋮ → Repositories**
3. Paste this URL and click **Add**:

   ```
   https://github.com/deftdawg/ha-bg500-poller
   ```

4. Close, refresh the store, and install **BG500 UPS Poller** from the
   new repository section.

## Add-ons

### [BG500 UPS Poller](bg500-poller/DOCS.md)

Polls the UPS management card's web UI every 60s (configurable) and
publishes power sensors into Home Assistant:

| Entity | What it reports |
| --- | --- |
| `binary_sensor.bg500_on_battery` | `on` when mains power is lost |
| `sensor.bg500_battery_capacity` | Battery charge (%) |
| `sensor.bg500_runtime_remaining` | Estimated runtime (min) |
| `sensor.bg500_load` | Total load (W) |
| `sensor.bg500_load_master` | Load on the Master outlet group (W) |
| `sensor.bg500_load_backup` | Load on the Backup outlet group (W) |
| `sensor.bg500_load_smart_outlet_1` | Load on Smart Outlet 1 (W) |
| `sensor.bg500_load_smart_outlet_2` | Load on Smart Outlet 2 (W) |
| `sensor.bg500_input_voltage` | Input (mains) voltage (V) |
| `sensor.bg500_energy_total` | Lifetime energy (kWh) |
| `sensor.bg500_battery_health` | Battery health text (e.g. "Battery OK") |
| `sensor.bg500_ups_state` | UPS state text (e.g. "UPS is online.") |
| `sensor.bg500_alarm` | `none` / `active`, with detail |
| `sensor.bg500_last_event` | Most recent device event from the card's log |

These feed automations directly — e.g. alert when `bg500_on_battery`
turns on, or start load-shedding when `bg500_battery_capacity` drops
below a threshold while on battery.

## Why an add-on?

The BG500's management card (AP9537) exposes **no UPS data over SNMP** —
its agent only serves the card's own configuration MIBs — and its web UI
requires a form login with a session cookie and a per-session URL,
which Home Assistant's built-in REST/Scrape integrations cannot perform.
So the polling logic has to run as code somewhere. An add-on keeps it on
the (UPS-powered) Home Assistant host, and it talks to Home Assistant
with the Supervisor-injected token: **no long-lived access token is
stored anywhere**.

## Configuration

The UPS address and credentials are add-on options — nothing is
hard-coded:

| Option | Default | Description |
| --- | --- | --- |
| `ups_host` | `192.168.1.19` | IP or hostname of the UPS management card |
| `ups_username` | `apc` | Management card user name |
| `ups_password` | `apc` | Management card password |
| `poll_interval` | `60` | Seconds between polls (15–600) |

See [bg500-poller/DOCS.md](bg500-poller/DOCS.md) for full documentation.

## License

MIT — see [LICENSE](LICENSE).

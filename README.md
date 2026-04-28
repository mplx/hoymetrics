# hoymetrics

Polls a Hoymiles solar inverter DTU over the local network and logs output to CSV or exposes it as Prometheus metrics.

## Requirements

- Python 3.10+
- A Hoymiles DTU reachable on the local network

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|---|---|---|
| `DTU_IP` | _(required)_ | IP address of the Hoymiles DTU |
| `FETCH_MODE` | _(unset)_ | Set to `daemon` to enable Prometheus exporter mode |
| `FETCH_INTERVAL` | `60` | Seconds between polls; minimum 10. Unset or `0` = single fetch |
| `LOG_FILE` | _(unset)_ | CSV log file path; if unset, no file is written |
| `PROMETHEUS_PORT` | `9100` | HTTP port for `/metrics` (daemon mode only) |

## Running

### Single fetch

Polls once, prints to stdout, optionally appends a row to the CSV, and exits.

```bash
DTU_IP=192.168.0.100 python hoymetrics/hoymetrics.py
```

### Docker

Pre-built images are available on GHCR:

```bash
docker pull ghcr.io/mplx/hoymetrics:latest
```

**Single fetch:**
```bash
docker run --rm -e DTU_IP=192.168.0.100 ghcr.io/mplx/hoymetrics
```

**Periodic fetch** - runs every `FETCH_INTERVAL` seconds via supervisord:
```bash
docker run -v /your/data:/data -e DTU_IP=192.168.0.100 -e FETCH_INTERVAL=60 ghcr.io/mplx/hoymetrics
```

**Daemon mode** - Prometheus exporter:
```bash
docker run -e DTU_IP=192.168.0.100 -e FETCH_MODE=daemon -e FETCH_INTERVAL=60 -p 9100:9100 ghcr.io/mplx/hoymetrics
```

**Daemon mode with CSV logging:**
```bash
docker run -e DTU_IP=192.168.0.100 -e FETCH_MODE=daemon -e FETCH_INTERVAL=60 \
  -e LOG_FILE=/data/hoymiles_log.csv -v /your/data:/data -p 9100:9100 ghcr.io/mplx/hoymetrics
```

Metrics are available at `http://localhost:9100/metrics`.

### Grafana

A sample dashboard is provided at `grafana/hoymetrics.json`. Import it via "Dashboards" > "Import" and select your Prometheus datasource.

### Unraid

Install via Community Applications by adding `https://github.com/mplx/hoymetrics` as a template repository, then search for "hoymetrics".

## Prometheus metrics

| Metric | Description |
|---|---|
| `hoymetrics_power_watts` | Total PV output in watts |
| `hoymetrics_today_energy_kwh` | Total energy production today in kWh |
| `hoymetrics_total_energy_kwh` | Lifetime total energy production in kWh |
| `hoymetrics_port_power_watts{serial="…", port="N"}` | Per-port power in watts |
| `hoymetrics_port_voltage_volts{serial="…", port="N"}` | Per-port voltage in volts |
| `hoymetrics_port_current_amps{serial="…", port="N"}` | Per-port current in amps |
| `hoymetrics_port_today_energy_kwh{serial="…", port="N"}` | Per-port energy today in kWh |
| `hoymetrics_port_total_energy_kwh{serial="…", port="N"}` | Per-port lifetime energy in kWh |
| `hoymetrics_last_fetch_timestamp` | Unix timestamp of last fetch attempt |
| `hoymetrics_fetch_errors_total` | Counter of failed fetches (exceptions only; inverter offline is not counted) |

## CSV output

When `LOG_FILE` is set, all modes append to the same CSV schema. Port columns are generated dynamically from the inverter's `pv_data`, so the exact columns depend on port count:

```
timestamp, power_w, today_kwh, total_kwh, {serial}_port1_w, {serial}_port1_v, {serial}_port1_a, {serial}_port1_kwh_today, {serial}_port1_kwh_total, ...
```

`{serial}` is the inverter's hex serial number (e.g. `11410001`). Multiple inverters produce separate column groups, each prefixed with their own serial.

When the inverter is offline (e.g. at night), no row is written - the CSV will have a gap for that period. In daemon mode, power gauges are set to zero during offline periods so Prometheus does not report stale non-zero watt values.

If `LOG_FILE` is unset, single fetch prints to stdout only and daemon mode runs as Prometheus-only.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

## Credits

- [suaveolent/hoymiles-wifi](https://github.com/suaveolent/hoymiles-wifi) - MIT License
- [prometheus/client_python](https://github.com/prometheus/client_python) - Apache License 2.0
- [Pictogrammers/MaterialDesign](https://github.com/Templarian/MaterialDesign) - `solar-power-variant` icon - Apache License 2.0

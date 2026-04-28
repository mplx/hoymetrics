import asyncio
import os
import time

from common import fetch, log_to_csv, require_env, validate_interval
from prometheus_client import Counter, Gauge, start_http_server

DTU_IP = require_env("DTU_IP")
FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL", "60"))
validate_interval(FETCH_INTERVAL)
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", "9100"))
LOG_FILE = os.environ.get("LOG_FILE")

power_w        = Gauge("hoymetrics_power_watts",           "Total PV power in watts")
today_kwh      = Gauge("hoymetrics_today_energy_kwh",      "Total energy production today in kWh")
total_kwh      = Gauge("hoymetrics_total_energy_kwh",      "Lifetime total energy production in kWh")
port_power_w   = Gauge("hoymetrics_port_power_watts",      "Per-port power in watts", ["serial", "port"])
port_voltage_v = Gauge("hoymetrics_port_voltage_volts",    "Per-port voltage in volts", ["serial", "port"])
port_current_a = Gauge("hoymetrics_port_current_amps",     "Per-port current in amps", ["serial", "port"])
port_today_kwh = Gauge("hoymetrics_port_today_energy_kwh", "Per-port energy today in kWh", ["serial", "port"])
port_total_kwh = Gauge("hoymetrics_port_total_energy_kwh", "Per-port lifetime energy in kWh", ["serial", "port"])
last_fetch_ts  = Gauge("hoymetrics_last_fetch_timestamp",  "Unix timestamp of last successful fetch")
fetch_errors   = Counter("hoymetrics_fetch_errors_total",  "Number of failed fetches (exceptions only)")

# tracks which (serial, port) label sets have been seen so we can zero them on inverter offline
_known_port_labels: set[tuple[str, str]] = set()


def _set_power_zero():
    power_w.set(0)
    for serial, port in _known_port_labels:
        labels = {"serial": serial, "port": port}
        port_power_w.labels(**labels).set(0)
        port_voltage_v.labels(**labels).set(0)
        port_current_a.labels(**labels).set(0)


def poll_loop():
    while True:
        try:
            data = asyncio.run(fetch(DTU_IP, FETCH_INTERVAL))
            if data:
                power_w.set(data.dtu_power)
                today_kwh.set(data.dtu_daily_energy)
                total_kwh.set(sum(pv.energy_total for pv in data.pv_data))
                for pv in data.pv_data:
                    labels = {"serial": hex(pv.serial_number)[2:], "port": str(pv.port_number)}
                    _known_port_labels.add((labels["serial"], labels["port"]))
                    port_power_w.labels(**labels).set(pv.power)
                    port_voltage_v.labels(**labels).set(pv.voltage)
                    port_current_a.labels(**labels).set(pv.current)
                    port_today_kwh.labels(**labels).set(pv.energy_daily)
                    port_total_kwh.labels(**labels).set(pv.energy_total)
                last_fetch_ts.set(time.time())
                if LOG_FILE:
                    log_to_csv(LOG_FILE, data)
            else:
                _set_power_zero()
                last_fetch_ts.set(time.time())
        except Exception as exc:
            print(f"fetch error: {exc}")
            fetch_errors.inc()
        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    start_http_server(PROMETHEUS_PORT)
    print(f"Prometheus metrics on :{PROMETHEUS_PORT}/metrics, polling every {FETCH_INTERVAL}s")
    poll_loop()

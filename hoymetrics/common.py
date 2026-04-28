import csv
import os

from datetime import datetime
from hoymiles_wifi.dtu import DTU


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Error: {name} environment variable is required")
    return value


def validate_interval(interval, allow_zero=False):
    if interval < 10 and not (allow_zero and interval == 0):
        raise SystemExit("Error: FETCH_INTERVAL must be at least 10 seconds")


async def fetch(dtu_ip, fetch_interval=0):
    dtu = DTU(dtu_ip)
    if 0 < fetch_interval < 35:
        await dtu.async_enable_performance_data_mode()
    return await dtu.async_get_real_data_new()


def _pv_serial(pv):
    return hex(pv.serial_number)[2:]


def log_to_csv(log_file, data):
    base_fields = ["timestamp", "power_w", "today_kwh", "total_kwh"]
    port_fields = []
    for pv in data.pv_data:
        s, n = _pv_serial(pv), pv.port_number
        port_fields += [f"{s}_port{n}_w", f"{s}_port{n}_v", f"{s}_port{n}_a",
                        f"{s}_port{n}_kwh_today", f"{s}_port{n}_kwh_total"]

    row = {
        "timestamp": datetime.now().isoformat(),
        "power_w": data.dtu_power,
        "today_kwh": data.dtu_daily_energy,
        "total_kwh": sum(pv.energy_total for pv in data.pv_data),
    }
    for pv in data.pv_data:
        s, n = _pv_serial(pv), pv.port_number
        row[f"{s}_port{n}_w"] = pv.power
        row[f"{s}_port{n}_v"] = pv.voltage
        row[f"{s}_port{n}_a"] = pv.current
        row[f"{s}_port{n}_kwh_today"] = pv.energy_daily
        row[f"{s}_port{n}_kwh_total"] = pv.energy_total

    with open(log_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_fields + port_fields)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(row)

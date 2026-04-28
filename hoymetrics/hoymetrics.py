import asyncio
import os

from common import fetch, log_to_csv, require_env, validate_interval

DTU_IP = require_env("DTU_IP")
LOG_FILE = os.environ.get("LOG_FILE")
FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL", "0"))
validate_interval(FETCH_INTERVAL, allow_zero=True)


async def main():
    data = await fetch(DTU_IP, FETCH_INTERVAL)
    if data:
        if LOG_FILE:
            log_to_csv(LOG_FILE, data)
        print(f"{data.dtu_power}W, today {data.dtu_daily_energy}kWh")
    else:
        print("No response from inverter")


asyncio.run(main())

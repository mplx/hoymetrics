import asyncio
import csv
import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from common import fetch, log_to_csv, require_env, validate_interval


# --- require_env ---

def test_require_env_returns_value(monkeypatch):
    monkeypatch.setenv("DTU_IP", "192.168.1.100")
    assert require_env("DTU_IP") == "192.168.1.100"


def test_require_env_missing_raises(monkeypatch):
    monkeypatch.delenv("DTU_IP", raising=False)
    with pytest.raises(SystemExit, match="DTU_IP"):
        require_env("DTU_IP")


def test_require_env_empty_raises(monkeypatch):
    monkeypatch.setenv("DTU_IP", "")
    with pytest.raises(SystemExit):
        require_env("DTU_IP")


# --- validate_interval ---

def test_validate_interval_valid():
    validate_interval(60)


def test_validate_interval_minimum_boundary():
    validate_interval(10)


def test_validate_interval_below_minimum_raises():
    with pytest.raises(SystemExit, match="10 seconds"):
        validate_interval(9)


def test_validate_interval_one_raises():
    with pytest.raises(SystemExit):
        validate_interval(1)


def test_validate_interval_zero_raises_by_default():
    with pytest.raises(SystemExit):
        validate_interval(0)


def test_validate_interval_zero_allowed():
    validate_interval(0, allow_zero=True)


def test_validate_interval_nonzero_below_minimum_still_raises_with_allow_zero():
    with pytest.raises(SystemExit):
        validate_interval(5, allow_zero=True)


# --- fetch ---

def _make_dtu_instance(return_value=None):
    instance = MagicMock()
    instance.async_get_real_data_new = AsyncMock(return_value=return_value or MagicMock())
    instance.async_enable_performance_data_mode = AsyncMock()
    return instance


def test_fetch_returns_dtu_data():
    mock_data = MagicMock()
    with patch("common.DTU") as MockDTU:
        MockDTU.return_value = _make_dtu_instance(mock_data)
        result = asyncio.run(fetch("10.0.0.1", fetch_interval=60))
    assert result is mock_data


def test_fetch_no_performance_mode_at_threshold():
    with patch("common.DTU") as MockDTU:
        instance = _make_dtu_instance()
        MockDTU.return_value = instance
        asyncio.run(fetch("10.0.0.1", fetch_interval=35))
        instance.async_enable_performance_data_mode.assert_not_called()


def test_fetch_enables_performance_mode_below_threshold():
    with patch("common.DTU") as MockDTU:
        instance = _make_dtu_instance()
        MockDTU.return_value = instance
        asyncio.run(fetch("10.0.0.1", fetch_interval=34))
        instance.async_enable_performance_data_mode.assert_called_once()


def test_fetch_no_performance_mode_for_zero_interval():
    with patch("common.DTU") as MockDTU:
        instance = _make_dtu_instance()
        MockDTU.return_value = instance
        asyncio.run(fetch("10.0.0.1", fetch_interval=0))
        instance.async_enable_performance_data_mode.assert_not_called()


def test_fetch_passes_dtu_ip():
    with patch("common.DTU") as MockDTU:
        MockDTU.return_value = _make_dtu_instance()
        asyncio.run(fetch("192.168.0.100"))
        MockDTU.assert_called_once_with("192.168.0.100")


# --- log_to_csv ---

SERIAL_A = 0x11410001
SERIAL_B = 0x11410002
SERIAL_A_HEX = hex(SERIAL_A)[2:]  # "11410001"
SERIAL_B_HEX = hex(SERIAL_B)[2:]  # "11410002"


def _make_pv(port_number, power, voltage=230, current=5, energy_daily=100,
             energy_total=5000, serial_number=SERIAL_A):
    pv = MagicMock()
    pv.serial_number = serial_number
    pv.port_number = port_number
    pv.power = power
    pv.voltage = voltage
    pv.current = current
    pv.energy_daily = energy_daily
    pv.energy_total = energy_total
    return pv


def _make_data(dtu_power=150, dtu_daily_energy=1200, pv_data=None):
    data = MagicMock()
    data.dtu_power = dtu_power
    data.dtu_daily_energy = dtu_daily_energy
    data.pv_data = pv_data if pv_data is not None else [_make_pv(1, 90), _make_pv(2, 60)]
    return data


def test_log_to_csv_creates_file_with_header(tmp_path):
    log_file = tmp_path / "log.csv"
    log_to_csv(str(log_file), _make_data())
    with open(log_file) as f:
        lines = f.readlines()
    assert lines[0].startswith("timestamp,")


def test_log_to_csv_writes_base_values(tmp_path):
    log_file = tmp_path / "log.csv"
    log_to_csv(str(log_file), _make_data(dtu_power=200, dtu_daily_energy=2500))
    with open(log_file) as f:
        row = next(csv.DictReader(f))
    assert row["power_w"] == "200"
    assert row["today_kwh"] == "2500"


def test_log_to_csv_writes_per_port_values(tmp_path):
    log_file = tmp_path / "log.csv"
    pv_data = [
        _make_pv(1, power=120, voltage=235, current=6, energy_daily=800, energy_total=4000),
        _make_pv(2, power=80,  voltage=233, current=4, energy_daily=500, energy_total=3000),
    ]
    log_to_csv(str(log_file), _make_data(pv_data=pv_data))
    with open(log_file) as f:
        row = next(csv.DictReader(f))
    assert row[f"{SERIAL_A_HEX}_port1_w"] == "120"
    assert row[f"{SERIAL_A_HEX}_port1_v"] == "235"
    assert row[f"{SERIAL_A_HEX}_port1_a"] == "6"
    assert row[f"{SERIAL_A_HEX}_port1_kwh_today"] == "800"
    assert row[f"{SERIAL_A_HEX}_port1_kwh_total"] == "4000"
    assert row[f"{SERIAL_A_HEX}_port2_w"] == "80"
    assert row[f"{SERIAL_A_HEX}_port2_v"] == "233"


def test_log_to_csv_two_inverters_separate_columns(tmp_path):
    log_file = tmp_path / "log.csv"
    pv_data = [
        _make_pv(1, power=100, serial_number=SERIAL_A),
        _make_pv(1, power=80,  serial_number=SERIAL_B),
    ]
    log_to_csv(str(log_file), _make_data(pv_data=pv_data))
    with open(log_file) as f:
        row = next(csv.DictReader(f))
    assert row[f"{SERIAL_A_HEX}_port1_w"] == "100"
    assert row[f"{SERIAL_B_HEX}_port1_w"] == "80"


def test_log_to_csv_total_kwh_is_sum_of_ports(tmp_path):
    log_file = tmp_path / "log.csv"
    pv_data = [_make_pv(1, power=90, energy_total=3000), _make_pv(2, power=60, energy_total=2000)]
    log_to_csv(str(log_file), _make_data(pv_data=pv_data))
    with open(log_file) as f:
        row = next(csv.DictReader(f))
    assert row["total_kwh"] == "5000"


def test_log_to_csv_appends_rows(tmp_path):
    log_file = tmp_path / "log.csv"
    log_to_csv(str(log_file), _make_data())
    log_to_csv(str(log_file), _make_data())
    with open(log_file) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2


def test_log_to_csv_no_duplicate_header(tmp_path):
    log_file = tmp_path / "log.csv"
    log_to_csv(str(log_file), _make_data())
    log_to_csv(str(log_file), _make_data())
    with open(log_file) as f:
        lines = f.readlines()
    assert sum(1 for l in lines if l.startswith("timestamp,")) == 1


def test_log_to_csv_empty_pv_data(tmp_path):
    log_file = tmp_path / "log.csv"
    log_to_csv(str(log_file), _make_data(pv_data=[]))
    with open(log_file) as f:
        row = next(csv.DictReader(f))
    assert row["power_w"] == "150"
    assert row["total_kwh"] == "0"

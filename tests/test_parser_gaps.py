"""Two Altus Metrum logs in one flight, and the Blue Raven summary CSV."""

from __future__ import annotations

import json
import shutil

import pandas as pd
from conftest import DATA, copy_flight
from typer.testing import CliRunner

from pfa.cli import _sniff_kind, app
from pfa.parsers.blueraven_summary import blueraven_identity

runner = CliRunner()

TM_0003 = DATA / "2022-06-24_prometheus_sac22" / "raw" / "2022-06-24-serial-6583-flight-0003.csv"
# Columns a TeleMega log has and the 67-column Altus Metrum log does not.
IMU_COLUMNS = {
    "accel_x", "accel_y", "accel_z", "gyro_roll", "gyro_pitch", "gyro_yaw",
    "mag_x", "mag_y", "mag_z", "tilt", "pyro",
    "igniter_a", "igniter_b", "igniter_c", "igniter_d",
}  # fmt: skip

SUMMARY = """Rocket Name,TEST RKT
Firmware,abc1234 01/02/2024 03:04:05
Serial number,SN999 TEST RKT
Max Altitude,0.00 feet
Launch date,21-Aug-25
Pad Low-G Accel,-0.07,-1.00,-0.02"""


def _non_imu_altus_log(dst, serial: str) -> None:
    """Write a copy of the 0003 log without the IMU columns, under another serial."""
    lines = TM_0003.read_text().splitlines()
    header = [c.strip().lstrip("#") for c in lines[0].split(",")]
    keep = [i for i, c in enumerate(header) if c not in IMU_COLUMNS]
    out = []
    for n, line in enumerate(lines):
        cells = line.split(",")
        if n > 0:
            cells[header.index("serial")] = f" {serial}"
        out.append(",".join(cells[i] for i in keep))
    dst.write_text("\n".join(out) + "\n")


def test_sniff_splits_telemega_from_other_altus_metrum(tmp_path):
    other = tmp_path / "other.csv"
    _non_imu_altus_log(other, "5115")
    assert len(other.read_text().splitlines()[0].split(",")) == 67
    assert _sniff_kind(TM_0003) == "telemega"
    assert _sniff_kind(other) == "altusmetrum"


def test_two_altus_metrum_logs_both_survive(tmp_path):
    flight = copy_flight("2022-06-24_prometheus_sac22", tmp_path)
    _non_imu_altus_log(flight / "raw" / "2022-06-24-serial-5115-flight-0001.csv", "5115")

    result = runner.invoke(app, ["preprocess", str(flight)])
    assert result.exit_code == 0, result.output

    tm = pd.read_csv(flight / "interim" / "telemega_std.csv")
    am = pd.read_csv(flight / "interim" / "altusmetrum_5115_std.csv")
    assert set(tm["device_sn"].astype(str)) == {"6583"}
    assert set(am["device_sn"].astype(str)) == {"5115"}
    assert set(am["source"]) == {"altusmetrum"}

    meta = json.loads((flight / "interim" / "altusmetrum_5115_std.meta.json").read_text())
    assert meta["device"] == {"type": "altusmetrum", "serial": "5115", "firmware": "6"}
    assert [f["path"] for f in meta["input_files"]] == [
        "raw/2022-06-24-serial-5115-flight-0001.csv"
    ]

    result = runner.invoke(app, ["analyze", str(flight)])
    assert result.exit_code == 0, result.output


def test_same_serial_copy_is_not_duplicated(tmp_path):
    flight = copy_flight("2022-06-24_prometheus_sac22", tmp_path)
    shutil.copy(TM_0003, flight / "raw" / "copy.csv")
    result = runner.invoke(app, ["preprocess", str(flight)])
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (flight / "interim").glob("*_std.csv")) == ["telemega_std.csv"]


def test_blueraven_summary_identity(tmp_path):
    p = tmp_path / "TEST RKT_summary_x.csv"
    p.write_text(SUMMARY)
    assert _sniff_kind(p) == "blueraven_summary"
    assert blueraven_identity(p) == {"serial": "SN999", "firmware": "abc1234 01/02/2024 03:04:05"}


def test_blueraven_summary_fills_meta(tmp_path):
    flight = copy_flight("2025-08-21_hyperion2_lc25", tmp_path)
    (flight / "raw" / "src" / "TEST RKT_summary_x.csv").write_text(SUMMARY)

    result = runner.invoke(app, ["preprocess", str(flight)])
    assert result.exit_code == 0, result.output

    for name in ("blueraven_std", "blueraven_hr_std"):
        meta = json.loads((flight / "interim" / f"{name}.meta.json").read_text())
        assert meta["device"]["serial"] == "SN999"
        assert meta["device"]["firmware"] == "abc1234 01/02/2024 03:04:05"
        assert "raw/src/TEST RKT_summary_x.csv" in [f["path"] for f in meta["input_files"]]
    assert not (flight / "interim" / "blueraven_summary_std.csv").exists()


def test_plot_labels():
    from pfa.analyze import _plot_label

    assert _plot_label("telemega_std") == "TeleMega"
    assert _plot_label("blueraven_std") == "Blue Raven"
    assert _plot_label("altusmetrum_5115_std") == "Altus Metrum s/n 5115"
    assert _plot_label("telemega_7000_std") == "Altus Metrum s/n 7000"
    assert _plot_label("blueraven_hr_std") is None  # IMU only, not on the alt/vel panels

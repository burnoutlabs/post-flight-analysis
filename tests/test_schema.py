"""The interim column set is tied to SCHEMA_VERSION.

Changing STANDARD_COLUMNS fails test_columns_pinned_to_version until
SCHEMA_VERSION is bumped and the new version's column list is pinned here.
"""

from __future__ import annotations

import json
import re

from conftest import DATA, REPO

from pfa.schema import SCHEMA_VERSION, STANDARD_COLUMNS

# version -> exact column list, in order
PINNED = {
    "gfr-0.2": (
        "t_epoch_s,t_flight_s,source,state,event,alt_baro_m_msl,alt_gps_m_msl,alt_agl_m,"
        "alt_inertial_m,lat_deg,lon_deg,v_up_mps,v_dr_mps,v_cr_mps,pos_dr_m,pos_cr_m,"
        "speed_2d_mps,a_up_mps2,tilt_deg,future_angle_deg,roll_deg,sats,hdop,pressure_pa,"
        "temperature_c,v_batt_v,flag_liftoff,flag_apogee,flag_press_increasing,"
        "flag_burnout_coast,flag_apo_fired,flag_main_fired,flag_3rd_fired,flag_4th_fired,"
        "flag_normal_ascent,flag_accel_vel_le_0,flag_eci_vvel_le_0,flag_tilt_exceeded_90deg,"
        "device_sn,fw_version,schema_version,accel_x_g,accel_y_g,accel_z_g,gyro_x_degps,"
        "gyro_y_degps,gyro_z_degps,quat_1,quat_2,quat_3,quat_4"
    ).split(","),
}


def test_columns_pinned_to_version():
    assert SCHEMA_VERSION in PINNED, f"pin the column list for {SCHEMA_VERSION}"
    assert list(STANDARD_COLUMNS) == PINNED[SCHEMA_VERSION], (
        "STANDARD_COLUMNS changed: bump SCHEMA_VERSION and pin the new list"
    )


def test_schema_doc_matches_columns():
    text = (REPO / "docs" / "schema.md").read_text(encoding="utf-8")
    documented = re.findall(r"^\| `([a-z0-9_]+)` \|", text, flags=re.MULTILINE)
    # the first table rows that look like columns are the version table; skip them
    documented = [c for c in documented if not c.startswith("gfr-")]
    assert documented == list(STANDARD_COLUMNS)
    assert f"# Interim schema (`{SCHEMA_VERSION}`)" in text


def test_committed_interim_carries_current_version():
    for csv in sorted(DATA.glob("*/interim/*_std.csv")):
        header, first = csv.read_text(encoding="utf-8").splitlines()[:2]
        cols = header.split(",")
        assert cols == list(STANDARD_COLUMNS), csv
        assert first.split(",")[cols.index("schema_version")] == SCHEMA_VERSION, csv
        meta = json.loads(csv.with_name(csv.stem + ".meta.json").read_text(encoding="utf-8"))
        assert meta["schema_version"] == SCHEMA_VERSION, csv

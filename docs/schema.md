# Interim schema (`gfr-0.2`)

`pfa preprocess` writes one `interim/<name>_std.csv` per device log. Every
file has the same columns in the same order, listed below. The list is
`STANDARD_COLUMNS` in `src/pfa/schema.py`, and the version string is
`SCHEMA_VERSION` in the same file. It is written to every row's
`schema_version` column and to each `*.meta.json`.

## Versioning

Bump `SCHEMA_VERSION` whenever a column is added, removed, renamed, reordered
or changes unit or meaning, then regenerate every interim file (`just
preprocess`) and update this page. `tests/test_schema.py` pins the column list
to the version and fails if the columns change without a bump.

| Version | Columns | Change |
| --- | --- | --- |
| `gfr-0.1` | 41, later 51 | The tag covered two different column sets; the IMU columns were added without a bump |
| `gfr-0.2` | 51 | Same columns as the 51-column `gfr-0.1`; the bump makes the version identify them |

## Conventions

- Units are SI unless the column name says otherwise (`_g`, `_degps`, `_deg`).
  Imperial device values are converted on parse (feet to metres, ft/s to m/s,
  °F to °C, atm to Pa).
- A column a device does not provide is empty.
- Rows are sorted by `t_epoch_s`; rows with a duplicate `t_epoch_s` are dropped.
- Device names: **Altus Metrum** = TeleMega (`telemega`) and other Altus
  Metrum loggers (`altusmetrum`); **BR** = Blue Raven low-rate export
  (`blueraven`); **BR HR** = Blue Raven high-rate export (`blueraven_hr`);
  **FW** = Featherweight GPS tracker (`featherweight`).

## Columns

| Column | Unit | Devices | Meaning |
| --- | --- | --- | --- |
| `t_epoch_s` | s | all | Absolute time, Unix epoch. Altus Metrum: GPS date/time columns plus the log's `time` column, so it is not a clean UTC clock. BR, BR HR: local date/time converted to UTC with `--tz`. FW: device date/time, UTC only if the device clock was set to UTC |
| `t_flight_s` | s | all | Time since liftoff; negative before it. Altus Metrum: the log's `time` column. BR: from the first `Liftoff` row. BR HR: `Flight_Time_(s)`. FW: from the first row with vertical speed above 20 ft/s |
| `source` | — | all | Parser that produced the row: `telemega`, `altusmetrum`, `blueraven`, `blueraven_hr`, `featherweight` |
| `state` | — | Altus Metrum | Flight state name from the log (`boost`, `fast`, `coast`, `drogue`, `main`, `landed`, ...) |
| `event` | — | none | Reserved; no parser fills it |
| `alt_baro_m_msl` | m | Altus Metrum, BR | Barometric altitude above mean sea level |
| `alt_gps_m_msl` | m | Altus Metrum, FW | GPS altitude above mean sea level |
| `alt_agl_m` | m | Altus Metrum, BR, FW | Height above the pad. Altus Metrum: `height`. BR: `Baro_Altitude_AGL_(feet)`. FW: GPS altitude minus the median on-pad GPS altitude |
| `alt_inertial_m` | m | BR | Inertial altitude |
| `lat_deg` | deg | Altus Metrum, FW | GPS latitude |
| `lon_deg` | deg | Altus Metrum, FW | GPS longitude |
| `v_up_mps` | m/s | Altus Metrum, BR, FW | Vertical velocity, up positive. Altus Metrum: `speed`. BR: `Velocity_Up`. FW: `VERTV` |
| `v_dr_mps` | m/s | BR | Downrange velocity |
| `v_cr_mps` | m/s | BR | Crossrange velocity |
| `pos_dr_m` | m | BR | Inertial downrange position |
| `pos_cr_m` | m | BR | Inertial crossrange position |
| `speed_2d_mps` | m/s | BR, FW | Horizontal speed. BR: computed from `v_dr_mps` and `v_cr_mps`. FW: `HORZV` |
| `a_up_mps2` | m/s² | Altus Metrum, BR HR | Axial acceleration. Altus Metrum: `acceleration`. BR HR: `Accel_Y` × 9.80665 |
| `tilt_deg` | deg | BR | Tilt angle from vertical |
| `future_angle_deg` | deg | BR | Blue Raven predicted tilt angle |
| `roll_deg` | deg | BR | Roll angle |
| `sats` | count | Altus Metrum | GPS satellites in the solution |
| `hdop` | — | Altus Metrum | GPS horizontal dilution of precision |
| `pressure_pa` | Pa | Altus Metrum, BR | Barometric pressure |
| `temperature_c` | °C | Altus Metrum, BR | Board temperature |
| `v_batt_v` | V | Altus Metrum, BR, FW | Battery voltage |
| `flag_liftoff` | 0/1 | BR | Device reports liftoff detected |
| `flag_apogee` | 0/1 | BR | Device reports apogee detected |
| `flag_press_increasing` | 0/1 | BR | Device reports pressure increasing (descending) |
| `flag_burnout_coast` | 0/1 | BR | Device reports burnout, coasting |
| `flag_apo_fired` | 0/1 | BR | Apogee pyro channel has fired |
| `flag_main_fired` | 0/1 | BR | Main pyro channel has fired |
| `flag_3rd_fired` | 0/1 | BR | Third pyro channel has fired |
| `flag_4th_fired` | 0/1 | BR | Fourth pyro channel has fired |
| `flag_normal_ascent` | 0/1 | BR | Device reports a normal ascent |
| `flag_accel_vel_le_0` | 0/1 | BR | Accelerometer-integrated vertical velocity ≤ 0 |
| `flag_eci_vvel_le_0` | 0/1 | BR | Inertial-frame vertical velocity ≤ 0 |
| `flag_tilt_exceeded_90deg` | 0/1 | BR | Tilt has exceeded 90° |
| `device_sn` | — | Altus Metrum | Logger serial number |
| `fw_version` | — | Altus Metrum | The log's `version` column (AltOS log format version, not the firmware release) |
| `schema_version` | — | all | This schema's version, `gfr-0.2` |
| `accel_x_g` | g | BR HR | Accelerometer X |
| `accel_y_g` | g | BR HR | Accelerometer Y (axial, nose up; about −1 g at rest) |
| `accel_z_g` | g | BR HR | Accelerometer Z |
| `gyro_x_degps` | deg/s | BR HR | Gyro X rate |
| `gyro_y_degps` | deg/s | BR HR | Gyro Y rate |
| `gyro_z_degps` | deg/s | BR HR | Gyro Z rate |
| `quat_1` | — | BR HR | Orientation quaternion component 1 |
| `quat_2` | — | BR HR | Orientation quaternion component 2 |
| `quat_3` | — | BR HR | Orientation quaternion component 3 |
| `quat_4` | — | BR HR | Orientation quaternion component 4 |

`flag_*` columns are 1 where the device's flag column is non-zero and 0
otherwise, including where the device left it blank. Devices without these
flags leave them empty.

## Meta files

Each `<name>_std.csv` has a `<name>_std.meta.json` beside it: generation time,
`pfa_version`, `schema_version`, device type/serial/firmware, every input file
as a path relative to the flight directory with its sha256, the vendor-to-
standard column mapping, unit conversions, how liftoff was found
(`liftoff_method`) and row counts.

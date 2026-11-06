# Prioritization of Flight Data Categories by Importance

Goal: order all fields across Featherweight Blue Raven, Featherweight GPS Tracker, and Altus Metrum TeleMega from most safety-critical and analysis-enabling to least. Top categories are specific and prescriptive. Lower categories get broader and more optional.

---

## 1) Deployment & Safety-Critical Events ⟶ must-have for post-flight safety audit

**Why**: Confirms charges fired, main opened at target AGL, backups, and anomalies.

- Blue Raven (Low-Rate): `Apo_fired`,`Main_fired`,`3rd_fired`,`4th_fired`,`Rocket_FER_Hex`,`Apo_FER_Hex`,`Main_FER_Hex`,`3rd_FER_Hex`,`4th_FER_Hex`
- TeleMega: `drogue_voltage`,`main_voltage`,`pyro`,`igniter_a`,`igniter_b`,`igniter_c`,`igniter_d`
- GPS Tracker: N/A for pyros; use success/ack metrics in Cat 7

---

## 2) Flight State & Timing ⟶ aligns all streams and phases

**Why**: Defines liftoff→boost→coast→apogee→drogue→main→landed boundaries.

- Blue Raven (Low-Rate): `Liftoff`,`Apogee`,`Burnout_Coast`,`Press_Increasing`,`Normal_Ascent`,`Accel_Vel_LE_0`,`ECI_Vvel_le_0`,`Tilt_Exceeded_90deg`
- TeleMega: `time`,`state`,`state_name`
- All: `Year`,`Month`,`Day`,`Time`,`Flight_Time_(s)` (BR High/Low); `year..second` (TM)

---

## 3) Kinematics Core (Altitude / Velocity) ⟶ trajectory reconstruction

**Why**: Apogee, descent rates, drift, energy.

- Blue Raven (Low-Rate): `Baro_Altitude_ASL_(feet)`,`Baro_Altitude_AGL_(feet)`,`Velocity_Up`,`Velocity_DR`,`Velocity_CR`,`Inertial_Altitude`,`Inertial_DR_Position`,`Inertial_CR_Position`
- TeleMega: `altitude` (baro m), `height`, `speed`
- GPS Tracker: `TRACKER_Alt_ASL`,`Alt_AGL_(ft)`,`HORZV`,`VERTV`

---

## 4) Attitude & Stability ⟶ tilt limits, staging gates, dynamic issues

**Why**: Staging safety, off-vertical risk, coning, weathercocking.

- Blue Raven (Low-Rate): `Tilt_Angle_(deg)`,`Future_Angle_(deg)`,`Roll_Angle_(deg)`; event gates `LT_FANG1`,`GT_FANG2`,`GT_FUTANG`
- Blue Raven (High-Rate): `Quat_1..Quat_4`,`Gyro_X/Y/Z`,`Accel_X/Y/Z`
- TeleMega: `tilt`,`gyro_roll`,`gyro_pitch`,`gyro_yaw`,`accel_x/y/z`,`mag_x/y/z`
- Tracker: heading `HEAD` (coarse), phone pointing used at runtime

---

## 5) Environment & Baro Sensor Health ⟶ sensor trust and density effects

**Why**: Validate apogee detection and pressure-derived altitude quality.

- Blue Raven (Low-Rate): `Temperature_(F)`,`Baro_Press_(atm)`
- TeleMega: `pressure`,`temperature`
- Notes: cross-check with GPS altitude when available; watch for light/vent artifacts (BR guidance)

---

## 6) Power & Continuity ⟶ root cause for deployment failures

**Why**: Battery droop or open circuits are common failure modes.

- Blue Raven (Low-Rate): `Batt_Volts`,`Apo_Volts`,`Main_Volts`,`3rd_Volts`,`4th_Volts`
- TeleMega: `battery_voltage`,`drogue_voltage`,`main_voltage`,`igniter_a/b/c/d`
- Tracker: `BATT`,`GS_batt_v`

---

## 7) Link Health & Telemetry Reliability ⟶ situational awareness during/after flight

**Why**: Range prediction, lost-rocket diagnosis, packet integrity.

- Tracker: `RSSI_Down`,`RSSI_Up`,`LoRa_Max_Range_(kft)`,`LoRa_Success_Rate`,`Down_Sent`,`Down_Rcvd`,`Up_Sent`,`Up_Rcvd`
- Ground relays (Tracker): `Found_Sent`,`Found_rocket_ID`,`Found_RSSI`
- TeleMega/AltOS (operational): `connected`

---

## 8) GPS Core Position & Pad Geometry ⟶ recovery and drift analysis

**Why**: Where it went and how far.

- Tracker: `TRACKER_Lat`,`TRACKER_Lon`,`TRACKER_Alt_ASL`,`Horizontal_range_(ft)`,`Total_range_(ft)`
- TeleMega: `latitude`,`longitude`,`altitude` (GPS), `pad_dist`,`pad_range`,`pad_az`,`pad_el`
- Tracker: `GS_Lat`,`GS_Lon`,`GS_Alt_ASL`,`GS_ASL_offset`

---

## 9) GPS Fix Quality & Satellite Metrics ⟶ accuracy gating for analytics

**Why**: Decide when to trust GPS vs baro/inertial.

- TeleMega: `locked`,`nsat`,`pdop`,`hdop`,`vdop`,`sat01..sat32`
- Tracker: `FIX`,`#TOT`,`>24`,`>32`,`>40`
- Heuristics: prefer GPS when 3D fix + low DOP + ≥10 sats with ≥32 dB-Hz median

---

## 10) IMU Raw (High-Rate) ⟶ advanced dynamics, post-flight reconstruction

**Why**: Detailed motion study, flutter, shock loads, spin rates.

- Blue Raven (High-Rate): `Gyro_X/Y/Z` (deg/s×100), `Accel_X/Y/Z` (Gs×100), `Quat_1..4`, `Sync`
- TeleMega (100 Hz): `accel_x/y/z`,`gyro_roll/pitch/yaw`,`mag_x/y/z`
- Use with Cat 2 & 3 for precise phase and trajectory fits

---

## 11) Derived/Advanced Gates & Counters ⟶ optional decision logic inputs

**Why**: Custom deployment logic, transonic filters, burn counters.

- Blue Raven (Low-Rate): `LT_VEL1`,`GT_VEL2`,`LT_BVEL1`,`GT_BURN`,`LT_TVAL1`,`GT_TVAL2`,`LT_AGL1`,`GT_AGL2`
- TeleMega: covered via `pyro` and states; less granular bitfields than BR custom gates

---

## 12) Meta & Identifiers ⟶ bookkeeping

**Why**: Traceability and versioning.

- TeleMega: `version`,`serial`,`flight`,`call`
- Tracker: `TRACKER` (ID string)
- Blue Raven: rocket name in summary, firmware build in summary

---

## 13) Auxiliary & Reserveds ⟶ ignore unless populated

**Why**: Placeholders vary by firmware.

- Blue Raven (Low-Rate): `Reserved_1`,`Reserved_2`,`Reserved_3`,`Reserved` flags
- Blue Raven (High-Rate): `Aux_Volts`,`Current` (if wired)
- TeleMega: none standardized beyond listed

---

## Practical Use Order (TL;DR)

1. **Cat 1–2** to bracket phases and confirm deployments.
2. **Cat 3–4** to quantify trajectory and stability.
3. **Cat 5–6** to validate sensor health and power/continuity.
4. **Cat 7–9** to judge telemetry/GPS trust and aid recovery.
5. **Cat 10–11** for deep dive reconstruction or anomaly RCA.
6. **Cat 12–13** for provenance and filler.

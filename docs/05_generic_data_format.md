# Generic Flight-Computer Time-Series Format (GFC-TSF)

Purpose: a minimal, future-proof, columnar time series with categories ordered left→right by importance. Anything not available is empty. Additions use namespaced columns without breaking parsers.

## File Set

- `flight.csv` — time series, one row per sample.
- `metadata.json` — schema, units, frames, events, channels, and provenance.

## Column Ordering (left = strict/critical → right = broad/optional)

1. **Core Time & Phase**
2. **Deployment & Events**
3. **Flight State & Timing**
4. **Kinematics Core**
5. **Attitude & Stability**
6. **Environment**
7. **Power & Continuity**
8. **Link Health**
9. **GPS Position & Pad Geometry**
10. **GPS Quality**
11. **IMU Raw (Hi-Rate or Downsampled)**
12. **Advanced Gates / Derived**
13. **Aux / Vendor Extensions**

## `flight.csv` Columns (minimal baseline + extensible)

```csv
t,phase,evt_mask,deploy_main_fired,deploy_drogue_fired,deploy_aux1_fired,deploy_aux2_fired,liftoff_detect,apogee_detect,burnout_detect,alt_agl_m,alt_asl_m,vz_mps,vx_mps,vy_mps,tilt_deg,roll_deg,q0,q1,q2,q3,p_pa,temp_c,v_batt_v,v_main_v,v_drogue_v,v_aux1_v,v_aux2_v,rssi_down_dbm,rssi_up_dbm,link_success_rate,lat_deg,lon_deg,alt_gps_m,pad_dist_m,pad_range_m,pad_az_deg,pad_el_deg,gps_fix,nsat,pdop,hdop,vdop,gyro_x_dps,gyro_y_dps,gyro_z_dps,acc_x_mps2,acc_y_mps2,acc_z_mps2,mag_x_uT,mag_y_uT,mag_z_uT,drag_accel_mps2,ballistic_coef_est,wind_est_mps,staging_future_tilt_deg,x_vendor_example
```

### 1) Core Time & Phase

- `t` — seconds from liftoff or start (float, required)
- `phase` — enum string: `pad|boost|coast|apogee|drogue|main|landed|other`

### 2) Deployment & Events

- `evt_mask` — uint32 bitfield (event map in `metadata.json`)
- `deploy_main_fired` — bool
- `deploy_drogue_fired` — bool
- `deploy_aux1_fired` — bool
- `deploy_aux2_fired` — bool

### 3) Flight State & Timing

- `liftoff_detect` — bool
- `apogee_detect` — bool
- `burnout_detect` — bool

### 4) Kinematics Core

- `alt_agl_m` — meters
- `alt_asl_m` — meters
- `vz_mps` — vertical velocity
- `vx_mps` — downrange velocity
- `vy_mps` — crossrange velocity

### 5) Attitude & Stability

- `tilt_deg` — 0=vertical
- `roll_deg` — integrated roll
- `q0,q1,q2,q3` — unit quaternion (w,x,y,z) or leave empty if unknown

### 6) Environment

- `p_pa` — static pressure
- `temp_c` — internal temperature

### 7) Power & Continuity

- `v_batt_v` — system battery
- `v_main_v` — main continuity
- `v_drogue_v` — drogue continuity
- `v_aux1_v` — aux continuity
- `v_aux2_v` — aux continuity

### 8) Link Health

- `rssi_down_dbm` — GS receive
- `rssi_up_dbm` — tracker receive
- `link_success_rate` — 0..1 over sliding window

### 9) GPS Position & Pad Geometry

- `lat_deg` — WGS84
- `lon_deg`
- `alt_gps_m`
- `pad_dist_m` — horizontal from pad
- `pad_range_m` — slant range
- `pad_az_deg`
- `pad_el_deg`

### 10) GPS Quality

- `gps_fix` — 0/2/3
- `nsat` — total satellites
- `pdop`
- `hdop`
- `vdop`

### 11) IMU Raw (optional)

- `gyro_x_dps`,`gyro_y_dps`,`gyro_z_dps`
- `acc_x_mps2`,`acc_y_mps2`,`acc_z_mps2`
- `mag_x_uT`,`mag_y_uT`,`mag_z_uT`

### 12) Advanced / Derived (optional)

- `drag_accel_mps2`
- `ballistic_coef_est`
- `wind_est_mps`
- `staging_future_tilt_deg`

### 13) Aux / Vendor Extensions

- `x_<vendor>_<name>` — reserved namespace for future devices

---

## `metadata.json` (concise schema + provenance)

```json
{
  "version": "gfc-tsf-1.0",
  "provenance": {
    "generator": "gfc-normalizer",
    "source_files": ["raw_log_01.csv"],
    "created_utc": "2025-09-01T00:00:00Z",
    "device_family": "generic",
    "notes": "Normalized to SI; empty = unknown."
  },
  "frames": {
    "navigation_frame": "NED",
    "body_axes": "x=fwd,y=right,z=down",
    "quaternion_convention": "wxyz",
    "tilt_reference": "angle from local vertical"
  },
  "units": {
    "t": "s",
    "alt_agl_m": "m",
    "alt_asl_m": "m",
    "vz_mps": "m/s",
    "v_batt_v": "V",
    "p_pa": "Pa",
    "temp_c": "C",
    "pad_az_deg": "deg"
  },
  "columns": [
    { "name": "t", "type": "float", "category": 1, "required": true },
    {
      "name": "phase",
      "type": "string",
      "category": 1,
      "enum": [
        "pad",
        "boost",
        "coast",
        "apogee",
        "drogue",
        "main",
        "landed",
        "other"
      ]
    },
    { "name": "evt_mask", "type": "uint32", "category": 2 },
    { "name": "deploy_main_fired", "type": "bool", "category": 2 },
    { "name": "deploy_drogue_fired", "type": "bool", "category": 2 },
    { "name": "deploy_aux1_fired", "type": "bool", "category": 2 },
    { "name": "deploy_aux2_fired", "type": "bool", "category": 2 },
    { "name": "liftoff_detect", "type": "bool", "category": 3 },
    { "name": "apogee_detect", "type": "bool", "category": 3 },
    { "name": "burnout_detect", "type": "bool", "category": 3 },
    { "name": "alt_agl_m", "type": "float", "category": 4 },
    { "name": "alt_asl_m", "type": "float", "category": 4 },
    { "name": "vz_mps", "type": "float", "category": 4 },
    { "name": "vx_mps", "type": "float", "category": 4 },
    { "name": "vy_mps", "type": "float", "category": 4 },
    { "name": "tilt_deg", "type": "float", "category": 5 },
    { "name": "roll_deg", "type": "float", "category": 5 },
    { "name": "q0", "type": "float", "category": 5 },
    { "name": "q1", "type": "float", "category": 5 },
    { "name": "q2", "type": "float", "category": 5 },
    { "name": "q3", "type": "float", "category": 5 },
    { "name": "p_pa", "type": "float", "category": 6 },
    { "name": "temp_c", "type": "float", "category": 6 },
    { "name": "v_batt_v", "type": "float", "category": 7 },
    { "name": "v_main_v", "type": "float", "category": 7 },
    { "name": "v_drogue_v", "type": "float", "category": 7 },
    { "name": "v_aux1_v", "type": "float", "category": 7 },
    { "name": "v_aux2_v", "type": "float", "category": 7 },
    { "name": "rssi_down_dbm", "type": "float", "category": 8 },
    { "name": "rssi_up_dbm", "type": "float", "category": 8 },
    { "name": "link_success_rate", "type": "float", "category": 8 },
    { "name": "lat_deg", "type": "float", "category": 9 },
    { "name": "lon_deg", "type": "float", "category": 9 },
    { "name": "alt_gps_m", "type": "float", "category": 9 },
    { "name": "pad_dist_m", "type": "float", "category": 9 },
    { "name": "pad_range_m", "type": "float", "category": 9 },
    { "name": "pad_az_deg", "type": "float", "category": 9 },
    { "name": "pad_el_deg", "type": "float", "category": 9 },
    { "name": "gps_fix", "type": "int", "category": 10, "enum": [0, 2, 3] },
    { "name": "nsat", "type": "int", "category": 10 },
    { "name": "pdop", "type": "float", "category": 10 },
    { "name": "hdop", "type": "float", "category": 10 },
    { "name": "vdop", "type": "float", "category": 10 },
    { "name": "gyro_x_dps", "type": "float", "category": 11 },
    { "name": "gyro_y_dps", "type": "float", "category": 11 },
    { "name": "gyro_z_dps", "type": "float", "category": 11 },
    { "name": "acc_x_mps2", "type": "float", "category": 11 },
    { "name": "acc_y_mps2", "type": "float", "category": 11 },
    { "name": "acc_z_mps2", "type": "float", "category": 11 },
    { "name": "mag_x_uT", "type": "float", "category": 11 },
    { "name": "mag_y_uT", "type": "float", "category": 11 },
    { "name": "mag_z_uT", "type": "float", "category": 11 },
    { "name": "drag_accel_mps2", "type": "float", "category": 12 },
    { "name": "ballistic_coef_est", "type": "float", "category": 12 },
    { "name": "wind_est_mps", "type": "float", "category": 12 },
    { "name": "staging_future_tilt_deg", "type": "float", "category": 12 },
    { "name": "x_vendor_example", "type": "string", "category": 13 }
  ],
  "events": {
    "bit0": "liftoff_detect",
    "bit1": "apogee_detect",
    "bit2": "burnout_detect",
    "bit3": "deploy_main_fired",
    "bit4": "deploy_drogue_fired",
    "bit5": "geofence_exceeded",
    "bit6": "tilt_limit_exceeded",
    "bit7": "high_descent_rate",
    "reserved_from_bit8_to_bit31": "vendor_defined"
  },
  "channels": [
    {
      "name": "main",
      "type": "deployment",
      "priority": 1,
      "fire_column": "deploy_main_fired",
      "continuity_column": "v_main_v"
    },
    {
      "name": "drogue",
      "type": "deployment",
      "priority": 1,
      "fire_column": "deploy_drogue_fired",
      "continuity_column": "v_drogue_v"
    },
    {
      "name": "aux1",
      "type": "aux",
      "priority": 2,
      "fire_column": "deploy_aux1_fired",
      "continuity_column": "v_aux1_v"
    },
    {
      "name": "aux2",
      "type": "aux",
      "priority": 2,
      "fire_column": "deploy_aux2_fired",
      "continuity_column": "v_aux2_v"
    }
  ],
  "sampling": {
    "primary_rate_hz": 50,
    "imu_rate_hz": 100,
    "gps_rate_hz": 1,
    "link_agg_window_s": 5
  },
  "pad": {
    "lat_deg": null,
    "lon_deg": null,
    "alt_asl_m": null,
    "agl_reference": "first_valid_sample",
    "notes": "Provide pad if known to improve geometry."
  },
  "quality": {
    "gps_trust_rules": {
      "require_fix": 3,
      "min_nsat": 8,
      "max_pdop": 3.0
    },
    "limits": {
      "tilt_deg_warn": 20,
      "tilt_deg_abort": 90,
      "v_batt_v_min": 3.6
    }
  },
  "extensions": {
    "vendor_namespaces": ["x_fw", "x_am", "x_custom"]
  }
}
```

### Required Sections

- `version` — GFC-TSF spec version
- `provenance` — who/when/how
- `frames` — definitions for axes and pad reference
- `units` — column→unit mapping
- `columns` — ordered list with type and category
- `events` — `evt_mask` bit index map
- `channels` — deployment channel semantics
- `sampling` — per-signal nominal rates and decimation
- `pad` — reference lat/lon/alt and derivation method
- `quality` — validity flags and thresholds
- `extensions` — vendor-specific notes

### Design Rules

- All columns optional except `t`.
- Units are SI; convert at ingestion.
- Unknowns empty, not zero.
- Add new fields only at the right or under `x_*`.
- Event semantics live in `metadata.json`, not hard-coded.
- Per-file pad reference is required if `alt_agl_m` present.

---

## Minimal Workflow

1. **Ingest**: parse vendor CSV → normalize to SI → compute `t` and `phase`.
2. **Calibrate**: apply biases from metadata if provided.
3. **Derive**: compute AGL, pad geometry, link rates, event masks.
4. **Validate**: mark quality flags; keep unknowns empty.
5. **Export**: write `flight.csv` and `metadata.json`.

# Datasources Understanding

We will review the initial datasources targeted for processing. Focus is on structure, content, and role in flight data analysis.

## Featherweight

### Blue Raven Altimeter

#### Low-Rate Flight Data

- Lower-frequency logging.
- Fields include:
  - Timebase: timestamps, flight time, sync.
  - Environment: temperature, pressure, altitude (ASL/AGL).
  - Power: battery and pyro channel voltages.
  - Dynamics: derived velocities, inertial estimates.
  - Orientation: tilt, roll, future angle.
  - Events: liftoff, apogee, burnout, pyro firings.
  - Numerous boolean flags and reserved diagnostics.
- Purpose: flight overview, key events, system health.

#### High-Rate Flight Data

- Higher-frequency logging.
- Fields include:
  - IMU: gyroscope (X/Y/Z), accelerometer (X/Y/Z).
  - Orientation: quaternions.
  - Power: auxiliary voltage, current.
- Purpose: detailed dynamics, orientation, and trajectory analysis.

#### Relationship

- Low-rate: event summary, system state.
- High-rate: high-resolution motion data.
- Together: enable both coarse reconstruction and fine-grained dynamics.

### GPS Tracker

- Provides position and telemetry via LoRa link to ground station, with Bluetooth forwarding to app.
- Data fields:
  - Identifiers: tracker ID, date, time.
  - Positions: GS lat/lon/ASL, tracker lat/lon/ASL.
  - GPS fix and satellites: fix type, count, signal bins (>24, >32, >40).
  - Motion: horizontal/vertical velocity, heading.
  - Link: RSSI up/down, LoRa success rate, max range, packet counts.
  - Derived: horizontal range, AGL altitude, total range.
  - Power: tracker and GS battery voltages.
  - Recovery: “found rocket” relay fields.
- Purpose: real-time tracking, post-flight trajectory and link quality, lost-rocket recovery.
- Relation to altimeter logs: complements high-resolution onboard data with geospatial trajectory and communications.

## TeleMega

### Single-Rate Full-Flight Data

- Continuous logging and telemetry through flight.
- Captures barometric, inertial, GPS, pyro, and system state.
- Data Fields:
  - Metadata: version, serial, flight ID, call sign, timestamp, state (numeric + text).
  - Environment & motion: acceleration, pressure, altitude, height above pad, speed, temperature.
  - Voltages: drogue, main, battery.
  - IMU: accel_x/y/z, gyro_roll/pitch/yaw, mag_x/y/z.
  - Orientation: tilt.
  - Pyro: pyro channel status, igniter A–D, continuity.
  - Connectivity: connected, GPS locked.
  - GPS: nsat, lat/lon, GPS altitude, full timestamp, pad distance/range/az/el, PDOP/HDOP/VDOP.
  - Satellites: IDs and signal values up to 32 sats.
- Purpose:
  - Provides integrated full-flight dataset with sensor fusion, deployment events, GPS trajectory, and system monitoring.
  - Enables detailed post-flight analysis in one continuous log.

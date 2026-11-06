# Altus Metrum TeleMega Flight Data Insights

This guide documents the structure and interpretation of TeleMega flight log data.  
It is based on official Altus Metrum documentation, community resources, and the provided header.

---

## 1. General Information

- **Logging System**: TeleMega records flight data at 100 Hz for sensors, with downsampled telemetry packets sent to ground stations.
- **File Format**: CSV logs with a fixed header defining all columns.
- **Units**: SI unless otherwise noted.
- **Timebase**: Derived from internal clock, synchronized with GPS when available.

---

## 2. Data Fields

### Metadata

- **version** – Log file format version.
- **serial** – TeleMega hardware serial number.
- **flight** – Flight number stored in EEPROM.
- **call** – Callsign (user configured).

### Time and State

- **time** – Seconds since boot or flight start.
- **state** – Numeric flight state ID.
- **state_name** – Textual state (prelaunch, boost, coast, apogee, drogue, main, landed).

### Core Sensors

- **acceleration** – Derived acceleration magnitude (m/s²).
- **pressure** – Barometric pressure (Pa).
- **altitude** – Barometric altitude (m).
- **height** – Height above pad (m).
- **speed** – Vertical speed estimate (m/s).
- **temperature** – Internal sensor temperature (°C).

### Power and Pyro Circuits

- **drogue_voltage** – Voltage on drogue deployment channel (V).
- **main_voltage** – Voltage on main deployment channel (V).
- **battery_voltage** – System battery voltage (V).
- **pyro** – Pyro channel continuity and status flags.
- **igniter_a/b/c/d** – Voltage continuity per igniter channel (V).

### IMU Data

- **accel_x, accel_y, accel_z** – Raw accelerometer axes (m/s²).
- **gyro_roll, gyro_pitch, gyro_yaw** – Gyroscope axes (deg/s).
- **mag_x, mag_y, mag_z** – Magnetometer axes (µT).
- **tilt** – Computed tilt angle relative to vertical (degrees).

### Connectivity and Status

- **connected** – Ground station connectivity flag (0/1).
- **locked** – GPS lock flag (0/1).
- **nsat** – Number of satellites in solution.

### GPS Data

- **latitude, longitude** – Position (decimal degrees).
- **altitude** – GPS-derived altitude (m).
- **year, month, day, hour, minute, second** – UTC timestamp.
- **pad_dist** – Horizontal distance from pad (m).
- **pad_range** – Slant range from pad (m).
- **pad_az** – Azimuth from pad (deg).
- **pad_el** – Elevation angle from pad (deg).
- **pdop, hdop, vdop** – GPS dilution of precision metrics:
  - **PDOP**: Position accuracy.
  - **HDOP**: Horizontal accuracy.
  - **VDOP**: Vertical accuracy.

### GPS Satellite Info

- **sat01 … sat32** – Signal-to-noise ratio (SNR, dB-Hz) per satellite in view.
  - 0 = not tracked.
  - 30–40 dB-Hz = good.
  - > 40 dB-Hz = excellent.

---

## 3. Flight State Logic

| State ID | Name   | Description                      |
| -------- | ------ | -------------------------------- |
| 0        | Idle   | Pre-powerup / waiting            |
| 1        | Pad    | Armed, waiting for liftoff       |
| 2        | Boost  | Motor burning, high acceleration |
| 3        | Coast  | Post-burnout, ascending          |
| 4        | Apogee | Detected peak altitude           |
| 5        | Drogue | Drogue deployment phase          |
| 6        | Main   | Main chute deployment phase      |
| 7        | Landed | On ground, low motion            |

Deployment logic is configured via **AltOS**. Drogue and main fire conditions depend on detected apogee and configured main deployment altitude.

---

## 4. Sensor Interpretation

- **Accelerometers** – ±16 g range. Used for boost detection, tilt, and velocity estimates.
- **Gyroscopes** – ±2000 °/s. Used for tilt propagation and flight dynamics.
- **Magnetometer** – Provides compass heading for redundancy.
- **Pressure Sensor** – Used for altitude and apogee detection.

---

## 5. GPS and Radio

- **Fix Flags**: Locked = 1 when valid 3D GPS solution.
- **nsat**: Typically ≥ 6 for reliable fix.
- **DOP Metrics**: Lower values = higher accuracy.
- **satXX Fields**: SNR values help evaluate GPS reception quality.
- **Telemetry**: TeleMega streams packets via APRS/AltOS to ground station.

---

## 6. Deployment and Pyros

- **Continuity Voltages**: Channels report continuity before flight.
- **During Firing**: Voltage drops as igniter fires.
- **Post-Flight**: Logged voltages can confirm pyro channel performance.

---

## 7. Logging and Analysis

- **Sample Rates**:
  - IMU sensors: 100 Hz.
  - GPS: 1 Hz (standard).
  - Telemetry: Downsampled ~10 Hz.
- **Data Uses**:
  - Reconstruct trajectory.
  - Verify deployment timing.
  - Cross-check baro vs GPS altitudes.

---

## References

[1] Altus Metrum TeleMega Product Page – <http://altusmetrum.org/TeleMega/>  
[2] Altus Metrum AltOS Software and Manuals – <http://altusmetrum.org/AltOS/>
[3] Altus Metrum AltOS UI Manual – <http://altusmetrum.org/AltosUI/>
[4] TeleMega Hardware and Specs (PDF) – <http://altusmetrum.org/TeleMega/v3.0/telemega-v3.0.pdf>  
[5] TeleMetrum/TeleMega Telemetry Fields – <http://altusmetrum.org/AltOS/telemetry.html>  
[6] GPS Dilution of Precision (PDOP/HDOP/VDOP) – <https://en.wikipedia.org/wiki/Dilution_of_precision_(navigation)>

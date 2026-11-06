# Blue Raven Flight Data Logs – Output Columns

The Blue Raven records three tiers of data after each flight:

1. **Summary Data** – key metrics (apogee, max velocity, deployment stats).
2. **Low-Rate Data** – full state data at 50 Hz.
3. **High-Rate Data** – core inertial and orientation data at 500 Hz.

This document lists all fields available in **low-rate** and **high-rate** logs with units and descriptions.

---

## 1. Summary Data

Via USB `<summary>` or phone auto-download after flight.

- **Rocket**: User-defined rocket name.
- **Build Date/Time**: Firmware build timestamp.
- **Launch / Landing Time**: Start and end of flight.
- **Pad Accel (X,Y,Z)**: Raw accelerometer readings at rest (Gs ×10,000).
- **Rail Direction (X,Y,Z)**: Normalized first-motion vector, defines rocket axis.
- **Accel Pad Offsets (X,Y,Z)**: Bias corrections applied to low-range accelerometers (Gs ×10,000).
- **Hi-G Pad Offsets (X,Y,Z)**: Bias corrections applied to high-range accelerometers (Gs ×10,000).
- **Flash Status**: Active bank, completion state, last address written.
- **Apogee Horizontal Velocity**: Estimated horizontal velocity at apogee (ft/s).
- **Max Motor Accel**: Maximum acceleration during boost (Gs ×10).
- **Max Drag Accel**: Maximum acceleration after burnout before apogee (Gs ×10).
- **Drogue Vel @ Main**: Descent velocity just before main deployment (ft/s ×10).
- **Main Avg Velocity**: Average descent velocity 6 seconds after main deployment (ft/s ×10).
- **Burnout Tilt**: Tilt angle at burnout (deg ×10).
- **Tilt Efficiency**: Ratio of vertical to expected vertical velocity at burnout (% ×10).
- **Ascent Roll Angle**: Integrated roll angle prior to apogee (deg).
- **Pad ASL**: Launch site altitude above sea level from barometric sensor (ft).
- **Max Deploy Accel (per channel)**: Max acceleration in 1 s window after each deployment (Gs ×10).
- **Max Landing Accel**: Highest acceleration before landing (Gs ×10).
- **Max Altitude**: Apogee (ft).
- **Max Velocity**: Peak velocity (ft/s).
- **CRC**: 16-bit checksum.

---

## 2. Low-Rate Log (50 Hz)

Via USB `<download l>` or phone auto-download after upon approaching rocket on recovery.

Each row contains:

- **Sync**: Millisecond counter, aligns with high-rate log. Rolls every 250 ms.
- **Bo**:
  - Temperature (°F)
  - Barometric pressure (atm × 50,000)
- **V**: Voltages (mV)
  - Battery
  - Apo channel
  - Main channel
  - 3rd channel
  - 4th channel
  - Output current (mA)
- **Vel** (ft/s, inertial frame):
  - Upward velocity
  - Downrange velocity
  - Crossrange velocity
- **Pos** (ft, inertial frame):
  - Inertial altitude
  - Downrange position
  - Crossrange position
- **ang**:
  - Tilt angle (deg ×10)
  - Roll angle (deg)
  - Future tilt (deg ×10, projected +3 s)
- **FER**: Flight Event Registers
  - Rocket-level FER (liftoff, apogee, burnout, etc.)
  - Apo FER
  - Main FER
  - 3rd FER
  - 4th FER
- **CRC**: 16-bit checksum.

**Notes:**

- Inertial data derived by gyro-driven attitude propagation. Large rotation rates (>±2000 °/s) cause drift.
- Future tilt angle useful for staging logic.
- FER values are hex bitfields with one bit per event (e.g. liftoff, apogee, channel-fired).

---

## 3. High-Rate Log (500 Hz)

Via USB `<download h>` or phone auto-download after upon approaching rocket on recovery.

Each row contains:

- **Sync**: Millisecond counter (same as low-rate).
- **Gyro** (deg/s ×100):
  - X-axis
  - Y-axis
  - Z-axis
- **Accel** (Gs ×100):
  - X-axis
  - Y-axis
  - Z-axis
  - Uses ±32 G accelerometers unless exceeded → high-range used.
- **Quaternion** (scaled ×30,000):
  - X component (rotation axis)
  - Y component
  - Z component
  - Magnitude term (w)

**Notes:**

- Quaternions encode rocket orientation without gimbal lock.
- Data allows reconstruction of 3D orientation and angular rates at sub-millisecond resolution.

---

## 4. Key Integration Notes

- **Alignment**: Use `sync` field to merge low-rate and high-rate datasets.
- **FER**: Provides a record of onboard event detections (liftoff, apogee, channel fires).
- **Units**: Pay close attention to scaling factors (e.g. Gs ×100 vs Gs ×10,000).
- **Accuracy Limits**: Inertial navigation degrades with gyro saturation or sensor noise after deployment.

---

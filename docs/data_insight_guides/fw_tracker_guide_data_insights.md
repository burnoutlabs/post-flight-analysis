# Featherweight GPS Tracker – Data Output Reference

The Featherweight GPS Tracker provides **real-time telemetry** and **onboard logged data**.  
This document consolidates available fields from the **tracker**, **ground station**, and **serial telemetry** output.

---

## 1. Logged Flight Data (Onboard Tracker)

Logged internally at **10 Hz during ascent**, **1 Hz during descent**, up to 6144 samples.  
Download required before firmware updates or power cycle.

### Fields

- **UTC Time** – GPS-derived timestamp.
- **UNIX Time** – Seconds since epoch.
- **Altitude (ASL)** – Feet above sea level.
- **Latitude** – Decimal degrees.
- **Longitude** – Decimal degrees.
- **Total Satellites** – Count of satellites tracked.
- **Fix Flag** – GPS fix type (0 = no fix, 2 = 2D fix, 3 = 3D fix).
- **Horizontal Velocity** – Feet/second.
- **Vertical Velocity** – Feet/second.
- **Heading** – Degrees from North.
- **GPS Quality Flags** – Internal flags for solution reliability.
- **Satellite Strength Counts**:
  - Satellites > 40 dB-Hz
  - Satellites > 32 dB-Hz
  - Satellites > 24 dB-Hz
- **LoRa Signal Strength (Ack Packets)** – dBm from ground station acks.
- **Tracker Battery Voltage** – Volts.

---

## 2. Real-Time App Telemetry

### **GPS Page**

- **Satellite Bars** – Signal strength per satellite:
  - Orange (<24 dB-Hz) = weak, poor accuracy.
  - Yellow (24–32) = fair.
  - Green (32–40) = good.
  - Blue (>40) = very good.
- **GS Altitude (ASL)** – Feet.
- **Phone GPS** – Position of user device.
- **Tracker Satellites** – Count and signal quality.
- **Comm Status** – Time since last contact with GS and Tracker.

### **Track Page**

- **Azimuth** – Tracker vs phone orientation.
- **Elevation** – Tracker vs phone orientation.
- **Altitude** – Feet ASL.
- **Vertical Velocity** – Ft/s.
- **Horizontal Velocity** – Ft/s.
- **Range/Distance** – Feet line-of-sight.
- **Tracker Battery Voltage** – Volts.
- **Ground Station Voltage** – Volts.
- **Tracker ID** – User-defined identifier.

### **Comm Page**

- **Packet Counters** (increment once/sec if link healthy):
  - Tracker telemetry packets sent
  - GS packets received
  - GS acknowledgements sent
  - Tracker acknowledgements received
- **Signal Strength (RSSI)** – dBm of LoRa packets.
- **Signal-to-Noise Ratio (SNR)** – dB.
- **Ack RSSI / Ack SNR** – Quality of return path.

---

## 3. Serial Telemetry Packets (Ground Station V2, USB @115200 bps)

Each line begins with `@` and ends with `CRC`.

### **GPS_STAT**

- **Time (Y/M/D hh:mm:ss.ms)**
- **Unit Type** (`TRK`, `GS`, `FND`)
- **Altitude ASL** – Feet.
- **Latitude, Longitude** – Decimal degrees.
- **Horizontal Velocity** – Ft/s.
- **Heading** – Degrees from North.
- **Vertical Velocity** – Ft/s.
- **Fix Type** – 0 (no fix), 2 (2D), 3 (3D).
- **Total Satellites** – Count.
- **Sats >24, >32, >40 dB-Hz** – Counts.
- **Per-Satellite Triplets** – Azimuth, Elevation, Strength.

### **TX_STAT**

- Transmission event log.
- Fields: Time, Tracker ID, Tx duration (ms), Spreading factor, Frequency (Hz).

### **FRST_FIX**

- Time to first fix after reset/wakeup (ms).

### **RX_TMOUT**

- LoRa receive timeout, includes spreading factor.

### **RLY_DIST**

- Relay packet for lost rockets:
  - Relay ID
  - RSSI (dBm)
  - Δ Altitude (ft)
  - Horizontal Distance (ft)
  - Tracker battery voltage (mV)
  - Relay battery voltage (mV)
  - Relay temperature (°C)

### **RX_FOUND**

- Found rocket relays:
  - Tracker LoRa ID
  - Packet counters (sent/received)
  - RSSI/SNR of relayed packets
  - Relay info and signal strength.

### **RX_NOMTK**

- Normal tracker telemetry reception:
  - Packets received/sent
  - RSSI and SNR
  - Tracker battery voltage
  - Relay temperature.

### **RX_COORD / RX_CRDFD**

- Channel coordination / found data exchange between GS units.

### **GS_COORD / COORDFND**

- Ground station channel coordination.
- Found rocket summary packets (ID, battery voltage, etc.).

### **FS_CHNGE**

- Flight state changes (manual or automatic).

### **BATT_BLE**

- Ground station battery, BLE status, and temperature.

---

## 4. Insights

- **GPS Robustness**: Full accuracy requires ≥10 satellites with at least half green/blue (>32 dB-Hz). Carbon fiber or metallic airframes degrade signal.
- **LoRa Link Budget**:
  - Minimum RX sensitivity ~ -133 dBm.
  - Range estimation: each 20 dB ≈ ×10 in range.
  - Stub antennas sufficient for 100+ km line-of-sight flights.
- **Lost Rocket Mode**:
  - Activates 5 minutes after landing without comms.
  - Transmits intermittently on “lost and found” channels.
  - Other flyers’ trackers relay lost rocket location back to all GS units.
- **Logging vs Real-time**:
  - Logged data is authoritative for Tripoli records.
  - Real-time telemetry may drop during launch but logging continues with valid GPS fixes.
- **Spoken Telemetry**: Provides ascent, apogee, descent altitudes and velocities via phone app.

---

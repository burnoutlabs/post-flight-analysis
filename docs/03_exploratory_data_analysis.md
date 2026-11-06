# Exploratory Data Analysis (EDA)

Now that we have our [datasource understanding](02_datasources_understanding.md) we can begin to explore our data!

The purpose of EDA to analyze and summarize the main characteristics of a dataset using visual or summative methods in order to identify patterns, spot anomalies, and understand relationships between variables before formal modeling or hypothesis testing.

## Featherweight

### High-Rate Data (500 Hz)

`Year,Month,Day,Time,Flight_Time_(s),Sync,Gyro_X,Gyro_Y,Gyro_Z,Accel_X,Accel_Y,Accel_Z,Quat_1,Quat_2,Quat_3,Quat_4,Aux_Volts,Current`

- **Year** – UTC year.
- **Month** – UTC month.
- **Day** – UTC day.
- **Time** – UTC time (hh:mm:ss).
- **Flight*Time*(s)** – Seconds since launch detection.
- **Sync** – Millisecond counter (rolls every 250 ms, aligns low/high logs).
- **Gyro_X** – Angular velocity about X-axis (deg/s ×100).
- **Gyro_Y** – Angular velocity about Y-axis (deg/s ×100).
- **Gyro_Z** – Angular velocity about Z-axis (deg/s ×100).
- **Accel_X** – Acceleration along X-axis (Gs ×100, ±32 G range).
- **Accel_Y** – Acceleration along Y-axis (Gs ×100).
- **Accel_Z** – Acceleration along Z-axis (Gs ×100).
- **Quat_1** – Quaternion X component (×30,000).
- **Quat_2** – Quaternion Y component (×30,000).
- **Quat_3** – Quaternion Z component (×30,000).
- **Quat_4** – Quaternion magnitude/rotation term (×30,000).
- **Aux_Volts** – Auxiliary channel voltage (V).
- **Current** – Auxiliary channel current (mA).

---

### Low-Rate Data (50 Hz)

`Year,Month,Day,Time,Flight_Time_(s),Sync,Temperature_(F),Baro_Press_(atm),Baro_Altitude_ASL_(feet),Baro_Altitude_AGL_(feet),Batt_Volts,Apo_Volts,Main_Volts,3rd_Volts,4th_Volts,Velocity_Up,Velocity_DR,Velocity_CR,Inertial_Altitude,Inertial_DR_Position,Inertial_CR_position,Tilt_Angle_(deg),Future_Angle_(deg),Roll_Angle_(deg),Reserved_1,Reserved_2,Reserved_3,Rocket_FER_Hex,Apo_FER_H  ex,Main_FER_Hex,3rd_FER_Hex,4th_FER_Hex,Liftoff,Apogee,Press_Increasing,Burnout_Coast,Apo_fired,Main_fired,3rd_fired,4th_fired,Normal_Ascent,Accel_Vel_LE_0,ECI_Vvel_le_0,Tilt Exceeded 90deg,Reserved,LT_AGL1,GT_AGL2,LT_FANG1,GT_FANG2,GT_FUTANG,LT_TVAL1,GT_TVAL2,LT_VEL1,GT_VEL2,LT_BVEL1,GT_BURN,Armed,Reserved,Reserved,LT_AGL1,GT_AGL2,LT_FANG1,GT_FANG2,GT_FUTANG,LT_TVAL1,GT_TVAL2,LT_VEL1,GT_VEL2,LT_BVEL1,GT_BURN,Armed,Reserved,Reserved,LT_AGL1,GT_AGL2,LT_FANG1,GT_FANG2,GT_FUTANG,LT_TVAL1,GT_TVAL2,LT_VEL1,GT_VEL2,LT_BVEL1,GT_BURN,Armed,Reserved,Reserved,LT_AGL1,GT_AGL2,LT_FANG1,GT_FANG2,GT_FUTANG,LT_TVAL1,GT_TVAL2,LT_VEL1,GT_VEL2,LT_BVEL1,GT_BURN,Armed,Reserved,Reserved`

- **Year** – UTC year.
- **Month** – UTC month.
- **Day** – UTC day.
- **Time** – UTC time (hh:mm:ss).
- **Flight*Time*(s)** – Seconds since launch detection.
- **Sync** – Millisecond counter (same as high-rate).
- **Temperature\_(F)** – Barometric sensor temperature (°F).
- **Baro*Press*(atm)** – Barometric pressure (atm).
- **Baro*Altitude_ASL*(feet)** – Altitude above sea level from baro (ft).
- **Baro*Altitude_AGL*(feet)** – Altitude above pad from baro (ft).
- **Batt_Volts** – Battery voltage (V).
- **Apo_Volts** – Apo channel continuity voltage (V).
- **Main_Volts** – Main channel continuity voltage (V).
- **3rd_Volts** – 3rd channel continuity voltage (V).
- **4th_Volts** – 4th channel continuity voltage (V).
- **Velocity_Up** – Upward velocity, inertial frame (ft/s).
- **Velocity_DR** – Downrange velocity (ft/s).
- **Velocity_CR** – Crossrange velocity (ft/s).
- **Inertial_Altitude** – Inertial altitude estimate (ft).
- **Inertial_DR_Position** – Inertial downrange position (ft).
- **Inertial_CR_Position** – Inertial crossrange position (ft).
- **Tilt*Angle*(deg)** – Tilt angle from vertical (deg ×10).
- **Future*Angle*(deg)** – Projected tilt in +3 s (deg ×10).
- **Roll*Angle*(deg)** – Integrated roll angle (deg).
- **Reserved_1** – Reserved.
- **Reserved_2** – Reserved.
- **Reserved_3** – Reserved.
- **Rocket_FER_Hex** – Rocket-level flight event register (hex bitfield).
- **Apo_FER_Hex** – Apo channel FER (hex bitfield).
- **Main_FER_Hex** – Main channel FER (hex bitfield).
- **3rd_FER_Hex** – 3rd channel FER (hex bitfield).
- **4th_FER_Hex** – 4th channel FER (hex bitfield).
- **Liftoff** – Event flag (bitfield).
- **Apogee** – Event flag.
- **Press_Increasing** – Event flag.
- **Burnout_Coast** – Event flag.
- **Apo_fired** – Event flag.
- **Main_fired** – Event flag.
- **3rd_fired** – Event flag.
- **4th_fired** – Event flag.
- **Normal_Ascent** – Event flag.
- **Accel_Vel_LE_0** – Event flag (accel-only velocity ≤ 0).
- **ECI_Vvel_le_0** – Event flag (ECI vertical velocity ≤ 0).
- **Tilt_Exceeded_90deg** – Event flag.
- **Reserved** – Reserved event flag.

_Event flags then repeat per channel: Apo, Main, 3rd, 4th:_

- **LT_AGL1** – Event flag (altitude < threshold 1).
- **GT_AGL2** – Event flag (altitude > threshold 2).
- **LT_FANG1** – Event flag (tilt < threshold 1).
- **GT_FANG2** – Event flag (tilt > threshold 2).
- **GT_FUTANG** – Event flag (future tilt > threshold).
- **LT_TVAL1** – Event flag (time < threshold 1).
- **GT_TVAL2** – Event flag (time > threshold 2).
- **LT_VEL1** – Event flag (velocity < threshold 1).
- **GT_VEL2** – Event flag (velocity > threshold 2).
- **LT_BVEL1** – Event flag (baro velocity < threshold).
- **GT_BURN** – Event flag (burnout counter > threshold).
- **Armed** – Channel armed status.
- **Reserved** – Reserved.

---

### Tracker GPS

`TRACKER,DATE,TIME,GS_Lat,GS_Lon,GS_Alt_ASL,TRACKER_Lat,TRACKER_Lon,TRACKER_Alt_ASL,FIX,HORZV,VERTV,HEAD,FLAGS,#TOT,>40,>32,>24,RSSI_Down,RSSI_Up,Horizontal_range_(ft),Alt_AGL_(ft),Total_range_(ft),LoRa_Max_Range_(kft),LoRa_Success_Rate,BATT,GS_batt_v,Down_Sent,Down_Rcvd,Found_Sent,Up_Sent,Up_Rcvd,Found_rocket_ID,Found_rocket_lat,Found_rocket_lon,Found_rocket_altitude,Found_rocket_fix,Found_rocket_batt_v,Found_RSSI,GS_ASL_offset`

- **TRACKER** – Tracker ID string (user-defined, up to 11 chars).
- **DATE** – UTC date (YYYY-MM-DD).
- **TIME** – UTC time (hh:mm:ss).
- **GS_Lat** – Ground station latitude (decimal degrees).
- **GS_Lon** – Ground station longitude (decimal degrees).
- **GS_Alt_ASL** – Ground station altitude above sea level (ft).
- **TRACKER_Lat** – Tracker latitude (decimal degrees).
- **TRACKER_Lon** – Tracker longitude (decimal degrees).
- **TRACKER_Alt_ASL** – Tracker altitude above sea level (ft).
- **FIX** – GPS fix type (0 = no fix, 2 = 2D fix, 3 = 3D fix).
- **HORZV** – Horizontal velocity (ft/s).
- **VERTV** – Vertical velocity (ft/s).
- **HEAD** – Heading (degrees from North).
- **FLAGS** – GPS/telemetry status flags (bitfield for quality and error states).
- **#TOT** – Total number of satellites tracked.
- **>40** – Satellites with signal > 40 dB-Hz (excellent).
- **>32** – Satellites with signal > 32 dB-Hz (good).
- **>24** – Satellites with signal > 24 dB-Hz (usable).
- **RSSI_Down** – Received signal strength (dBm) of downlink packets at GS.
- **RSSI_Up** – Received signal strength (dBm) of uplink acks at tracker.
- **Horizontal*range*(ft)** – Horizontal ground distance between GS and tracker (ft).
- **Alt*AGL*(ft)** – Tracker altitude above launch pad (ft).
- **Total*range*(ft)** – Line-of-sight 3D distance between GS and tracker (ft).
- **LoRa*Max_Range*(kft)** – Estimated maximum theoretical range based on RSSI margin (kft).
- **LoRa_Success_Rate** – Percentage of packets successfully acknowledged (%).
- **BATT** – Tracker battery voltage (V).
- **GS_batt_v** – Ground station battery voltage (V).
- **Down_Sent** – Number of downlink packets sent by tracker.
- **Down_Rcvd** – Number of downlink packets received at GS.
- **Found_Sent** – Number of “found rocket” packets broadcast.
- **Up_Sent** – Number of uplink ack packets sent by GS.
- **Up_Rcvd** – Number of uplink ack packets received by tracker.
- **Found_rocket_ID** – ID of lost rocket relayed via “found rocket” mode.
- **Found_rocket_lat** – Latitude of found rocket (decimal degrees).
- **Found_rocket_lon** – Longitude of found rocket (decimal degrees).
- **Found_rocket_altitude** – Altitude of found rocket above sea level (ft).
- **Found_rocket_fix** – GPS fix type of found rocket (0/2/3).
- **Found_rocket_batt_v** – Battery voltage of found rocket (V).
- **Found_RSSI** – RSSI (dBm) of found rocket packet.
- **GS_ASL_offset** – Offset used to normalize GS altitude relative to pad (ft).

---

## Altus Metrum

### TeleMega

`#version,serial,flight,call,time,state,state_name,acceleration,pressure,altitude,height,speed,temperature,drogue_voltage,main_voltage,battery_voltage,accel_x,accel_y,accel_z,gyro_roll,gyro_pitch,gyro_yaw,mag_x,mag_y,mag_z,tilt,pyro,igniter_a,igniter_b,igniter_c,igniter_d,connected,locked,nsat,latitude,longitude,altitude,year,month,day,hour,minute,second,pad_dist,pad_range,pad_az,pad_el,pdop,hdop,vdop,sat01,sat02,sat03,sat04,sat05,sat06,sat07,sat08,sat09,sat10,sat11,sat12,sat13,sat14,sat15,sat16,sat17,sat18,sat19,sat20,sat21,sat22,sat23,sat24,sat25,sat26,sat27,sat28,sat29,sat30,sat31,sat32`

- **version** – Log file format version.
- **serial** – TeleMega hardware serial number.
- **flight** – Flight number stored in memory.
- **call** – User-configured callsign string.
- **time** – Seconds since boot or flight start.
- **state** – Numeric flight state ID (0–7).
- **state_name** – Human-readable state (idle, pad, boost, coast, apogee, drogue, main, landed).
- **acceleration** – Total acceleration magnitude (m/s²).
- **pressure** – Barometric pressure (Pa).
- **altitude** – Barometric altitude (m).
- **height** – Altitude above pad reference (m).
- **speed** – Vertical speed estimate (m/s).
- **temperature** – Internal sensor temperature (°C).
- **drogue_voltage** – Drogue channel voltage (V).
- **main_voltage** – Main channel voltage (V).
- **battery_voltage** – System battery voltage (V).
- **pyro** – Pyro continuity/status bitfield.
- **igniter_a** – Voltage continuity for igniter A (V).
- **igniter_b** – Voltage continuity for igniter B (V).
- **igniter_c** – Voltage continuity for igniter C (V).
- **igniter_d** – Voltage continuity for igniter D (V).
- **accel_x** – Acceleration X-axis (m/s²).
- **accel_y** – Acceleration Y-axis (m/s²).
- **accel_z** – Acceleration Z-axis (m/s²).
- **gyro_roll** – Gyro roll rate (deg/s).
- **gyro_pitch** – Gyro pitch rate (deg/s).
- **gyro_yaw** – Gyro yaw rate (deg/s).
- **mag_x** – Magnetometer X-axis (µT).
- **mag_y** – Magnetometer Y-axis (µT).
- **mag_z** – Magnetometer Z-axis (µT).
- **tilt** – Computed tilt angle from vertical (degrees).
- **connected** – Ground station connection status (0/1).
- **locked** – GPS lock flag (0 = no fix, 1 = locked).
- **nsat** – Number of satellites in solution.
- **latitude** – Tracker latitude (decimal degrees).
- **longitude** – Tracker longitude (decimal degrees).
- **altitude** – GPS-derived altitude (m).
- **year** – UTC year.
- **month** – UTC month.
- **day** – UTC day.
- **hour** – UTC hour.
- **minute** – UTC minute.
- **second** – UTC second.
- **pad_dist** – Horizontal distance from pad (m).
- **pad_range** – 3D slant range from pad (m).
- **pad_az** – Azimuth from pad (deg).
- **pad_el** – Elevation angle from pad (deg).
- **pdop** – Position dilution of precision.
- **hdop** – Horizontal dilution of precision.
- **vdop** – Vertical dilution of precision.
- **sat01** – Satellite 1 SNR (dB-Hz).
- **sat02** – Satellite 2 SNR (dB-Hz).
- **sat03** – Satellite 3 SNR (dB-Hz).
- **sat04** – Satellite 4 SNR (dB-Hz).
- **sat05** – Satellite 5 SNR (dB-Hz).
- **sat06** – Satellite 6 SNR (dB-Hz).
- **sat07** – Satellite 7 SNR (dB-Hz).
- **sat08** – Satellite 8 SNR (dB-Hz).
- **sat09** – Satellite 9 SNR (dB-Hz).
- **sat10** – Satellite 10 SNR (dB-Hz).
- **sat11** – Satellite 11 SNR (dB-Hz).
- **sat12** – Satellite 12 SNR (dB-Hz).
- **sat13** – Satellite 13 SNR (dB-Hz).
- **sat14** – Satellite 14 SNR (dB-Hz).
- **sat15** – Satellite 15 SNR (dB-Hz).
- **sat16** – Satellite 16 SNR (dB-Hz).
- **sat17** – Satellite 17 SNR (dB-Hz).
- **sat18** – Satellite 18 SNR (dB-Hz).
- **sat19** – Satellite 19 SNR (dB-Hz).
- **sat20** – Satellite 20 SNR (dB-Hz).
- **sat21** – Satellite 21 SNR (dB-Hz).
- **sat22** – Satellite 22 SNR (dB-Hz).
- **sat23** – Satellite 23 SNR (dB-Hz).
- **sat24** – Satellite 24 SNR (dB-Hz).
- **sat25** – Satellite 25 SNR (dB-Hz).
- **sat26** – Satellite 26 SNR (dB-Hz).
- **sat27** – Satellite 27 SNR (dB-Hz).
- **sat28** – Satellite 28 SNR (dB-Hz).
- **sat29** – Satellite 29 SNR (dB-Hz).
- **sat30** – Satellite 30 SNR (dB-Hz).
- **sat31** – Satellite 31 SNR (dB-Hz).
- **sat32** – Satellite 32 SNR (dB-Hz).

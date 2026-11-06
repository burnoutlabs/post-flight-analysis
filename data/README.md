# Flight data

One directory per flight, `data/<date>_<vehicle>_<event>/`:

- `raw/`: device logs as the devices or their apps wrote them. Stored
  byte-for-byte (`.gitattributes` sets `-text`), so the sha256 in each
  `interim/*.meta.json` matches on every OS. Exceptions are listed under
  [Modified files](#modified-files).
- `raw/src/`: for Hyperion II, the files under their original device names;
  `raw/` holds renamed copies of the primary logs. `pfa preprocess` reads
  `raw/` first and fills in from `raw/src/`.
- `interim/`: `pfa preprocess` output, one `<name>_std.csv` plus
  `<name>_std.meta.json` per device log ([schema](../docs/schema.md)).
- `figures/`: `pfa analyze` output.

## Inventory

Every flight log known for these vehicles, and where it is.

| Date | Vehicle / event | Device | Files | In `data/` |
| --- | --- | --- | --- | --- |
| 2021-07-25 | — | TeleMega s/n 6583, flight 0002 | `.csv`, `.eeprom`, `.kml` | **Excluded**, see below |
| 2022-06-24 | Prometheus, SAC 2022 | TeleMega s/n 6583, flight 0003 | `.csv`, `.eeprom`, `.kml` | `2022-06-24_prometheus_sac22/raw/` |
| 2022-06-24 | Prometheus, SAC 2022 | Altus Metrum s/n 5115, flight 0001 | `.csv` | `2022-06-24_prometheus_sac22/raw/` (modified, see below) |
| 2024-06-21 | Hyperion I, SAC 2024 | TeleMega s/n 6583, flight 0004 | `.csv`, `.eeprom`, `.kml` | `2024-06-21_hyperion1_sac24/raw/` |
| 2024-06-21 | Hyperion I, SAC 2024 | Featherweight GPS tracker | `.xlsx` | `2024-06-21_hyperion1_sac24/raw/` |
| 2025-08-21 | Hyperion II, LC 2025 | TeleMega s/n 6583, flight 0005 | `.csv`, `.eeprom`, `.kml` | `2025-08-21_hyperion2_lc25/raw/src/` (csv also as `raw/2025-08-21_redundant_telemega.csv`) |
| 2025-08-21 | Hyperion II, LC 2025 | Blue Raven "WERT FBR" | LR and HR `.csv`, summary `.csv`, deploy settings `.xlsx` | `2025-08-21_hyperion2_lc25/raw/src/` (LR also as `raw/2025-08-21_primary_blueraven.csv`) |
| 2025-08-21 | Hyperion II, LC 2025 | Featherweight GPS tracker | `.csv`, `.kml` | `2025-08-21_hyperion2_lc25/raw/src/` |

`pfa` parses the `.csv` and `.xlsx` logs. The `.eeprom` and `.kml` files are
kept as the device originals but not read.

## Deliberately excluded

- **2021-07-25, TeleMega s/n 6583, flight 0002.** The log covers 22 s with a
  maximum barometric height of 114 m and no meaningful speed: it is not a
  flight. Its GPS fix is not a launch site, so the files are not published.

## Modified files

- `2022-06-24_prometheus_sac22/raw/2022-06-24-serial-5115-flight-0001.csv`:
  the `call` (callsign) column is blanked on every row, as it already was in
  the s/n 6583 flight 0003 log. Every other byte is as logged, so this file is
  not the device's original bytes.

## Notes on specific files

- `2025-08-21_hyperion2_lc25/raw/src/WERT FBR_summary_08-21-2025_14_11_45_.csv`
  is the Blue Raven app's flight summary, kept as exported. Most of its flight
  figures read zero (max altitude, event times, descent rates), so do not use
  them. `pfa` reads only the firmware and serial number from it.

## Provenance

- The s/n 6583 `.kml` files, the Blue Raven summary CSV and the original
  (not whitespace-reflowed) tracker KML come from the consolidated flight
  data, byte-for-byte.
- The s/n 5115 log comes from `werocketry/airbrakes-SR`,
  `flight_sims/Prometheus_flight_data/`, with the callsign blanked as above.

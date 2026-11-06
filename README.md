# post-flight-analysis

Flight logs from our rockets, and `pfa`, a small CLI that turns each device's
log into one standard CSV format and plots and summarises the flights.

This repository is a standalone copy of `werocketry/post-flight-analysis`,
carried over with its history. It is not synced with the original.

## Layout

```text
src/pfa/            the pfa package (CLI in cli.py, one parser per device in parsers/)
data/               one directory per flight; see data/README.md
  <date>_<vehicle>_<event>/   e.g. 2025-08-21_hyperion2_lc25
    README.md       a short note on the flight and its logs
    raw/            device logs, stored byte-for-byte (raw/src/: original file names)
    interim/        pfa preprocess output: <name>_std.csv + <name>_std.meta.json
    figures/        pfa analyze output: flight_profile.png
docs/               schema of the interim files (docs/schema.md) and device/data notes
notebooks/playground/   exploratory scripts that predate pfa
tests/              pytest suite (golden files, device detection, smoke tests)
justfile            setup / check / test / preprocess recipes
```

## Devices

| Device | Files | Parser | Interim output |
| --- | --- | --- | --- |
| Altus Metrum TeleMega | AltOS CSV export with IMU columns | `parsers/telemega.py` | `telemega_std.csv` |
| Other Altus Metrum loggers | AltOS CSV export without IMU columns | `parsers/telemega.py` | `altusmetrum_<serial>_std.csv` |
| Featherweight Blue Raven, low rate | app CSV export | `parsers/blueraven.py` | `blueraven_std.csv` |
| Featherweight Blue Raven, high rate | app CSV export (IMU) | `parsers/blueraven_hr.py` | `blueraven_hr_std.csv` |
| Featherweight Blue Raven summary | app summary CSV | `parsers/blueraven_summary.py` | none; serial and firmware go into the Blue Raven meta files |
| Featherweight GPS tracker | app `.csv` or `.xlsx` export | `parsers/featherweight.py` | `featherweight_std.csv` |

Files are recognised by their content, not their names: `_sniff_kind` in
`src/pfa/cli.py` reads each file's header. `.eeprom` and `.kml` files are kept
in `raw/` but not read. Logs downloaded over USB with `braven download-low` /
`download-high` are not supported yet.

A second TeleMega in one flight is written as `telemega_<serial>_std.csv`. A
second copy of a log from the same serial is skipped; `raw/` is read before
`raw/src/`.

## Install

Python 3.9 or later. With [uv](https://docs.astral.sh/uv/):

```sh
uv sync
uv run pfa --help
```

or with pip, in a virtual environment:

```sh
pip install -e .
pfa --help
```

## Usage

```sh
pfa preprocess data/2025-08-21_hyperion2_lc25   # raw/ -> interim/*_std.csv + *.meta.json
pfa analyze data/2025-08-21_hyperion2_lc25      # interim/ -> figures/flight_profile.png + summary
pfa compare data                                # one summary row per preprocessed flight
```

Prefix each command with `uv run` if you installed with uv. `pfa preprocess`
takes `--tz` (default `America/Toronto`), the time zone the Blue Raven app
wrote its local timestamps in, and `-v` to list the files it detected.

`analyze` and `compare` take their summary from the TeleMega log when there is
one, then the Blue Raven, then the tracker.

## Adding a flight

1. Create `data/<date>_<vehicle>_<event>/raw/` and copy the device files in
   unchanged. Add a short `README.md`, and list the logs in `data/README.md`.
2. Run `pfa preprocess` and `pfa analyze` on the new directory and commit
   `interim/` and `figures/` with the raw files.

## Development

With [just](https://github.com/casey/just) and uv:

```sh
just setup       # uv sync
just check       # ruff format --check + ruff check
just test        # pytest
just preprocess  # regenerate interim/ for every flight
```

The golden tests rerun `pfa preprocess` on each flight and require the
committed `interim/*_std.csv` byte-for-byte. A parser change that alters
output fails them; if the change is intended, run `just preprocess`, commit
the regenerated files with the code, and bump `SCHEMA_VERSION` if the columns
changed (see `docs/schema.md`). CI runs `just check` and `just test` on Linux
and Windows.

## License

- **Code**: Apache-2.0
- **Data**: CC BY 4.0

See `LICENSE` and `LICENSES/`.

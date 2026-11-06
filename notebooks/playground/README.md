# Playground

This is where we play with data so that our program is grounded in reality.

## Running these scripts here

These exploratory scripts were written before `pfa` and are kept as they were
written. They are not part of the package and are not linted. Each one reads
its input from the current directory under a short name and writes its
outputs next to it. Outputs are not committed (see `.gitignore`); rerun a
script to regenerate them.

Copy the inputs from the Hyperion II flight into a scratch directory under the
names the scripts expect, then run the scripts from there:

| Name the scripts expect | File in this repository |
| --- | --- |
| `2025-08-21_redundant_telemega.csv` (`altusmetrum/`) | `data/2025-08-21_hyperion2_lc25/raw/2025-08-21_redundant_telemega.csv` |
| `2025-08-21_gps_tracker.csv` | `data/2025-08-21_hyperion2_lc25/raw/src/FthrWt03337_08-21-2025_13_28_45.csv` |
| `2025-08-21_primary_blueraven_hr.csv` | `data/2025-08-21_hyperion2_lc25/raw/src/WERT FBR HR_08-21-2025_14_11_45.csv` |
| `2025-08-21_primary_blueraven_lr.csv` | `data/2025-08-21_hyperion2_lc25/raw/2025-08-21_primary_blueraven.csv` |

In `featherweight/`, run `trim_gps_by_lr_window.py` first: it writes
`2025-08-21_gps_tracker_trimmed.csv`, which `analyze_fw_sampling.py` and
`gps_interval_outliers.py` read. The other scripts need only the inputs above.

The HR/LR merge in `br_hrlr_merge.py` and `br_hrlr_merge_sync.py` is not in
`pfa` yet; `docs/blue_raven_hr-lr_sync_merge.md` describes it.

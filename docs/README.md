# Docs

| Doc | What it covers |
| --- | --- |
| [schema.md](schema.md) | The interim schema `pfa preprocess` writes. **Canonical** for column names, units and versioning |
| [01_definition_scoping.md](01_definition_scoping.md) | Objectives and scope of the log-parsing work |
| [02_datasources_understanding.md](02_datasources_understanding.md) | What each device log contains |
| [03_exploratory_data_analysis.md](03_exploratory_data_analysis.md) | Column-by-column exploration of the device logs |
| [04_data_prioritization.md](04_data_prioritization.md) | Which fields matter most, by analysis need |
| [05_generic_data_format.md](05_generic_data_format.md) | An earlier proposal for a generic flight time-series format (`flight.csv` + `metadata.json`). Not what `pfa` writes; see `schema.md` |
| [blue_raven_hr-lr_sync_merge.md](blue_raven_hr-lr_sync_merge.md) | Merging Blue Raven high-rate and low-rate logs on the `Sync` counter; implemented only in `notebooks/playground/featherweight/` so far |
| [data_insight_guides/](data_insight_guides/) | Per-device field guides: Blue Raven, Featherweight tracker, TeleMega |

Docs 01–05, the merge doc and the field guides came over with the
consolidated flight data and are unchanged.

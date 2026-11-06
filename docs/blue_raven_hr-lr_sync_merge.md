# Blue Raven HR/LR Merge Using Sync

## 1) Inputs

- HR CSV: `Time` (UTC), `Flight_Time_(s)`, `Sync` (0–249 wrap @ 250 ms), ~500 Hz.
- LR CSV: `Time` (UTC), `Flight_Time_(s)`, `Sync` (same), ~50 Hz.

## 2) Output Controls

- `output_rate`: `hr` (500 Hz), `lr` (50 Hz), or `custom` with `dt`.
- `bounds`: `overlap` (max start, min end), `union` (min start, max end), `hr`, `lr`.
- `align_by`: `utc` or `sync`.
- `method_numeric`:
  - Upsample: `linear`, `nearest`, `ffill`.
  - Downsample: `mean`, `median`, `nearest`.
- `method_flags`: `nearest` or `ffill`.
- `sync_tolerance_counts`: int, default 2 (≈2 ms).
- `time_tolerance_s`: float, default 0.015.

## 3) Canonical Time Index

- Parse `Year,Month,Day,Time` → UTC timestamps `t_hr` and `t_lr`.
- Span by `bounds`:
  - `overlap`: `[max(min(t_hr), min(t_lr)), min(max(t_hr), max(t_lr))]`.
  - `union`: `[min(min(.)), max(max(.))]`.
  - `hr`: HR span, `lr`: LR span.
- Target index:
  - `hr`: HR timestamps within span.
  - `lr`: LR timestamps within span.
  - `custom`: regular grid `t0:dt:t1`.

## 4) Sync Phase Estimation

- Pick initial overlap window.
- Pair LR→nearest HR by UTC within `time_tolerance_s`.
- Compute `delta_sync = mode((Sync_hr - Sync_lr) mod 250)`.
- Matching rule thereafter:
  - Accept HR for LR row if `((Sync_hr - Sync_lr - delta_sync) mod 250) <= sync_tolerance_counts`.
  - If none, fall back to UTC nearest within `time_tolerance_s`.
  - Else leave NaN.

## 5) Merge Strategies

### A) Upsample LR → HR (expand to 500 Hz)

- Target index: HR timestamps in span.
- LR numeric: interpolate per `method_numeric` (time-based).
- LR flags/hex/bitfields: `nearest` with sync rule, else `ffill`.
- Keep HR-native columns as-is.

### B) Downsample HR → LR (condense to 50 Hz)

- Target index: LR timestamps in span.
- HR numeric:
  - `nearest` within `time_tolerance_s` with sync rule, or
  - window aggregate centered on LR time (±10 ms) using `mean`/`median`.
- HR flags: `any` in window or `nearest`.
- Keep LR-native columns as-is.

### C) Custom Grid

- Project both sources onto regular grid with step `dt` using same rules.
- Resolve conflicts per column priority if needed.

## 6) Bounds and Padding

- `union` or single-source bounds → missing source columns outside its span are NaN.
- `overlap` → trim to common window.
- No extrapolation unless explicitly requested.

## 7) Column Typing

- Continuous: floats (accel, gyro, quat, volts, temp, pressure, velocities, positions).
- Flags/bitfields: integers or strings; do not interpolate.
- FER hex: keep as strings (optional later parse to bits).

## 8) Quality Checks (report)

- Cadence check: HR ≈ 0.002 s, LR ≈ 0.020 s.
- Overlap duration and coverage by source.
- Sync quality:
  - Share meeting `sync_tolerance_counts`.
  - Median absolute UTC delta for matched pairs.

## 9) Output Schema

- Index: UTC timestamp.
- Columns: prefix by source to avoid collisions (e.g., `HR_Accel_X`, `LR_Baro_Altitude_ASL`).
- Optional unified derived fields after merge (e.g., a single altitude chooser).
- Sidecar metadata JSON:
  - `source_files`, `output_rate`, `bounds`, `align_by`, `delta_sync`, `tolerances`,
    `coverage`, `column_map`, `units`.

## 10) Edge Cases

- Missing `Time`: synthesize from `Flight_Time_(s)`; still use `Sync` constraint.
- Clock skew: estimate median `(t_lr - t_hr)` over matched pairs; shift one axis.
- Unstable `delta_sync`: fallback to UTC-only nearest with wider `time_tolerance_s`.

## 11) Performance

- Use `merge_asof` on UTC for nearest pairing, apply sync filter post-merge.
- Categoricals for flags to reduce memory.

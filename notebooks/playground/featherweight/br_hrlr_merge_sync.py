# Merge Blue Raven High-Rate (HR, 500 Hz) and Low-Rate (LR, 50 Hz) logs using Sync.
# Options:
#   - Output cadence: HR, LR, or custom dt
#   - Bounds: overlap, union, hr, lr
#   - Alignment: UTC and Sync-based pairing with tolerance
#   - Upsample LR → HR (interpolate numeric; nearest/ffill flags)
#   - Downsample HR → LR (nearest or window aggregate)
#   - Missing spans are NaN without extrapolation
#
# Usage:
#   - Set CONFIG below and run:  python merge_br_hr_lr.py
#
# Dependencies: pandas, numpy

from __future__ import annotations
import json
import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# =========================
# ======== CONFIG =========
# =========================
HR_CSV = "2025-08-21_primary_blueraven_hr.csv"
LR_CSV = "2025-08-21_primary_blueraven_lr.csv"
OUTPUT_CSV = "2025-08-21_primary_blueraven_merged_hrlr_sync.csv"
OUTPUT_META_JSON = "2025-08-21_primary_blueraven_merged_hrlr_sync.meta.json"

# Output cadence: 'hr', 'lr', or 'custom'
OUTPUT_RATE = "hr"
# If OUTPUT_RATE == 'custom', specify a step in seconds
CUSTOM_DT_S: Optional[float] = None  # e.g., 0.01

# Merge bounds: 'overlap', 'union', 'hr', or 'lr'
BOUNDS = "union"

# Alignment base: 'utc' (always) + Sync filter for discrete fields
ALIGN_BY = "utc"  # keep as 'utc' (Sync is applied as a constraint for flags)

# Tolerances
TIME_TOLERANCE_S = 0.015  # nearest-match tolerance for UTC pairing
SYNC_TOL_COUNTS = 2  # allowed |delta sync| counts (0..250), i.e., ≤ 2

# Methods
NUMERIC_UP_METHOD = "ffill"  # for LR→HR interpolation: 'linear'|'nearest'|'ffill'
NUMERIC_DOWN_METHOD = "nearest"  # for HR→LR: 'nearest'|'mean'|'median'
FLAG_METHOD = "ffill"  # for discrete fields: 'nearest'|'ffill'
WINDOW_HALF_WIDTH_S = 0.010  # for window aggregations when condensing

# Prefix columns to avoid name collisions
HR_PREFIX = "HR_"
LR_PREFIX = "LR_"

# =========================
# ====== IMPLEMENT =========
# =========================

SYNC_MOD = 250  # Sync rolls at 250 ms per device spec


@dataclass
class MergeSettings:
    output_rate: str
    custom_dt_s: Optional[float]
    bounds: str
    align_by: str
    time_tolerance_s: float
    sync_tol_counts: int
    numeric_up_method: str
    numeric_down_method: str
    flag_method: str
    window_half_width_s: float
    hr_prefix: str
    lr_prefix: str


@dataclass
class MergeReport:
    hr_rows: int
    lr_rows: int
    output_rows: int
    span_start: str
    span_end: str
    span_seconds: float
    bounds_mode: str
    delta_sync_est: Optional[int]
    delta_sync_samples: int
    utc_match_median_ms: Optional[float]
    lr_to_hr_flag_match_rate: Optional[float]
    hr_to_lr_flag_match_rate: Optional[float]
    coverage_nonnull_ratio: Dict[str, float]
    source_files: Dict[str, str]


def _parse_utc_from_cols(df: pd.DataFrame) -> pd.Series:
    # Expect columns Year, Month, Day, Time ("HH:MM:SS.sss")
    # If 'Time' lacks timezone, assume UTC.
    if not {"Year", "Month", "Day", "Time"}.issubset(df.columns):
        raise ValueError("Expected columns Year, Month, Day, Time")
    y = df["Year"].astype(int).astype(str)
    m = df["Month"].astype(int).astype(str).str.zfill(2)
    d = df["Day"].astype(int).astype(str).str.zfill(2)
    ts = y + "-" + m + "-" + d + " " + df["Time"].astype(str)
    t = pd.to_datetime(ts, utc=True, errors="coerce")
    return t


def _read_br_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["_utc"] = _parse_utc_from_cols(df)
    if "Sync" not in df.columns:
        raise ValueError("Missing 'Sync' column in file: " + path)
    df["Sync"] = (
        pd.to_numeric(df["Sync"], errors="coerce").fillna(0).astype(int) % SYNC_MOD
    )
    df = df.sort_values("_utc").reset_index(drop=True)
    return df


def _pick_bounds(
    t_hr: pd.Series, t_lr: pd.Series, mode: str
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    hr_min, hr_max = t_hr.min(), t_hr.max()
    lr_min, lr_max = t_lr.min(), t_lr.max()
    if mode == "overlap":
        start = max(hr_min, lr_min)
        end = min(hr_max, lr_max)
    elif mode == "union":
        start = min(hr_min, lr_min)
        end = max(hr_max, lr_max)
    elif mode == "hr":
        start, end = hr_min, hr_max
    elif mode == "lr":
        start, end = lr_min, lr_max
    else:
        raise ValueError("bounds must be one of: overlap|union|hr|lr")
    if end < start:
        raise ValueError("Selected bounds have no overlap window")
    return start, end


def _clip_span(
    df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    m = (df["_utc"] >= start) & (df["_utc"] <= end)
    return df.loc[m].copy()


def _estimate_delta_sync(
    hr: pd.DataFrame,
    lr: pd.DataFrame,
    time_tolerance_s: float,
) -> Tuple[Optional[int], int, Optional[float]]:
    # prefer exact-time intersections (most robust)
    hr_key = hr[["_utc", "Sync"]].rename(columns={"Sync": "Sync_hr"})
    lr_key = lr[["_utc", "Sync"]].rename(columns={"Sync": "Sync_lr"})
    exact = pd.merge(lr_key, hr_key, on="_utc", how="inner")
    if not exact.empty:
        delta = (exact["Sync_hr"].astype(int) - exact["Sync_lr"].astype(int)) % SYNC_MOD
        delta_sync = int(delta.mode().iloc[0])
        return delta_sync, int(len(exact)), 0.0  # exact matches ⇒ 0 ms

    # fallback: nearest merge
    matched = pd.merge_asof(
        lr_key.sort_values("_utc"),
        hr_key.sort_values("_utc"),
        on="_utc",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=time_tolerance_s),
    ).dropna(subset=["Sync_hr", "Sync_lr"])
    if matched.empty:
        return None, 0, None

    delta = (matched["Sync_hr"].astype(int) - matched["Sync_lr"].astype(int)) % SYNC_MOD
    delta_sync = int(delta.mode().iloc[0])

    # median absolute time error (ms)
    # use right_on to get the true HR time chosen by asof
    hr_idx = hr_key.rename(columns={"_utc": "_utc_hr"})
    lr_to_hr = pd.merge_asof(
        lr_key[["_utc"]].sort_values("_utc"),
        hr_idx.sort_values("_utc_hr"),
        left_on="_utc",
        right_on="_utc_hr",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=time_tolerance_s),
    )
    dt_ms = (
        lr_to_hr["_utc_hr"] - lr_to_hr["_utc"]
    ).dropna().dt.total_seconds().abs() * 1000.0
    med_ms = float(dt_ms.median()) if not dt_ms.empty else None
    return delta_sync, int(len(matched)), med_ms


def _split_columns(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns (numeric_cols, flag_cols, other_cols)
    Flags = event flags and FER-like hex strings. Numeric = float/int continuous.
    """
    ignore = {"Year", "Month", "Day", "Time", "Sync", "_utc"}
    # Heuristics
    fer_like = [c for c in df.columns if "FER" in c or "Hex" in c]
    common_event_flags = {
        "Liftoff",
        "Apogee",
        "Press_Increasing",
        "Burnout_Coast",
        "Apo_fired",
        "Main_fired",
        "3rd_fired",
        "4th_fired",
        "Normal_Ascent",
        "Accel_Vel_LE_0",
        "ECI_Vvel_le_0",
        "Tilt Exceeded 90deg",
        "Reserved",
        "LT_AGL1",
        "GT_AGL2",
        "LT_FANG1",
        "GT_FANG2",
        "GT_FUTANG",
        "LT_TVAL1",
        "GT_TVAL2",
        "LT_VEL1",
        "GT_VEL2",
        "LT_BVEL1",
        "GT_BURN",
        "Armed",
    }
    event_cols = [c for c in df.columns if c in common_event_flags]
    # Add columns that look strictly boolean/integer 0/1 across data
    boolish = []
    for c in df.columns:
        if c in ignore or c in fer_like or c in event_cols:
            continue
        if pd.api.types.is_integer_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            # treat as flag ONLY if 0/1 values or small set
            vals = pd.Series(df[c].dropna().unique())
            if len(vals) <= 4 and set(vals.astype(int)).issubset({0, 1, 2, 3}):
                boolish.append(c)
    flag_cols = list(dict.fromkeys(fer_like + event_cols + boolish))
    # Numeric are continuous types excluding flags and ignore
    numeric_cols = [
        c
        for c in df.columns
        if c not in ignore
        and c not in flag_cols
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    other_cols = [
        c
        for c in df.columns
        if c not in ignore and c not in numeric_cols and c not in flag_cols
    ]
    return numeric_cols, flag_cols, other_cols


def _time_index_for_output(
    hr: pd.DataFrame,
    lr: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    output_rate: str,
    custom_dt_s: Optional[float],
) -> pd.DatetimeIndex:
    if output_rate == "hr":
        t = hr.loc[(hr["_utc"] >= start) & (hr["_utc"] <= end), "_utc"]
        return pd.DatetimeIndex(t.values, tz="UTC")
    elif output_rate == "lr":
        t = lr.loc[(lr["_utc"] >= start) & (lr["_utc"] <= end), "_utc"]
        return pd.DatetimeIndex(t.values, tz="UTC")
    elif output_rate == "custom":
        if not custom_dt_s or custom_dt_s <= 0:
            raise ValueError("custom_dt_s must be positive when output_rate=='custom'")
        # Build regular grid
        n = int(math.floor((end - start).total_seconds() / custom_dt_s)) + 1
        # Guard against huge n
        if n > 5_000_000:
            raise ValueError("Custom grid too large")
        return pd.date_range(
            start=start,
            periods=n,
            freq=pd.to_timedelta(custom_dt_s, unit="s"),
            tz="UTC",
        )
    else:
        raise ValueError("output_rate must be 'hr'|'lr'|'custom'")


def _apply_sync_mask(
    left_times: pd.Series,
    left_sync: pd.Series,
    right_times: pd.Series,
    right_sync: pd.Series,
    delta_sync: Optional[int],
    time_tolerance_s: float,
    sync_tol_counts: int,
) -> pd.Series:
    # time window gate
    dt = (left_times - right_times).abs()
    ok_time = right_times.notna() & (dt <= pd.Timedelta(seconds=time_tolerance_s))
    if not ok_time.any() or delta_sync is None:
        return ok_time

    # dynamic allowed Sync drift: base tol OR the implied ms drift (+1 margin)
    dt_ms = dt.dt.total_seconds().abs() * 1000.0
    allowed = np.maximum(sync_tol_counts, np.ceil(dt_ms).astype("int64") + 1)

    ds = (
        left_sync.fillna(0).astype("int64")
        - right_sync.fillna(0).astype("int64")
        - int(delta_sync)
    ) % SYNC_MOD
    ds = np.minimum(ds, SYNC_MOD - ds)  # shortest modular distance [0..SYNC_MOD/2]
    ok_sync = ds <= allowed
    return ok_time & ok_sync


def _nearest_with_sync(
    target_df: pd.DataFrame,  # columns: _utc, Sync_target
    source_df: pd.DataFrame,  # columns: _utc, Sync, <payload>
    payload_cols: List[str],
    delta_sync: Optional[int],
    time_tolerance_s: float,
    sync_tol_counts: int,
    fill_method: str = "nearest",
) -> pd.DataFrame:
    # keep source time separately so we can compute true dt
    s_key = (
        source_df[["_utc", "Sync"] + payload_cols]
        .rename(columns={"_utc": "_utc_src"})
        .sort_values("_utc_src")
    )
    t_key = target_df[["_utc", "Sync_target"]].sort_values("_utc")

    merged = pd.merge_asof(
        t_key,
        s_key,
        left_on="_utc",
        right_on="_utc_src",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=time_tolerance_s),
    )
    mask = _apply_sync_mask(
        left_times=merged["_utc"],
        left_sync=merged["Sync_target"],
        right_times=merged["_utc_src"],  # <-- real source time
        right_sync=merged["Sync"],
        delta_sync=delta_sync,
        time_tolerance_s=time_tolerance_s,
        sync_tol_counts=sync_tol_counts,
    )
    out = merged[payload_cols].where(mask)
    out.index = t_key.index
    if fill_method == "ffill":
        out = out.ffill()
    elif fill_method != "nearest":
        raise ValueError("fill_method must be 'nearest' or 'ffill'")
    return out.reindex(target_df.index)


def _numeric_interpolate_to_index(
    source_numeric: pd.DataFrame, target_index: pd.DatetimeIndex, method: str
) -> pd.DataFrame:
    s = source_numeric.copy()
    s = s[~s.index.duplicated(keep="first")]
    # Reindex to target
    s2 = s.reindex(target_index)
    if method == "linear":
        return s2.interpolate(method="time", limit_area="inside")
    elif method == "nearest":
        return s2.interpolate(method="nearest", limit_area="inside")
    elif method == "ffill":
        return s2.ffill()
    else:
        raise ValueError("numeric upsample method must be 'linear'|'nearest'|'ffill'")


def _numeric_downsample_to_times(
    hr_numeric: pd.DataFrame,
    lr_times: pd.Series,
    lr_sync: pd.Series,
    hr_sync: pd.Series,
    delta_sync: Optional[int],
    method: str,
    time_tolerance_s: float,
    window_half_width_s: float,
    sync_tol_counts: int,
) -> pd.DataFrame:
    # Nearest with sync
    if method == "nearest":
        left = pd.DataFrame(
            {"_utc": lr_times.values, "Sync_target": lr_sync.values}
        ).sort_values("_utc")

        right = hr_numeric.reset_index()  # index is _utc for HR
        right = right.rename(columns={"_utc": "_utc_hr"})
        right["Sync"] = hr_sync.values  # align by order (same span)

        merged = pd.merge_asof(
            left,
            right.sort_values("_utc_hr"),
            left_on="_utc",
            right_on="_utc_hr",
            direction="nearest",
            tolerance=pd.Timedelta(seconds=time_tolerance_s),
        )

        mask = _apply_sync_mask(
            left_times=merged["_utc"],
            left_sync=merged["Sync_target"],
            right_times=merged["_utc_hr"],
            right_sync=merged["Sync"],
            delta_sync=delta_sync,
            time_tolerance_s=time_tolerance_s,
            sync_tol_counts=sync_tol_counts,
        )

        out = merged[hr_numeric.columns].where(mask)
        out.index = left.index
        out = out.reindex(pd.RangeIndex(len(lr_times))).sort_index()
        out.index = lr_times.index
        return out

    # Window aggregation
    out = pd.DataFrame(index=lr_times.index, columns=hr_numeric.columns, dtype=float)
    # Precompute for efficiency
    hr_ts = hr_numeric.index.view("int64")  # ns
    half = int(window_half_width_s * 1e9)
    for i, t in enumerate(lr_times.view("int64")):
        left = t - half
        right = t + half
        lo = np.searchsorted(hr_ts, left, side="left")
        hi = np.searchsorted(hr_ts, right, side="right")
        if hi <= lo:
            continue
        window = hr_numeric.iloc[lo:hi]
        if method == "mean":
            agg = window.mean(axis=0)
        elif method == "median":
            agg = window.median(axis=0)
        else:
            raise ValueError(
                "numeric downsample method must be 'nearest'|'mean'|'median'"
            )
        out.iloc[i] = np.array(agg.values)
    return out


def merge_br_hr_lr(
    hr_csv: str,
    lr_csv: str,
    output_csv: str,
    metadata_json: str,
    merge_settings: MergeSettings,
) -> MergeReport:
    # Read
    hr = _read_br_csv(hr_csv)
    lr = _read_br_csv(lr_csv)

    # Bounds
    start, end = _pick_bounds(hr["_utc"], lr["_utc"], merge_settings.bounds)
    hr_span = _clip_span(hr, start, end)
    lr_span = _clip_span(lr, start, end)

    # Split columns
    hr_num, hr_flag, hr_other = _split_columns(hr_span)
    lr_num, lr_flag, lr_other = _split_columns(lr_span)

    # Estimate delta sync on overlap
    delta_sync, sync_n, med_ms = _estimate_delta_sync(
        hr_span, lr_span, merge_settings.time_tolerance_s
    )

    # Build target index
    target_index = _time_index_for_output(
        hr=hr,
        lr=lr,
        start=start,
        end=end,
        output_rate=merge_settings.output_rate,
        custom_dt_s=merge_settings.custom_dt_s,
    )

    # Base frame with index
    out = pd.DataFrame(index=target_index)

    # Assemble according to output cadence
    coverage = {}

    if merge_settings.output_rate == "hr":
        # Start with HR native aligned to target (subset of HR span)
        hr_on_target = hr_span.set_index("_utc").reindex(target_index)
        # Keep all HR columns with prefix (except Sync which we keep separately)
        hr_payload_cols = [c for c in hr_on_target.columns if c not in {"Sync"}]
        out[[merge_settings.hr_prefix + c for c in hr_payload_cols]] = hr_on_target[
            hr_payload_cols
        ]

        # Upsample LR numeric to HR timeline
        if lr_num:
            lr_numeric = lr_span.set_index("_utc")[lr_num]
            lr_numeric_interp = _numeric_interpolate_to_index(
                lr_numeric, target_index, merge_settings.numeric_up_method
            )
            out[[merge_settings.lr_prefix + c for c in lr_num]] = (
                lr_numeric_interp.values
            )

        # Discrete/flags from LR nearest+sync onto HR timeline
        if lr_flag:
            idx_df = pd.DataFrame({"_utc": target_index}, index=target_index)
            # HR Sync at target times
            hr_sync_on_target = hr_span.set_index("_utc")["Sync"].reindex(target_index)
            idx_df["Sync_target"] = hr_sync_on_target.values
            lr_flags_src = lr_span[["_utc", "Sync"] + lr_flag]

            # For flags, use time-only matching without sync filtering since flags change less frequently
            lr_flags_on_hr = _nearest_with_sync(
                target_df=idx_df,
                source_df=lr_flags_src,
                payload_cols=lr_flag,
                delta_sync=None,  # Disable sync filtering for flags
                time_tolerance_s=merge_settings.time_tolerance_s,
                sync_tol_counts=merge_settings.sync_tol_counts,
                fill_method=merge_settings.flag_method,
            )
            lr_flags_on_hr.columns = [
                merge_settings.lr_prefix + c for c in lr_flags_on_hr.columns
            ]
            out = out.join(lr_flags_on_hr)

    elif merge_settings.output_rate == "lr":
        # Start with LR native aligned to target
        lr_on_target = lr_span.set_index("_utc").reindex(target_index)
        lr_payload_cols = [c for c in lr_on_target.columns if c not in {"Sync"}]
        out[[merge_settings.lr_prefix + c for c in lr_payload_cols]] = lr_on_target[
            lr_payload_cols
        ]

        # Downsample HR numeric to LR times
        if hr_num:
            hr_numeric = hr_span.set_index("_utc")[hr_num]
            hr_sync = hr_span.set_index("_utc")["Sync"]
            lr_times = pd.Series(lr_on_target.index, index=lr_on_target.index)
            lr_sync = lr_on_target["Sync"]
            hr_to_lr = _numeric_downsample_to_times(
                hr_numeric=hr_numeric,
                lr_times=lr_times,
                lr_sync=lr_sync,
                hr_sync=hr_sync,
                delta_sync=delta_sync,
                method=merge_settings.numeric_down_method,
                time_tolerance_s=merge_settings.time_tolerance_s,
                window_half_width_s=merge_settings.window_half_width_s,
                sync_tol_counts=merge_settings.sync_tol_counts,
            )
            hr_to_lr.columns = [merge_settings.hr_prefix + c for c in hr_to_lr.columns]
            out = out.join(hr_to_lr)

        # HR flags (rare) would be processed similarly; LR flags are already present native.

    else:  # custom grid
        # Project HR numeric to grid
        if hr_num:
            hr_numeric = hr_span.set_index("_utc")[hr_num]
            hr_numeric_interp = _numeric_interpolate_to_index(
                hr_numeric, target_index, "linear"
            )
            hr_numeric_interp.columns = [
                merge_settings.hr_prefix + c for c in hr_numeric_interp.columns
            ]
            out = out.join(hr_numeric_interp)
        # HR flags: nearest with sync onto custom grid if possible
        if hr_flag:
            # For custom grid we don't have native Sync; approximate with nearest HR Sync
            idx_df = pd.DataFrame({"_utc": target_index})
            hr_sync_on_grid = pd.merge_asof(
                idx_df.sort_values("_utc"),
                hr_span[["_utc", "Sync"]].sort_values("_utc"),
                on="_utc",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=merge_settings.time_tolerance_s),
            )["Sync"]
            idx_df["Sync_target"] = hr_sync_on_grid
            hr_flags_src = hr_span[["_utc", "Sync"] + hr_flag]
            hr_flags_on_grid = _nearest_with_sync(
                target_df=idx_df,
                source_df=hr_flags_src,
                payload_cols=hr_flag,
                delta_sync=0,  # same source, treat delta as 0
                time_tolerance_s=merge_settings.time_tolerance_s,
                sync_tol_counts=merge_settings.sync_tol_counts,
                fill_method=merge_settings.flag_method,
            )
            hr_flags_on_grid.columns = [
                merge_settings.hr_prefix + c for c in hr_flags_on_grid.columns
            ]
            out = out.join(hr_flags_on_grid)

        # Project LR numeric to grid
        if lr_num:
            lr_numeric = lr_span.set_index("_utc")[lr_num]
            lr_numeric_interp = _numeric_interpolate_to_index(
                lr_numeric, target_index, "linear"
            )
            lr_numeric_interp.columns = [
                merge_settings.lr_prefix + c for c in lr_numeric_interp.columns
            ]
            out = out.join(lr_numeric_interp)
        # LR flags: nearest with sync onto grid
        if lr_flag:
            idx_df = pd.DataFrame({"_utc": target_index})
            # approximate Sync at grid by nearest LR
            lr_sync_on_grid = pd.merge_asof(
                idx_df.sort_values("_utc"),
                lr_span[["_utc", "Sync"]].sort_values("_utc"),
                on="_utc",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=merge_settings.time_tolerance_s),
            )["Sync"]
            idx_df["Sync_target"] = lr_sync_on_grid
            lr_flags_src = lr_span[["_utc", "Sync"] + lr_flag]
            lr_flags_on_grid = _nearest_with_sync(
                target_df=idx_df,
                source_df=lr_flags_src,
                payload_cols=lr_flag,
                delta_sync=0,  # same source relative
                time_tolerance_s=merge_settings.time_tolerance_s,
                sync_tol_counts=merge_settings.sync_tol_counts,
                fill_method=merge_settings.flag_method,
            )
            lr_flags_on_grid.columns = [
                merge_settings.lr_prefix + c for c in lr_flags_on_grid.columns
            ]
            out = out.join(lr_flags_on_grid)

    # Coverage ratios
    coverage = {c: float(out[c].notna().mean()) for c in out.columns}

    # Save
    out.reset_index(names=["UTC"]).to_csv(output_csv, index=False)

    # Report
    report = MergeReport(
        hr_rows=int(len(hr)),
        lr_rows=int(len(lr)),
        output_rows=int(len(out)),
        span_start=start.isoformat(),
        span_end=end.isoformat(),
        span_seconds=float((end - start).total_seconds()),
        bounds_mode=merge_settings.bounds,
        delta_sync_est=delta_sync if delta_sync is not None else None,
        delta_sync_samples=int(sync_n),
        utc_match_median_ms=float(med_ms) if med_ms is not None else None,
        lr_to_hr_flag_match_rate=None,  # computed on demand if needed
        hr_to_lr_flag_match_rate=None,
        coverage_nonnull_ratio=coverage,
        source_files={"hr": hr_csv, "lr": lr_csv, "out": output_csv},
    )
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "settings": asdict(merge_settings),
                "report": asdict(report),
                "columns": {
                    "hr_numeric": hr_num,
                    "hr_flags": hr_flag,
                    "hr_other": hr_other,
                    "lr_numeric": lr_num,
                    "lr_flags": lr_flag,
                    "lr_other": lr_other,
                },
            },
            f,
            indent=2,
        )
    return report


if __name__ == "__main__":
    settings = MergeSettings(
        output_rate=OUTPUT_RATE,
        custom_dt_s=CUSTOM_DT_S,
        bounds=BOUNDS,
        align_by=ALIGN_BY,
        time_tolerance_s=TIME_TOLERANCE_S,
        sync_tol_counts=SYNC_TOL_COUNTS,
        numeric_up_method=NUMERIC_UP_METHOD,
        numeric_down_method=NUMERIC_DOWN_METHOD,
        flag_method=FLAG_METHOD,
        window_half_width_s=WINDOW_HALF_WIDTH_S,
        hr_prefix=HR_PREFIX,
        lr_prefix=LR_PREFIX,
    )
    rep = merge_br_hr_lr(
        hr_csv=HR_CSV,
        lr_csv=LR_CSV,
        output_csv=OUTPUT_CSV,
        metadata_json=OUTPUT_META_JSON,
        merge_settings=settings,
    )
    # Minimal console summary
    print(
        f"merged rows={rep.output_rows} span={rep.span_seconds:.3f}s "
        f"delta_sync={rep.delta_sync_est} samples={rep.delta_sync_samples}"
    )

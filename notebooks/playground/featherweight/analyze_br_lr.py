# analyze_br_lr.py
#
# Quick analysis for Blue Raven Low-Rate (LR, ~50 Hz) log.
# - Loads 2025-08-21_primary_blueraven_lr.csv
# - Parses UTC timestamps
# - Computes sampling stats (rate, jitter, gaps/dupes)
# - Summarizes key channels (temps, pressure, altitudes, voltages, velocities, angles)
# - Detects event flag rising edges (0→1) with times (e.g., Liftoff, Apogee)
# - Decodes *_Hex / FER hex-like columns to integers
# - Estimates motion metrics: apogee (per available altitude sources), max vertical speed,
#   max resultant speed (if components present), time-to-apogee from Liftoff
# - Exports JSON report (+ events CSV), and plots (PNG) to OUTPUT_DIR
#
# Usage:
#   - Set CONFIG and run:  python analyze_br_lr.py
#
# Dependencies: pandas, numpy, matplotlib

from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

# ============ CONFIG ============
INPUT_CSV = "2025-08-21_primary_blueraven_lr.csv"
OUTPUT_DIR = "fw_br_lr_analysis"  # directory for JSON, CSV, PNGs (must be writable)
OUTPUT_META_JSON = "2025-08-21_primary_blueraven_lr.meta.json"
OUTPUT_EVENTS_CSV = "2025-08-21_primary_blueraven_lr.events.csv"
OUTPUT_EVENTS_CSV_NO_THRESH = "2025-08-21_primary_blueraven_lr.events_no_thresh.csv"
WRITE_EVENTS_CSV = True

EXPECTED_DT_S = 0.020  # nominal 50 Hz
JITTER_WARN_FACTOR = 3.0  # warn if std(dt) > factor * 1e-6 (practically >0)
MAX_GAP_S = 0.100  # mark gaps > this (5+ missing samples at 50 Hz)
# ================================


@dataclass
class SeriesSummary:
    count: int
    nonnull: int
    coverage: float
    min: Optional[float]
    max: Optional[float]
    mean: Optional[float]
    std: Optional[float]


@dataclass
class LRReport:
    samples: int
    first_utc: str
    last_utc: str
    duration_s: float
    dt_mean_s: Optional[float]
    dt_std_s: Optional[float]
    dt_min_s: Optional[float]
    dt_max_s: Optional[float]
    nominal_rate_hz: float
    estimated_rate_hz: Optional[float]
    gaps_count: int
    gaps_examples: List[Dict[str, str]]
    duplicate_timestamps: int
    key_channels: Dict[str, SeriesSummary]
    extremes: Dict[str, Dict[str, float]]
    motion_metrics: Dict[str, Any]
    event_flags_rising_edges: Dict[str, int]
    hex_fields_decoded: List[str]
    plots_written: List[str]
    file: str
    output_dir: str


def _parse_utc_from_cols(df: pd.DataFrame) -> pd.Series:
    required = {"Year", "Month", "Day", "Time"}
    if not required.issubset(df.columns):
        missing = ", ".join(sorted(required - set(df.columns)))
        raise ValueError(f"Missing required columns: {missing}")
    y = df["Year"].astype(int).astype(str)
    m = df["Month"].astype(int).astype(str).str.zfill(2)
    d = df["Day"].astype(int).astype(str).str.zfill(2)
    ts = y + "-" + m + "-" + d + " " + df["Time"].astype(str)
    return pd.to_datetime(ts, utc=True, errors="coerce")


def _summarize_numeric(s: pd.Series) -> SeriesSummary:
    nonnull = int(s.notna().sum())
    coverage = float(nonnull) / int(len(s)) if len(s) else 0.0
    if nonnull == 0:
        return SeriesSummary(int(len(s)), nonnull, coverage, None, None, None, None)
    return SeriesSummary(
        int(len(s)),
        nonnull,
        coverage,
        float(s.min()),
        float(s.max()),
        float(s.mean()),
        float(s.std(ddof=0)),
    )


def _is_flag_like(s: pd.Series) -> bool:
    if s.dtype == bool:
        return True
    if not pd.api.types.is_numeric_dtype(s):
        return False
    vals = pd.Series(pd.unique(s.dropna()))
    if len(vals) == 0:
        return False
    try:
        ivals = vals.astype(int)
    except (ValueError, TypeError):
        return False
    return len(ivals) <= 4 and set(ivals).issubset({0, 1, 2, 3})


def _detect_event_edges(df: pd.DataFrame, flag_cols: List[str]) -> pd.DataFrame:
    """
    Return DataFrame of 0→1 transitions for each flag with UTC, Flight_Time_(s), Sync.
    """
    out_rows: List[Dict[str, Any]] = []

    # Precompute optional numeric series once
    ft_series = pd.to_numeric(
        df.get("Flight_Time_(s)", pd.Series(index=df.index, dtype="float64")),
        errors="coerce",
    )
    sync_series = pd.to_numeric(
        df.get("Sync", pd.Series(index=df.index, dtype="float64")), errors="coerce"
    )

    for col in flag_cols:
        # normalize to 0/1 ints
        vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
        vals = (vals != 0).astype(int)

        # rising edges (0 -> 1)
        edges = vals.diff().eq(1)

        # Robust list of integer positions
        idxs: List[int] = edges[edges].index.to_list()
        # If index is not positional (unlikely since we reset_index), coerce to positions
        if not isinstance(df.index, pd.RangeIndex):
            idxs = [
                int(df.index.get_loc(ix)) if ix in df.index else int(ix)  # type: ignore
                for ix in idxs
            ]

        for idx in idxs:
            utc_i = df["_utc"].iloc[idx]

            ft_val = ft_series.iloc[idx]
            ft_out = float(ft_val) if pd.notna(ft_val) else np.nan

            sync_val = sync_series.iloc[idx]
            sync_out = int(sync_val) if pd.notna(sync_val) else np.nan

            out_rows.append(
                {
                    "Flag": col,
                    "UTC": utc_i.isoformat(),
                    "t_rel_s": float((utc_i - df["_utc"].iloc[0]).total_seconds()),
                    "Flight_Time_(s)": ft_out,
                    "Sync": sync_out,
                    "Row": int(idx),
                }
            )

    return pd.DataFrame(out_rows)


def _decode_hex_columns(df: pd.DataFrame) -> List[str]:
    """
    Detect hex-like columns robustly (handles headers with stray spaces, e.g. 'Apo_FER_H  ex').
    For any column whose name, after removing spaces, endswith 'Hex' (case-insensitive) or contains 'FER',
    create a new '<col>_dec' with integer decoding (base 16), NaN on errors.
    """
    decoded: List[str] = []
    for col in df.columns:
        key = col.replace(" ", "")
        if key.lower().endswith("hex") or ("FER" in key or "fer" in key):
            new_col = f"{col}_dec"
            df[new_col] = pd.to_numeric(df[col], errors="coerce")
            mask = (
                df[col]
                .astype(str)
                .str.contains(r"[A-Fa-f]|[^0-9\-\.]", regex=True, na=False)
            )
            to_hex = df.loc[mask, col].astype(str).str.replace(r"\s+", "", regex=True)

            def _h(x: str) -> float:
                try:
                    return float(int(x, 16))
                except (ValueError, TypeError):
                    return np.nan

            df.loc[to_hex.index, new_col] = to_hex.map(_h).astype("float64")
            decoded.append(new_col)
    return decoded


def _ensure_outdir(dirpath: str) -> str:
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    return os.path.abspath(dirpath)


def _secs_since_start(ts: pd.Series) -> np.ndarray:
    t0 = ts.iloc[0]
    return (ts - t0).dt.total_seconds().to_numpy()


def _save_plot(
    x: np.ndarray,
    series_list: List[Tuple[str, pd.Series]],
    title: str,
    ylabel: str,
    filepath: str,
    vlines: Optional[List[Tuple[float, str]]] = None,
) -> Optional[str]:
    fig, ax = plt.subplots(figsize=(10, 4))
    try:
        for label, s in series_list:
            y = pd.to_numeric(s, errors="coerce").to_numpy()
            ax.plot(x, y, label=label)
        if vlines:
            for xv, lab in vlines:
                ax.axvline(x=xv, linestyle="--")
                ytop = ax.get_ylim()[1]
                ax.text(xv, ytop, lab, rotation=90, va="top", ha="right")
        ax.set_title(title)
        ax.set_xlabel("Seconds since start")
        ax.set_ylabel(ylabel)
        if len(series_list) > 1:
            ax.legend(loc="best")
        fig.tight_layout()
        fig.savefig(filepath, dpi=150)
        return filepath
    except (ValueError, TypeError, RuntimeError, OSError):
        return None
    finally:
        plt.close(fig)


def _first_edge_time(events_df: pd.DataFrame, name_like: str) -> Optional[pd.Timestamp]:
    if events_df.empty:
        return None
    mask = events_df["Flag"].str.contains(name_like, case=False, regex=False)
    sel = events_df.loc[mask]
    if sel.empty:
        return None
    return pd.to_datetime(sel.iloc[0]["UTC"], utc=True)


def _pick_apogee(
    df: pd.DataFrame,
) -> Tuple[str, Optional[int], Optional[float], Optional[str]]:
    """
    Return (column_used, idx, value, utc_iso). Prioritize Inertial_Altitude, then Baro_Altitude_AGL_(feet),
    then Baro_Altitude_ASL_(feet).
    """
    candidates = [
        "Inertial_Altitude",
        "Baro_Altitude_AGL_(feet)",
        "Baro_Altitude_ASL_(feet)",
    ]
    for col in candidates:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            if s.notna().any():
                i = int(s.idxmax())
                return col, i, float(s.iloc[i]), df["_utc"].iloc[i].isoformat()
    return "N/A", None, None, None


def main():
    # I/O
    out_dir = _ensure_outdir(OUTPUT_DIR)
    meta_path = os.path.join(out_dir, OUTPUT_META_JSON)
    events_path = os.path.join(out_dir, OUTPUT_EVENTS_CSV)
    events_path_no_thresh = os.path.join(out_dir, OUTPUT_EVENTS_CSV_NO_THRESH)

    pd.set_option("display.width", 180)
    pd.set_option("display.max_columns", 200)

    # Load
    df = pd.read_csv(INPUT_CSV)
    df["_utc"] = _parse_utc_from_cols(df)
    df = df.sort_values("_utc").reset_index(drop=True)

    # Timing stats
    dt = df["_utc"].diff().dt.total_seconds()
    samples = int(len(df))
    first_utc = df["_utc"].iloc[0]
    last_utc = df["_utc"].iloc[-1]
    duration_s = float((last_utc - first_utc).total_seconds())
    dt_mean = float(dt.mean()) if dt.notna().any() else None
    dt_std = float(dt.std(ddof=0)) if dt.notna().any() else None
    dt_min = float(dt.min()) if dt.notna().any() else None
    dt_max = float(dt.max()) if dt.notna().any() else None
    est_rate = (samples - 1) / duration_s if duration_s > 0 and samples > 1 else None

    # Gaps & duplicates
    gaps_mask = dt > MAX_GAP_S
    gaps = df.loc[gaps_mask, ["_utc"]].copy()
    gap_examples: List[Dict[str, Any]] = []
    for i in gaps.index[:5]:
        gap_examples.append(
            {
                "utc_before": df["_utc"].iloc[i - 1].isoformat() if i > 0 else "",
                "utc_after": df["_utc"].iloc[i].isoformat(),
                "gap_s": float(dt.iloc[i]),
            }
        )
    dupes = int(df["_utc"].duplicated(keep=False).sum())

    # Key numeric channels to summarize (only if present)
    key_numeric = [
        "Temperature_(F)",
        "Baro_Press_(atm)",
        "Baro_Altitude_ASL_(feet)",
        "Baro_Altitude_AGL_(feet)",
        "Batt_Volts",
        "Apo_Volts",
        "Main_Volts",
        "3rd_Volts",
        "4th_Volts",
        "Velocity_Up",
        "Velocity_DR",
        "Velocity_CR",
        "Inertial_Altitude",
        "Inertial_DR_Position",
        "Inertial_CR_position",
        "Tilt_Angle_(deg)",
        "Future_Angle_(deg)",
        "Roll_Angle_(deg)",
    ]
    summaries: Dict[str, SeriesSummary] = {}
    for c in key_numeric:
        if c in df.columns:
            summaries[c] = _summarize_numeric(pd.to_numeric(df[c], errors="coerce"))

    # Extremes of interest
    extremes: Dict[str, Dict[str, float]] = {}

    def _mk_ext(name: str, series_name: str):
        if series_name not in df.columns:
            return
        s = pd.to_numeric(df[series_name], errors="coerce")
        if s.dropna().empty:
            return
        i_max = int(s.idxmax())
        i_min = int(s.idxmin())
        extremes[name] = {
            "max": float(s.iloc[i_max]),
            "max_utc": df["_utc"].iloc[i_max].isoformat(),
            "min": float(s.iloc[i_min]),
            "min_utc": df["_utc"].iloc[i_min].isoformat(),
        }

    _mk_ext("baro_agl_ft", "Baro_Altitude_AGL_(feet)")
    _mk_ext("baro_asl_ft", "Baro_Altitude_ASL_(feet)")
    _mk_ext("inertial_alt", "Inertial_Altitude")
    _mk_ext("tilt_deg", "Tilt_Angle_(deg)")
    _mk_ext("v_up", "Velocity_Up")

    # Decode hex-like fields
    decoded_cols = _decode_hex_columns(df)

    # Detect event flags (boolean-ish columns)
    flag_cols: List[str] = []
    for col in df.columns:
        if col in {"Year", "Month", "Day", "Time", "_utc"}:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if _is_flag_like(s):
            flag_cols.append(col)

    events_df = _detect_event_edges(df, flag_cols)
    if WRITE_EVENTS_CSV and not events_df.empty:
        sorted_events = events_df.sort_values("UTC")
        sorted_events.to_csv(events_path, index=False)

        # write filtered CSV excluding GT_/LT_ prefixed flags
        no_thresh = sorted_events[
            ~sorted_events["Flag"].astype(str).str.match(r"^\s*(?:GT_|LT_)")
        ]
        if not no_thresh.empty:
            no_thresh.to_csv(events_path_no_thresh, index=False)

    # Motion metrics
    apogee_col, ap_idx, ap_value, ap_utc = _pick_apogee(df)
    liftoff_t = _first_edge_time(events_df, "Liftoff") if not events_df.empty else None
    time_to_apogee_s: Optional[float] = None
    if ap_idx is not None and liftoff_t is not None and ap_utc is not None:
        time_to_apogee_s = float(
            (pd.to_datetime(ap_utc, utc=True) - liftoff_t).total_seconds()
        )

    # Vertical / resultant speed
    v_up = (
        pd.to_numeric(df["Velocity_Up"], errors="coerce")
        if "Velocity_Up" in df.columns
        else None
    )
    v_dr = (
        pd.to_numeric(df["Velocity_DR"], errors="coerce")
        if "Velocity_DR" in df.columns
        else None
    )
    v_cr = (
        pd.to_numeric(df["Velocity_CR"], errors="coerce")
        if "Velocity_CR" in df.columns
        else None
    )

    max_vup = float(v_up.max()) if v_up is not None and v_up.notna().any() else None
    min_vup = (
        float(v_up.min()) if v_up is not None and v_up.notna().any() else None
    )  # most negative (descent)

    speed_mag: Optional[pd.Series] = None
    max_speed_mag: Optional[float] = None
    max_speed_utc: Optional[str] = None
    if (v_up is not None) or (v_dr is not None) or (v_cr is not None):
        # treat missing components as 0 for magnitude, keep as Series for type safety
        vu = v_up.fillna(0.0) if v_up is not None else pd.Series(0.0, index=df.index)
        vd = v_dr.fillna(0.0) if v_dr is not None else pd.Series(0.0, index=df.index)
        vc = v_cr.fillna(0.0) if v_cr is not None else pd.Series(0.0, index=df.index)
        speed_mag = (vu.pow(2) + vd.pow(2) + vc.pow(2)).pow(0.5)
        if speed_mag.notna().any():
            j = int(speed_mag.idxmax())
            max_speed_mag = float(speed_mag.iloc[j])
            max_speed_utc = df["_utc"].iloc[j].isoformat()

    motion_metrics: Dict[str, Any] = {
        "apogee": {
            "column_used": apogee_col,
            "value_native": ap_value,
            "utc": ap_utc,
            "time_to_apogee_from_liftoff_s": time_to_apogee_s,
        },
        "vertical_speed": {
            "max_up_native": max_vup,
            "max_down_native": min_vup,
            "columns_used": [c for c in ["Velocity_Up"] if c in df.columns],
        },
        "resultant_speed": {
            "max_native": max_speed_mag,
            "utc": max_speed_utc,
            "columns_used": [
                c
                for c in ["Velocity_Up", "Velocity_DR", "Velocity_CR"]
                if c in df.columns
            ],
        },
        "liftoff_utc": liftoff_t.isoformat() if liftoff_t is not None else None,
    }

    # ===== Plots =====
    x = _secs_since_start(df["_utc"])
    vlines: List[Tuple[float, str]] = []
    if liftoff_t is not None:
        vlines.append(((liftoff_t - df["_utc"].iloc[0]).total_seconds(), "Liftoff"))
    if ap_idx is not None:
        vlines.append((x[ap_idx], "Apogee"))

    plots_written: List[str] = []

    # Altitudes
    alt_series: List[Tuple[str, pd.Series]] = []
    for col in [
        "Inertial_Altitude",
        "Baro_Altitude_AGL_(feet)",
        "Baro_Altitude_ASL_(feet)",
    ]:
        if col in df.columns:
            alt_series.append((col, df[col]))
    if alt_series:
        fp = os.path.join(out_dir, "lr_altitudes.png")
        p = _save_plot(
            x,
            alt_series,
            "Altitudes vs Time",
            "Altitude (native units)",
            fp,
            vlines=vlines,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Velocities
    vel_series: List[Tuple[str, pd.Series]] = []
    for col in ["Velocity_Up", "Velocity_DR", "Velocity_CR"]:
        if col in df.columns:
            vel_series.append((col, df[col]))
    if vel_series:
        fp = os.path.join(out_dir, "lr_velocities.png")
        p = _save_plot(
            x,
            vel_series,
            "Velocities vs Time",
            "Velocity (native units)",
            fp,
            vlines=vlines,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Speed magnitude (if computed)
    if speed_mag is not None:
        fp = os.path.join(out_dir, "lr_speed_magnitude.png")
        p = _save_plot(
            x,
            [("speed_mag", speed_mag)],
            "Resultant Speed Magnitude",
            "Speed (native units)",
            fp,
            vlines=vlines,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Angles
    ang_series: List[Tuple[str, pd.Series]] = []
    for col in ["Tilt_Angle_(deg)", "Future_Angle_(deg)", "Roll_Angle_(deg)"]:
        if col in df.columns:
            ang_series.append((col, df[col]))
    if ang_series:
        fp = os.path.join(out_dir, "lr_angles.png")
        p = _save_plot(x, ang_series, "Angles vs Time", "Degrees", fp, vlines=vlines)
        if p:
            plots_written.append(os.path.basename(p))

    # Voltages
    v_series: List[Tuple[str, pd.Series]] = []
    for col in ["Batt_Volts", "Apo_Volts", "Main_Volts", "3rd_Volts", "4th_Volts"]:
        if col in df.columns:
            v_series.append((col, df[col]))
    if v_series:
        fp = os.path.join(out_dir, "lr_voltages.png")
        p = _save_plot(
            x,
            v_series,
            "Voltages vs Time",
            "Volts",
            fp,
            vlines=vlines if vlines else None,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Pressure & Temperature (separate plots)
    if "Baro_Press_(atm)" in df.columns:
        fp = os.path.join(out_dir, "lr_baro_press.png")
        p = _save_plot(
            x,
            [("Baro_Press_(atm)", df["Baro_Press_(atm)"])],
            "Barometric Pressure",
            "atm",
            fp,
        )
        if p:
            plots_written.append(os.path.basename(p))
    if "Temperature_(F)" in df.columns:
        fp = os.path.join(out_dir, "lr_temperature.png")
        p = _save_plot(
            x, [("Temperature_(F)", df["Temperature_(F)"])], "Temperature", "F", fp
        )
        if p:
            plots_written.append(os.path.basename(p))

    # ===== Report =====
    report = LRReport(
        samples=samples,
        first_utc=first_utc.isoformat(),
        last_utc=last_utc.isoformat(),
        duration_s=duration_s,
        dt_mean_s=dt_mean,
        dt_std_s=dt_std,
        dt_min_s=dt_min,
        dt_max_s=dt_max,
        nominal_rate_hz=1.0 / EXPECTED_DT_S if EXPECTED_DT_S else 0.0,
        estimated_rate_hz=float(est_rate) if est_rate else None,
        gaps_count=int(gaps_mask.sum()),
        gaps_examples=gap_examples,
        duplicate_timestamps=dupes,
        key_channels=summaries,  # keep dataclasses; asdict(report) will serialize
        extremes=extremes,
        motion_metrics=motion_metrics,
        event_flags_rising_edges={
            f: int(
                (
                    pd.to_numeric(df[f], errors="coerce").fillna(0).astype(int).diff()
                    == 1
                ).sum()
            )
            for f in flag_cols
        },
        hex_fields_decoded=decoded_cols,
        plots_written=plots_written,
        file=os.path.abspath(INPUT_CSV),
        output_dir=out_dir,
    )

    # Console summary
    print(f"File: {report.file}")
    print(f"Output → {out_dir}")
    print(
        f"samples={report.samples}  span={report.duration_s:.3f}s  "
        f"dt(mean/σ/min/max)={report.dt_mean_s:.6f}/{report.dt_std_s:.6f}/{report.dt_min_s:.6f}/{report.dt_max_s:.6f}  "
        f"est_rate≈{report.estimated_rate_hz:.2f} Hz"
    )
    print(
        f"gaps>{MAX_GAP_S:.3f}s: {report.gaps_count}   dup_timestamps={report.duplicate_timestamps}"
    )

    apo = report.motion_metrics["apogee"]  # type: ignore[index]
    if apo["value_native"] is not None:  # type: ignore[index]
        print(
            f"Apogee ({apo['column_used']}): {apo['value_native']} at {apo['utc']}"
            + (
                f"  (Δt from liftoff: {apo['time_to_apogee_from_liftoff_s']:.3f}s)"
                if apo["time_to_apogee_from_liftoff_s"] is not None
                else ""
            )
        )

    vs = report.motion_metrics["vertical_speed"]  # type: ignore[index]
    if vs["max_up_native"] is not None:  # type: ignore[index]
        print(
            f"Vertical speed max up: {vs['max_up_native']}  | max down: {vs['max_down_native']}"
        )

    rs = report.motion_metrics["resultant_speed"]  # type: ignore[index]
    if rs["max_native"] is not None:  # type: ignore[index]
        print(f"Resultant speed max: {rs['max_native']} at {rs['utc']}")

    # Write JSON
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "report": asdict(report),
                "flag_columns_detected": flag_cols,
                "decoded_hex_columns": decoded_cols,
            },
            f,
            indent=2,
        )

    if WRITE_EVENTS_CSV and events_df.empty:
        print("[info] No 0→1 edges detected in flag columns; verify flags in source.")
    if report.dt_std_s and report.dt_std_s > JITTER_WARN_FACTOR * 1e-6:
        print(f"[warn] Jitter noticeable: σ(dt)={report.dt_std_s:.6f}s")
    if report.gaps_count > 0:
        print(
            f"[warn] Found {report.gaps_count} gaps > {MAX_GAP_S:.3f}s (see JSON for examples)"
        )
    if plots_written:
        print("Plots written:")
        for p in plots_written:
            print(f"  - {p}")


if __name__ == "__main__":
    main()

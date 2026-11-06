# analyze_tm.py
#
# Quick analysis for Altus Metrum TeleMega CSV logs.
# - Loads 2025-08-21_redundant_telemega.csv
# - Parses UTC-like timestamps from year,month,day,hour,minute,second
# - Computes sampling stats (rate, jitter, gaps/dupes)
# - Summarizes key channels (altitude/height/speed/accel/tilt/temps/voltages/GPS)
# - Detects state transitions (state_name) and 0→1 event edges on boolean-ish fields
# - Estimates motion metrics: apogee (height/altitude/gps_alt), max speed, time-to-apogee from liftoff
# - Exports JSON report (+ events CSV), and plots (PNG) to OUTPUT_DIR
#
# Usage:
#   - Set CONFIG and run:  python analyze_tm.py
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
INPUT_CSV = "2025-08-21_redundant_telemega.csv"
OUTPUT_DIR = "fw_tm_analysis"  # directory for JSON, CSV, PNGs (must be writable)
OUTPUT_META_JSON = "2025-08-21_telemega.meta.json"
OUTPUT_EVENTS_CSV = "2025-08-21_telemega.events.csv"
WRITE_EVENTS_CSV = True

EXPECTED_DT_S = 0.100  # TeleMega telemetry often ~10 Hz (adjust if you know better)
JITTER_WARN_FACTOR = 3.0
MAX_GAP_S = 0.500  # flag gaps >0.5s
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
class TMReport:
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
    gaps_examples: List[Dict[str, Any]]
    duplicate_timestamps: int
    key_channels: Dict[str, SeriesSummary]
    extremes: Dict[str, Dict[str, Any]]
    motion_metrics: Dict[str, Any]
    state_transitions: List[Dict[str, Any]]
    flag_edges_count: Dict[str, int]
    plots_written: List[str]
    file: str
    output_dir: str


# ---------- helpers ----------


def _ensure_outdir(dirpath: str) -> str:
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    return os.path.abspath(dirpath)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # strip spaces from headers
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    # handle duplicate "altitude" (baro vs GPS). Pandas appends .1, .2 etc — rename a common one.
    cols = df.columns.tolist()
    if cols.count("altitude") >= 2:
        # rename later duplicate(s)
        seen = 0
        new_cols = []
        for c in cols:
            if c == "altitude":
                seen += 1
                new_cols.append("altitude" if seen == 1 else f"altitude_{seen}")
            else:
                new_cols.append(c)
        df.columns = new_cols
    # If we have a GPS altitude (after lon), try renaming the second "altitude" to gps_altitude
    # Heuristic: if we have 'latitude' and 'longitude' and also 'altitude_2', rename that to 'gps_altitude'
    for name in ("altitude_2", "altitude_1"):
        if (
            name in df.columns
            and "latitude" in df.columns
            and "longitude" in df.columns
        ):
            df = df.rename(columns={name: "gps_altitude"})
            break
    return df


def _parse_utc(df: pd.DataFrame) -> pd.Series:
    # Build naive UTC from year,month,day,hour,minute,second
    required = {"year", "month", "day", "hour", "minute", "second"}
    # be tolerant to capitalization
    lower_map = {c.lower(): c for c in df.columns}
    if not required.issubset(lower_map.keys()):
        # try Altus Metrum CSV variants (capitalized)
        req_caps = {"Year", "Month", "Day", "Hour", "Minute", "Second"}
        if not req_caps.issubset(df.columns):
            raise ValueError("Missing time columns (year..second)")
        y = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
        m = pd.to_numeric(df["Month"], errors="coerce").astype("Int64")
        d = pd.to_numeric(df["Day"], errors="coerce").astype("Int64")
        hh = pd.to_numeric(df["Hour"], errors="coerce").astype("Int64")
        mm = pd.to_numeric(df["Minute"], errors="coerce").astype("Int64")
        ss = pd.to_numeric(df["Second"], errors="coerce").astype("Int64")
    else:
        y = pd.to_numeric(df[lower_map["year"]], errors="coerce").astype("Int64")
        m = pd.to_numeric(df[lower_map["month"]], errors="coerce").astype("Int64")
        d = pd.to_numeric(df[lower_map["day"]], errors="coerce").astype("Int64")
        hh = pd.to_numeric(df[lower_map["hour"]], errors="coerce").astype("Int64")
        mm = pd.to_numeric(df[lower_map["minute"]], errors="coerce").astype("Int64")
        ss = pd.to_numeric(df[lower_map["second"]], errors="coerce").astype("Int64")
    ts = (
        y.astype(str).str.zfill(4)
        + "-"
        + m.astype(str).str.zfill(2)
        + "-"
        + d.astype(str).str.zfill(2)
        + " "
        + hh.astype(str).str.zfill(2)
        + ":"
        + mm.astype(str).str.zfill(2)
        + ":"
        + ss.astype(str).str.zfill(2)
    )
    return pd.to_datetime(ts, utc=True, errors="coerce")


def _summarize_numeric(s: pd.Series) -> SeriesSummary:
    s = pd.to_numeric(s, errors="coerce")
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
    vals = pd.Series(pd.unique(pd.to_numeric(s, errors="coerce").dropna()))
    if len(vals) == 0:
        return False
    try:
        ivals = vals.astype(int)
    except (ValueError, TypeError):
        return False
    return len(ivals) <= 4 and set(ivals).issubset({0, 1, 2, 3})


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


def _detect_state_transitions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if "state_name" not in df.columns and "state" not in df.columns:
        return []
    state_str = None
    if "state_name" in df.columns:
        state_str = df["state_name"].astype(str).fillna("")
    else:
        state_str = df["state"].astype(str).fillna("")
    changes = state_str != state_str.shift(1)
    idxs = changes[changes].index.to_list()
    out: List[Dict[str, Any]] = []
    for idx in idxs:
        utc_i = df["_utc"].iloc[idx]
        out.append(
            {
                "type": "state_change",
                "state": state_str.iloc[idx],
                "UTC": utc_i.isoformat(),
                "Row": int(idx),
                "t_rel_s": float((utc_i - df["_utc"].iloc[0]).total_seconds()),
            }
        )
    return out


def _detect_flag_edges(
    df: pd.DataFrame, candidate_cols: List[str]
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for col in candidate_cols:
        vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
        vals = (vals != 0).astype(int)
        edges = vals.diff().eq(1)
        idxs = edges[edges].index.to_list()
        for idx in idxs:
            utc_i = df["_utc"].iloc[idx]
            rows.append(
                {
                    "type": "flag_edge",
                    "flag": col,
                    "UTC": utc_i.isoformat(),
                    "Row": int(idx),
                    "t_rel_s": float((utc_i - df["_utc"].iloc[0]).total_seconds()),
                }
            )
    return rows


def _pick_apogee(
    df: pd.DataFrame,
) -> Tuple[str, Optional[int], Optional[float], Optional[str]]:
    for col in ["height", "altitude", "gps_altitude"]:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            if s.notna().any():
                i = int(s.idxmax())
                return col, i, float(s.iloc[i]), df["_utc"].iloc[i].isoformat()
    return "N/A", None, None, None


def _liftoff_time(
    df: pd.DataFrame, events: List[Dict[str, Any]]
) -> Optional[pd.Timestamp]:
    # prefer state transition into 'boost' (case-insensitive)
    for e in events:
        if e.get("type") == "state_change":
            st = str(e.get("state", "")).lower()
            if "boost" in st:
                return pd.to_datetime(e["UTC"], utc=True)

    # fallback: speed threshold
    if "speed" in df.columns:
        s = pd.to_numeric(df["speed"], errors="coerce")
        if s.notna().any():
            mask = (s > 15.0).to_numpy()
            pos = np.flatnonzero(mask)
            if pos.size > 0:
                return df["_utc"].iloc[int(pos[0])]

    return None


# ---------- main ----------


def main():
    out_dir = _ensure_outdir(OUTPUT_DIR)
    meta_path = os.path.join(out_dir, OUTPUT_META_JSON)
    events_path = os.path.join(out_dir, OUTPUT_EVENTS_CSV)

    pd.set_option("display.width", 180)
    pd.set_option("display.max_columns", 300)

    # Load (be tolerant to spaces after commas)
    df = pd.read_csv(INPUT_CSV, skipinitialspace=True)
    df = _normalize_columns(df)

    # Parse UTC-like time
    df["_utc"] = _parse_utc(df)
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

    # Gaps & dupes
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

    # Summaries of key channels
    key_numeric = [
        "acceleration",
        "pressure",
        "altitude",
        "height",
        "speed",
        "temperature",
        "drogue_voltage",
        "main_voltage",
        "battery_voltage",
        "pyro",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_roll",
        "gyro_pitch",
        "gyro_yaw",
        "mag_x",
        "mag_y",
        "mag_z",
        "tilt",
        "nsat",
        "latitude",
        "longitude",
        "gps_altitude",
        "pdop",
        "hdop",
        "vdop",
        "pad_dist",
        "pad_range",
        "pad_az",
        "pad_el",
    ]
    summaries: Dict[str, SeriesSummary] = {}
    for c in key_numeric:
        if c in df.columns:
            summaries[c] = _summarize_numeric(df[c])

    # Extremes
    extremes: Dict[str, Dict[str, Any]] = {}

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

    _mk_ext("height", "height")
    _mk_ext("altitude", "altitude")
    _mk_ext("gps_altitude", "gps_altitude")
    _mk_ext("speed", "speed")
    _mk_ext("acceleration", "acceleration")
    _mk_ext("tilt", "tilt")
    _mk_ext("battery_voltage", "battery_voltage")

    # Events: state transitions + 0→1 edges on selected flags
    state_events = _detect_state_transitions(df)

    candidate_flags: List[str] = []
    for col in [
        "connected",
        "locked",
        "igniter_a",
        "igniter_b",
        "igniter_c",
        "igniter_d",
    ]:
        if col in df.columns:
            candidate_flags.append(col)
    # also auto-detect any other boolean-ish
    for col in df.columns:
        if col in {"_utc"}:
            continue
        if col in candidate_flags:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if _is_flag_like(s):
            candidate_flags.append(col)

    flag_events = _detect_flag_edges(df, candidate_flags)
    events_all = sorted(state_events + flag_events, key=lambda r: (r["UTC"], r["type"]))

    # Motion metrics
    apogee_col, ap_idx, ap_value, ap_utc = _pick_apogee(df)
    liftoff_t = _liftoff_time(df, state_events)
    time_to_apogee_s: Optional[float] = None
    if ap_idx is not None and liftoff_t is not None and ap_utc is not None:
        time_to_apogee_s = float(
            (pd.to_datetime(ap_utc, utc=True) - liftoff_t).total_seconds()
        )

    max_speed = None
    max_speed_utc = None
    if "speed" in df.columns:
        s = pd.to_numeric(df["speed"], errors="coerce")
        if s.notna().any():
            j = int(s.idxmax())
            max_speed = float(s.iloc[j])
            max_speed_utc = df["_utc"].iloc[j].isoformat()

    motion_metrics: Dict[str, Any] = {
        "apogee": {
            "column_used": apogee_col,
            "value_native": ap_value,
            "utc": ap_utc,
            "time_to_apogee_from_liftoff_s": time_to_apogee_s,
        },
        "speed": {
            "max_native": max_speed,
            "utc": max_speed_utc,
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
    for col in ["height", "altitude", "gps_altitude"]:
        if col in df.columns:
            alt_series.append((col, df[col]))
    if alt_series:
        fp = os.path.join(out_dir, "tm_altitudes.png")
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

    # Speed
    if "speed" in df.columns:
        fp = os.path.join(out_dir, "tm_speed.png")
        p = _save_plot(
            x,
            [("speed", df["speed"])],
            "Speed vs Time",
            "Speed (native units)",
            fp,
            vlines=vlines,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Acceleration
    if "acceleration" in df.columns:
        fp = os.path.join(out_dir, "tm_acceleration.png")
        p = _save_plot(
            x,
            [("acceleration", df["acceleration"])],
            "Acceleration vs Time",
            "Accel (native)",
            fp,
            vlines=vlines,
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Tilt
    if "tilt" in df.columns:
        fp = os.path.join(out_dir, "tm_tilt.png")
        p = _save_plot(
            x, [("tilt", df["tilt"])], "Tilt vs Time", "Degrees", fp, vlines=vlines
        )
        if p:
            plots_written.append(os.path.basename(p))

    # Voltages
    v_series: List[Tuple[str, pd.Series]] = []
    for col in ["battery_voltage", "drogue_voltage", "main_voltage", "pyro"]:
        if col in df.columns:
            v_series.append((col, df[col]))
    if v_series:
        fp = os.path.join(out_dir, "tm_voltages.png")
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

    # ===== Report =====
    report = TMReport(
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
        key_channels=summaries,
        extremes=extremes,
        motion_metrics=motion_metrics,
        state_transitions=[e for e in events_all if e["type"] == "state_change"],
        flag_edges_count={
            col: int(
                (
                    pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).diff()
                    == 1
                ).sum()
            )
            for col in candidate_flags
        },
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
        f"est_rate≈{(report.estimated_rate_hz or 0):.2f} Hz"
    )
    if motion_metrics["apogee"]["value_native"] is not None:
        a = motion_metrics["apogee"]
        print(
            f"Apogee ({a['column_used']}): {a['value_native']} at {a['utc']}"
            + (
                f"  (Δt from liftoff: {a['time_to_apogee_from_liftoff_s']:.3f}s)"
                if a["time_to_apogee_from_liftoff_s"] is not None
                else ""
            )
        )
    if motion_metrics["speed"]["max_native"] is not None:
        s = motion_metrics["speed"]
        print(f"Max speed: {s['max_native']} at {s['utc']}")

    # Write events CSV
    if WRITE_EVENTS_CSV and len(events_all) > 0:
        pd.DataFrame(events_all).to_csv(events_path, index=False)

    # Write JSON
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "report": asdict(report),
                "events_written": WRITE_EVENTS_CSV,
                "events_file": os.path.basename(events_path),
            },
            f,
            indent=2,
        )

    # Warnings
    if report.dt_std_s and report.dt_std_s > JITTER_WARN_FACTOR * 1e-6:
        print(f"[warn] Jitter noticeable: σ(dt)={report.dt_std_s:.6f}s")
    if report.gaps_count > 0:
        print(
            f"[warn] Found {report.gaps_count} gaps > {MAX_GAP_S:.3f}s (see JSON for examples)"
        )
    if report.plots_written:
        print("Plots written:")
        for p in report.plots_written:
            print(f"  - {p}")


if __name__ == "__main__":
    main()

import sys
import pandas as pd
import numpy as np
from pathlib import Path


FILES_DEFAULT = [
    # "2025-08-21_gps_tracker.csv",
    "2025-08-21_gps_tracker_trimmed.csv",
    "2025-08-21_primary_blueraven_hr.csv",
    "2025-08-21_primary_blueraven_lr.csv",
]

# Configurable report directory and filename
REPORT_DIR = "fw_sampling_report"
REPORT_FILE = "summary.txt"


def _ci_lookup(cols, targets):
    """Case-insensitive column lookup. Returns dict of found {logical_name: actual_col}."""
    by_lower = {c.lower(): c for c in cols}
    out = {}
    for key, alts in targets.items():
        for a in alts:
            if a.lower() in by_lower:
                out[key] = by_lower[a.lower()]
                break
    return out


def _combine_datetime(df, date_col, time_col):
    dt = pd.to_datetime(
        df[date_col].astype(str).str.strip()
        + " "
        + df[time_col].astype(str).str.strip(),
        errors="coerce",
        utc=True,
    )
    return dt


def _from_ymd_time(df, y, m, d, t):
    # Ensure two-digit month/day where needed
    ts = df[[y, m, d]].astype(str).agg("-".join, axis=1) + " " + df[t].astype(str)
    dt = pd.to_datetime(ts, errors="coerce", utc=True)
    return dt


def extract_times_seconds(df):
    """Return np.array of seconds since first valid sample, using best available time basis."""
    cols = list(df.columns)

    # Tracker pattern: DATE + TIME
    m = _ci_lookup(cols, {"DATE": ["DATE"], "TIME": ["TIME"]})
    if "DATE" in m and "TIME" in m:
        dt = _combine_datetime(df, m["DATE"], m["TIME"])

    else:
        # Blue Raven pattern: Year,Month,Day,Time
        m2 = _ci_lookup(
            cols, {"Y": ["Year"], "M": ["Month"], "D": ["Day"], "T": ["Time"]}
        )
        if all(k in m2 for k in ("Y", "M", "D", "T")):
            dt = _from_ymd_time(df, m2["Y"], m2["M"], m2["D"], m2["T"])
        else:
            # Fall back to Flight_Time_(s)
            m3 = _ci_lookup(
                cols,
                {
                    "FT": [
                        "Flight_Time_(s)",
                        "Flight Time (s)",
                        "flight_time_s",
                        "flight_time",
                    ]
                },
            )
            if "FT" in m3:
                ft = pd.to_numeric(df[m3["FT"]], errors="coerce")
                return ft.to_numpy(dtype=float)
            else:
                raise ValueError("No usable time columns found.")

    # Convert to seconds from first valid timestamp
    if dt.isna().all():
        raise ValueError("All timestamps are NaT; cannot compute intervals.")
    t0 = dt.dropna().iloc[0]
    secs = (dt.astype("int64") - t0.value) / 1e9  # pandas datetime64[ns] to seconds
    return pd.Series(secs).to_numpy(dtype=float)


def summarize_intervals(seconds):
    seconds = np.asarray(seconds, dtype=float)
    # Remove NaNs and sort by time to be robust
    seconds = seconds[~np.isnan(seconds)]
    if seconds.size < 2:
        return None
    seconds = np.sort(seconds)
    dt = np.diff(seconds)
    # Keep only positive gaps
    dt = dt[dt > 0]
    if dt.size == 0:
        return None
    stats = {
        "samples": int(seconds.size),
        "duration_s": float(seconds[-1] - seconds[0]),
        "mean_dt_s": float(dt.mean()),
        "std_dt_s": float(dt.std(ddof=1)) if dt.size > 1 else 0.0,
        "min_dt_s": float(dt.min()),
        "max_dt_s": float(dt.max()),
        "mean_hz": float(1.0 / dt.mean()) if dt.mean() > 0 else float("nan"),
        # Placeholders for timestamps, will be filled in analyze_file
        "first_utc": None,
        "last_utc": None,
    }
    return stats


def analyze_file(path):
    # Try standard CSV; engine='python' handles odd rows gracefully
    df = pd.read_csv(path, engine="python")
    times = extract_times_seconds(df)
    stats = summarize_intervals(times)
    # Try to get first and last UTC timestamp
    # Use same logic as extract_times_seconds for timestamp columns
    cols = list(df.columns)
    m = _ci_lookup(cols, {"DATE": ["DATE"], "TIME": ["TIME"]})
    if "DATE" in m and "TIME" in m:
        dt = _combine_datetime(df, m["DATE"], m["TIME"])
    else:
        m2 = _ci_lookup(
            cols, {"Y": ["Year"], "M": ["Month"], "D": ["Day"], "T": ["Time"]}
        )
        if all(k in m2 for k in ("Y", "M", "D", "T")):
            dt = _from_ymd_time(df, m2["Y"], m2["M"], m2["D"], m2["T"])
        else:
            dt = None
    if stats is not None and dt is not None and not dt.isna().all():
        dt_valid = dt.dropna()
        if not dt_valid.empty:
            stats["first_utc"] = dt_valid.iloc[0].isoformat()
            stats["last_utc"] = dt_valid.iloc[-1].isoformat()
    return stats


def main(file_paths):
    report_dir = Path(REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / REPORT_FILE
    with open(report_path, "w", encoding="utf-8") as f:
        for p in file_paths:
            try:
                stats = analyze_file(p)
                f.write(f"\n=== {p} ===\n")
                if not stats:
                    f.write("Insufficient data to compute intervals.\n")
                    continue
                f.write(f"samples            : {stats['samples']}\n")
                if stats.get("first_utc"):
                    f.write(f"first_utc          : {stats['first_utc']}\n")
                if stats.get("last_utc"):
                    f.write(f"last_utc           : {stats['last_utc']}\n")
                f.write(f"duration           : {stats['duration_s']:.6f} s\n")
                f.write(
                    f"mean interval      : {stats['mean_dt_s']:.6f} s  | {stats['mean_hz']:.3f} Hz\n"
                )
                f.write(f"std interval       : {stats['std_dt_s']:.6f} s\n")
                f.write(f"min interval       : {stats['min_dt_s']:.6f} s\n")
                f.write(f"max interval       : {stats['max_dt_s']:.6f} s\n")
            except FileNotFoundError as e:
                f.write(f"\n=== {p} ===\n")
                f.write(f"File not found: {e}\n")
            except pd.errors.ParserError as e:
                f.write(f"\n=== {p} ===\n")
                f.write(f"CSV parse error: {e}\n")
            except ValueError as e:
                f.write(f"\n=== {p} ===\n")
                f.write(f"Value error: {e}\n")
            except OSError as e:
                f.write(f"\n=== {p} ===\n")
                f.write(f"OS error: {e}\n")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = FILES_DEFAULT
    # Resolve existing files in current dir
    paths = [str(Path(a)) for a in args]
    main(paths)

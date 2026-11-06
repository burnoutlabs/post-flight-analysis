# Trim the Featherweight GPS tracker CSV to the time window defined by the
# Blue Raven Low-Rate (LR) log start/end, expanded by configurable offsets.

import pandas as pd
from pathlib import Path

# ---- CONFIG ----
GPS_FILE = "2025-08-21_gps_tracker.csv"
LR_FILE = "2025-08-21_primary_blueraven_lr.csv"
START_OFFSET_S = 5.0  # seconds BEFORE LR start to include
END_OFFSET_S = 15.0  # seconds AFTER LR end to include
OUT_FILE = "2025-08-21_gps_tracker_trimmed.csv"


def _ci(cols):
    """Case-insensitive column map."""
    return {c.lower(): c for c in cols}


def _parse_ts_gps(df: pd.DataFrame) -> pd.Series:
    """Parse tracker DATE + TIME into a single pandas datetime64[ns] (naive)."""
    m = _ci(df.columns)
    date_col = m.get("date")
    time_col = m.get("time")
    if date_col is None or time_col is None:
        raise ValueError("GPS CSV must contain DATE and TIME columns.")
    ts = pd.to_datetime(
        df[date_col].astype(str).str.strip()
        + " "
        + df[time_col].astype(str).str.strip(),
        errors="coerce",
    )
    if ts.isna().all():
        raise ValueError("Failed to parse any timestamps in GPS file.")
    return ts


def _parse_ts_lr(df: pd.DataFrame) -> pd.Series:
    """Parse LR Year/Month/Day + Time; fallback to Flight_Time_(s) if needed."""
    m = _ci(df.columns)
    y, mo, d, t = m.get("year"), m.get("month"), m.get("day"), m.get("time")
    if y and mo and d and t:
        s = df[[y, mo, d]].astype(str).agg("-".join, axis=1) + " " + df[t].astype(str)
        ts = pd.to_datetime(s, errors="coerce")
        if not ts.isna().all():
            return ts
    # Fallback: use Flight_Time_(s) to synthesize a monotonic time axis
    for k in ("flight_time_(s)", "flight time (s)", "flight_time_s", "flight_time"):
        col = m.get(k)
        if col:
            ft = pd.to_numeric(df[col], errors="coerce")
            if ft.notna().any():
                t0 = ft.dropna().iloc[0]
                # synthesize pseudo-absolute timestamps using the first as epoch
                return pd.to_datetime(t0, unit="s") + pd.to_timedelta(ft - t0, unit="s")
    raise ValueError(
        "LR CSV must have Year/Month/Day/Time or a Flight_Time_(s) column."
    )


def main():
    gps_path = Path(GPS_FILE)
    lr_path = Path(LR_FILE)
    out_path = Path(OUT_FILE)

    gps_df = pd.read_csv(gps_path, engine="python")
    lr_df = pd.read_csv(lr_path, engine="python")

    gps_ts = _parse_ts_gps(gps_df)
    lr_ts = _parse_ts_lr(lr_df)

    lr_ts_valid = lr_ts.dropna()
    if lr_ts_valid.empty:
        raise ValueError("No valid timestamps found in LR file.")

    lr_start = lr_ts_valid.min()
    lr_end = lr_ts_valid.max()

    window_start = lr_start - pd.to_timedelta(float(START_OFFSET_S), unit="s")
    window_end = lr_end + pd.to_timedelta(float(END_OFFSET_S), unit="s")

    gps_df["_ts"] = gps_ts
    trimmed = gps_df[
        (gps_df["_ts"] >= window_start) & (gps_df["_ts"] <= window_end)
    ].copy()
    trimmed.drop(columns=["_ts"], inplace=True, errors="ignore")
    trimmed.to_csv(out_path, index=False)

    total = len(gps_df)
    kept = len(trimmed)
    print(f"LR window        : {lr_start} .. {lr_end}")
    print(f"Trim window      : {window_start} .. {window_end}")
    print(f"GPS rows         : {total}")
    print(
        f"Trimmed rows     : {kept} ({(kept / total * 100 if total else 0):.1f}% kept)"
    )
    print(f"Wrote            : {out_path.resolve()}")


if __name__ == "__main__":
    main()

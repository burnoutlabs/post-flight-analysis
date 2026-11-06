import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# User-configurable variables
INPUT_CSV_DEFAULT = "2025-08-21_gps_tracker_trimmed.csv"
REPORT_DIR_DEFAULT = "gps_interval_report_trimmed"
# INPUT_CSV_DEFAULT = "2025-08-21_gps_tracker.csv"
# REPORT_DIR_DEFAULT = "gps_interval_report"


def read_tracker(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, engine="python")
    # Case-insensitive access
    cols = {c.lower(): c for c in df.columns}
    date_col = cols.get("date")
    time_col = cols.get("time")
    if date_col is None or time_col is None:
        raise ValueError("Expected DATE and TIME columns in GPS tracker CSV.")
    dt = pd.to_datetime(
        df[date_col].astype(str).str.strip()
        + " "
        + df[time_col].astype(str).str.strip(),
        errors="coerce",
        utc=True,
    )
    df["_ts"] = dt
    df = df.sort_values("_ts").reset_index(drop=True)
    return df


def compute_intervals(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["_ts"]
    if ts.isna().all():
        raise ValueError("All timestamps are NaT.")
    # Compute deltas in seconds; align with the *current* row (interval between i-1 and i)
    dt = ts.astype("int64").to_numpy()
    # mask invalid
    valid = ~ts.isna().to_numpy()
    dt_sec = np.full_like(dt, np.nan, dtype=float)
    idx = np.where(valid)[0]
    if idx.size >= 2:
        diffs = (dt[idx[1:]] - dt[idx[:-1]]) / 1e9
        dt_sec[idx[1:]] = diffs
    out = df.copy()
    out["_dt_s"] = dt_sec
    # Filter strictly positive intervals for stats
    pos = out["_dt_s"] > 0
    out["_dt_pos"] = out["_dt_s"].where(pos)
    return out


def detect_outliers(dt_series: pd.Series, z_thresh: float = 3.0):
    x = dt_series.dropna().to_numpy()
    if x.size == 0:
        return dict(indices=np.array([], dtype=int), stats={})
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    iqr_hi = q3 + 1.5 * iqr
    iqr_hi_extreme = q3 + 3.0 * iqr
    mu = np.mean(x)
    sigma = np.std(x, ddof=1) if x.size > 1 else 0.0
    # Build boolean masks on the *original index* order of dt_series
    iqr_mask = dt_series > iqr_hi
    # Ensure dt_series is float for arithmetic
    dt_float = dt_series.astype(float).to_numpy()
    z_mask = (
        ((dt_float - mu) / sigma > z_thresh)
        if sigma > 0
        else np.zeros_like(dt_float, dtype=bool)
    )
    # iqr_mask is a Series, z_mask is a numpy array, align indices
    mask = iqr_mask.to_numpy() | z_mask
    outlier_idx = dt_series.index[mask].to_numpy(dtype=int)
    stats = {
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "iqr_hi": float(iqr_hi),
        "iqr_hi_extreme": float(iqr_hi_extreme),
        "mean": float(mu),
        "std": float(sigma),
        "z_thresh": float(z_thresh),
        "count": int(x.size),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
    }
    return dict(indices=outlier_idx, stats=stats)


def save_outliers_csv(df_dt: pd.DataFrame, outlier_idx: np.ndarray, out_path: Path):
    rows = []
    for i in outlier_idx:
        # interval is between i-1 and i; capture neighbor timestamps
        ts_curr = df_dt.loc[i, "_ts"] if i in df_dt.index else pd.NaT
        ts_prev = df_dt.loc[i - 1, "_ts"] if i - 1 in df_dt.index else pd.NaT
        dt_s = df_dt.loc[i, "_dt_s"] if i in df_dt.index else np.nan

        def iso_or_none(ts):
            # Only call isoformat if it's a Timestamp or datetime
            if pd.notna(ts) and hasattr(ts, "isoformat"):
                return ts.isoformat()
            return None

        # Robust float conversion for numpy types
        if pd.isna(dt_s):
            interval_val = np.nan
        else:
            try:
                interval_val = float(np.asarray(dt_s).item())
            except (TypeError, ValueError):
                interval_val = np.nan
        rows.append(
            {
                "sample_index": int(i),
                "interval_s": interval_val,
                "t_prev": iso_or_none(ts_prev),
                "t_curr": iso_or_none(ts_curr),
            }
        )
    pd.DataFrame(rows).to_csv(out_path, index=False)


def plot_interval_vs_index(
    df_dt: pd.DataFrame, outlier_idx: np.ndarray, out_prefix: Path
):
    # 1) Interval vs index
    fig = plt.figure()
    plt.plot(
        df_dt.index.to_numpy(), df_dt["_dt_s"].to_numpy(), marker=".", linestyle="none"
    )
    # Mark outliers
    if outlier_idx.size:
        plt.plot(
            outlier_idx,
            df_dt.loc[outlier_idx, "_dt_s"].to_numpy(),
            marker="o",
            linestyle="none",
        )
    plt.xlabel("Sample index (i)")
    plt.ylabel("Interval Δt (s) between i-1 and i")
    plt.title("GPS interval vs sample index")
    plt.tight_layout()
    fig.savefig(out_prefix.with_suffix(".interval_vs_index.png"), dpi=150)
    plt.close(fig)


def plot_interval_hist(df_dt: pd.DataFrame, out_prefix: Path):
    # 2) Histogram of positive intervals (log-x bins useful, but avoid styles; use many bins)
    x = df_dt["_dt_pos"].dropna().to_numpy()
    if x.size == 0:
        return
    fig = plt.figure()
    bins = (
        np.geomspace(max(1e-3, np.min(x[x > 0]) if np.any(x > 0) else 1e-3), max(x), 60)
        if np.any(x > 0)
        else 60
    )
    # Ensure bins is either int or a sequence of floats
    if isinstance(bins, (np.ndarray, list)):
        bins = bins.tolist() if isinstance(bins, np.ndarray) else bins
    plt.hist(x, bins=bins)
    plt.xscale("log")
    plt.xlabel("Interval Δt (s) [log scale]")
    plt.ylabel("Count")
    plt.title("Histogram of positive intervals")
    plt.tight_layout()
    fig.savefig(out_prefix.with_suffix(".interval_hist.png"), dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(
        description="Plot GPS tracker sampling intervals and flag outliers."
    )
    ap.add_argument("input_csv", nargs="?", default=INPUT_CSV_DEFAULT)
    ap.add_argument("--out-dir", default=REPORT_DIR_DEFAULT)
    ap.add_argument(
        "--z", type=float, default=3.0, help="z-score threshold for outliers"
    )
    args = ap.parse_args()

    in_path = Path(args.input_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = read_tracker(in_path)
    df_dt = compute_intervals(df)

    out = detect_outliers(df_dt["_dt_pos"], z_thresh=args.z)
    outlier_idx = np.array(out["indices"], dtype=int)
    stats = dict(out["stats"])  # Ensure stats is a dict for .items()

    # Save summaries
    summary_txt = out_dir / "summary.txt"
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write(f"file: {in_path}\n")
        f.write(f"samples: {len(df_dt)}\n")
        dur = (
            df_dt["_ts"].dropna().iloc[-1] - df_dt["_ts"].dropna().iloc[0]
        ).total_seconds()
        f.write(f"duration_s: {dur:.3f}\n")
        dt = df_dt["_dt_pos"].dropna().to_numpy()
        if dt.size:
            f.write(f"mean_dt_s: {np.mean(dt):.6f}\n")
            f.write(f"std_dt_s: {np.std(dt, ddof=1) if dt.size > 1 else 0.0:.6f}\n")
            f.write(f"min_dt_s: {np.min(dt):.6f}\n")
            f.write(f"max_dt_s: {np.max(dt):.6f}\n")
            f.write(f"mean_hz: {1.0 / np.mean(dt):.6f}\n")
        f.write("\nOutlier method: IQR + z-score\n")
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
        f.write(f"outlier_count: {len(outlier_idx)}\n")

    # Save outliers csv
    save_outliers_csv(df_dt, outlier_idx, out_dir / "interval_outliers.csv")

    # Plots
    out_prefix = out_dir / in_path.stem
    plot_interval_vs_index(df_dt, outlier_idx, out_prefix)
    plot_interval_hist(df_dt, out_prefix)

    print(f"Wrote: {summary_txt}")
    print(f"Wrote: {out_dir / 'interval_outliers.csv'}")
    print(f"Wrote: {out_prefix.with_suffix('.interval_vs_index.png')}")
    print(f"Wrote: {out_prefix.with_suffix('.interval_hist.png')}")


if __name__ == "__main__":
    main()

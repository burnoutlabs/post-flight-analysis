"""TeleMega flight time comes from the log's own `time` column.

AltOS records `time` as seconds since launch. Deriving flight time from the
GPS clock instead put Hyperion-II's apogee at 48.35 s rather than 24.05 s.
"""

from __future__ import annotations

import pandas as pd
import pytest
from conftest import DATA

from pfa.analyze import compute_summary
from pfa.parsers import parse_telemega_csv

HYPERION2 = (
    DATA / "2025-08-21_hyperion2_lc25" / "raw" / "src" / "2025-08-21-serial-6583-flight-0005.csv"
)
PROMETHEUS = DATA / "2022-06-24_prometheus_sac22" / "raw" / "2022-06-24-serial-6583-flight-0003.csv"


def _peak_time(df: pd.DataFrame) -> float:
    alt = pd.to_numeric(df["alt_agl_m"], errors="coerce")
    return float(pd.to_numeric(df["t_flight_s"], errors="coerce")[alt.idxmax()])


def test_hyperion2_apogee_at_vendor_time():
    df, _ = parse_telemega_csv(HYPERION2)
    assert _peak_time(df) == pytest.approx(24.05, abs=0.05)


def test_prometheus_apogee_at_vendor_time():
    df, _ = parse_telemega_csv(PROMETHEUS)
    assert _peak_time(df) == pytest.approx(28.81, abs=0.05)


def test_hyperion2_summary_timing():
    df, _ = parse_telemega_csv(HYPERION2)
    s = compute_summary(df)
    assert s["time_to_apogee_s"] == pytest.approx(24.05, abs=0.05)
    # boost -> coast at time = 3.20 s in the raw log
    assert s["burn_time_s"] == pytest.approx(3.2, abs=0.05)


def test_epoch_still_from_gps_clock():
    df, _ = parse_telemega_csv(HYPERION2)
    first = pd.Timestamp(float(df["t_epoch_s"].iloc[0]), unit="s", tz="UTC")
    # GPS clock in the first rows reads 2025-08-21 18:11:46 UTC
    assert first.strftime("%Y-%m-%d %H:%M") == "2025-08-21 18:11"


def _gps_clock_by_time(path) -> pd.DataFrame:
    """Raw GPS clock (whole seconds, UTC epoch) keyed by the row's `time`."""
    raw = pd.read_csv(path, skipinitialspace=True, engine="python")
    raw.columns = [c.strip().lstrip("#") for c in raw.columns]
    parts = raw[["year", "month", "day", "hour", "minute", "second"]]
    epoch0 = pd.Timestamp("1970-01-01", tz="UTC")
    gps = (pd.to_datetime(parts, utc=True) - epoch0).dt.total_seconds()
    out = pd.DataFrame({"t_flight_s": pd.to_numeric(raw["time"]), "gps": gps})
    return out.drop_duplicates(subset=["t_flight_s"])


@pytest.mark.parametrize("path", [HYPERION2, PROMETHEUS], ids=["hyperion2", "prometheus"])
def test_epoch_span_matches_vendor_time_span(path):
    # GPS clock fields already advance with each row; adding `time` on top
    # counted the elapsed time twice (Hyperion-II: 156.2 s instead of 78.2 s).
    df, _ = parse_telemega_csv(path)
    epoch = pd.to_numeric(df["t_epoch_s"], errors="coerce")
    t = pd.to_numeric(df["t_flight_s"], errors="coerce")
    assert epoch.max() - epoch.min() == pytest.approx(t.max() - t.min(), abs=1.0)


@pytest.mark.parametrize("path", [HYPERION2, PROMETHEUS], ids=["hyperion2", "prometheus"])
def test_epoch_tracks_gps_clock_on_every_row(path):
    # One clock: every row sits within the GPS clock's own resolution of the
    # whole second it logged, the first row and the last alike. The GPS clock
    # truncates to the second (so the epoch reads up to 1 s ahead of it) and
    # ticks over a sample or so early or late; allow 0.25 s for that.
    df, _ = parse_telemega_csv(path)
    rows = (
        df[["t_flight_s", "t_epoch_s"]]
        .astype(float)
        .merge(_gps_clock_by_time(path), on="t_flight_s", how="inner")
    )
    assert len(rows) == len(df)
    ahead = rows["t_epoch_s"] - rows["gps"]
    assert ahead.min() > -0.25
    assert ahead.max() < 1.25

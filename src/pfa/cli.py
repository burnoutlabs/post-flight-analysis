from __future__ import annotations

from pathlib import Path

import typer

from .common import PreprocessOptions, ensure_dir, write_csv, write_meta
from .parsers import (
    parse_blueraven_csv,
    parse_blueraven_hr_csv,
    parse_featherweight,
    parse_telemega_csv,
)
from .parsers.blueraven_summary import blueraven_identity

app = typer.Typer(add_completion=False)


@app.callback()
def _callback() -> None:
    """Post-flight analysis tools."""


def _read_first_nonempty_line(p: Path) -> str:
    with p.open("rb") as f:
        raw = f.read(4096)
    try:
        text = raw.decode("utf-8-sig", errors="ignore")
    except Exception:
        text = raw.decode("latin-1", errors="ignore")
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _altus_serial(p: Path) -> str | None:
    """Serial number from the first data row of an Altus Metrum CSV."""
    with p.open("rb") as f:
        text = f.read(8192).decode("utf-8-sig", errors="ignore")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    header = [c.strip().lstrip("#") for c in lines[0].split(",")]
    row = [c.strip() for c in lines[1].split(",")]
    if "serial" not in header:
        return None
    i = header.index("serial")
    return row[i] if i < len(row) and row[i] else None


def _sniff_kind(p: Path) -> str | None:
    """Return kind string by inspecting the file header/content.

    Altus Metrum CSVs are split by their columns: logs with the IMU columns
    (``accel_x``, ``gyro_roll``) are ``telemega``; other Altus Metrum loggers,
    such as the 67-column log without them, are ``altusmetrum``.
    """
    if not p.is_file():
        return None
    suffix = p.suffix.lower()

    if suffix == ".csv":
        head = _read_first_nonempty_line(p)
        hlow = head.lower()
        if hlow.startswith("#version,serial,flight"):
            cols = {c.strip() for c in hlow.lstrip("#").split(",")}
            if {"accel_x", "gyro_roll"} <= cols:
                return "telemega"
            return "altusmetrum"
        if hlow.startswith("rocket name,"):
            return "blueraven_summary"
        if "baro_altitude_asl_(feet)" in hlow or "baro_altitude_agl_(feet)" in hlow:
            return "blueraven"
        if "gyro_x" in hlow and "flight_time_(s)" in hlow:
            return "blueraven_hr"
        if "tracker lat" in hlow and "tracker lon" in hlow:
            return "featherweight"
        return None

    if suffix == ".xlsx":
        try:
            import openpyxl

            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            ws = wb.active
            first_row = next(ws.iter_rows(max_row=1, values_only=True), ())
            hlow = ",".join(str(c).lower().strip() for c in first_row if c is not None)
            if "tracker lat" in hlow and "tracker lon" in hlow:
                return "featherweight"
        except Exception:
            pass
        return None

    return None


_ALTUS_KINDS = ("telemega", "altusmetrum")


def _find_files(raw: Path, verbose: bool) -> dict[str, Path]:
    """Map output name -> input file.

    Top-level raw/ has priority; raw/src/ fills in what is not already found.
    For most kinds the name is the kind and only the first file is used.
    Altus Metrum logs are keyed by serial number so that two loggers in one
    flight both survive: the first TeleMega keeps the plain ``telemega`` name,
    any other Altus Metrum log is ``<kind>_<serial>``. A second copy of a log
    from the same serial is skipped.
    """
    found: dict[str, Path] = {}
    altus_serials: set[tuple[str, str | None]] = set()

    def _scan(directory: Path, where: str) -> None:
        for p in sorted(directory.glob("*")):
            if p.is_dir():
                continue
            kind = _sniff_kind(p)
            if not kind:
                continue
            if kind in _ALTUS_KINDS:
                serial = _altus_serial(p)
                if (kind, serial) in altus_serials:
                    continue
                altus_serials.add((kind, serial))
                key = kind if kind == "telemega" and kind not in found else f"{kind}_{serial}"
            else:
                key = kind
            if key in found:
                continue
            if verbose:
                typer.echo(f"Detected {kind} file{where}: {p.name}")
            found[key] = p

    _scan(raw, "")
    if (raw / "src").is_dir():
        _scan(raw / "src", " (src/)")
    return found


def _row_counts(df, meta: dict, *, gps: bool = True) -> dict:
    gps_valid = int(df["lat_deg"].notna().sum()) if gps and "lat_deg" in df.columns else 0
    return meta.get(
        "row_counts", {"total": len(df), "after_clean": len(df), "gps_valid": gps_valid}
    )


@app.command()
def preprocess(
    flight_dir: str = typer.Argument(..., help="Path to data/<date>_<vehicle>_<event>"),
    tz: str = typer.Option("America/Toronto", "--tz", help="Local time zone for Blue Raven logs"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    fpath = Path(flight_dir)
    raw = fpath / "raw"
    interim = fpath / "interim"
    ensure_dir(interim)

    if not raw.exists():
        typer.echo(f"Raw folder not found: {raw}")
        raise typer.Exit(code=1)

    files = _find_files(raw, verbose)
    if not files:
        typer.echo(f"No recognizable device files found in {raw}")
        raise typer.Exit(code=2)

    opts = PreprocessOptions(tz_name=tz)

    # The Blue Raven summary carries no samples, only the device identity.
    summary_file = files.get("blueraven_summary")
    br_identity = blueraven_identity(summary_file) if summary_file else {}

    wrote_any = False
    for key, path in files.items():
        kind = _sniff_kind(path)
        extra_inputs: list[Path] = []
        gps = True
        if kind in _ALTUS_KINDS:
            if verbose:
                typer.echo(f"Parsing {key} (Altus Metrum)...")
            df, meta = parse_telemega_csv(path, source=kind)
        elif kind == "blueraven":
            if verbose:
                typer.echo("Parsing Blue Raven altimeter...")
            df, meta = parse_blueraven_csv(path, tz_name=opts.tz_name)
        elif kind == "blueraven_hr":
            if verbose:
                typer.echo("Parsing Blue Raven HR IMU...")
            df, meta = parse_blueraven_hr_csv(path, tz_name=opts.tz_name)
            gps = False
        elif kind == "featherweight":
            if verbose:
                typer.echo("Parsing FeatherWeight GPS tracker...")
            df, meta = parse_featherweight(path)
        else:
            continue

        if kind in ("blueraven", "blueraven_hr") and summary_file:
            meta["serial"] = br_identity.get("serial")
            meta["firmware"] = br_identity.get("firmware")
            extra_inputs.append(summary_file)

        out_csv = interim / f"{key}_std.csv"
        write_csv(df, out_csv)
        write_meta(
            interim / f"{key}_std.meta.json",
            base_dir=fpath,
            input_files=[path, *extra_inputs],
            device=kind,
            serial=meta.get("serial"),
            firmware=meta.get("firmware"),
            mapping_used=meta.get("mapping_used", {}),
            units_converted=meta.get("units_converted", []),
            liftoff_method=meta.get("liftoff_method", "unknown"),
            row_counts=_row_counts(df, meta, gps=gps),
        )
        typer.echo(f"Wrote {out_csv}")
        wrote_any = True

    if not wrote_any:
        typer.echo("No recognisable device files detected after sniffing.")
        raise typer.Exit(code=3)


@app.command()
def analyze(
    flight_dir: str = typer.Argument(..., help="Path to data/<date>_<vehicle>_<event>"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """
    Generate flight-profile plots and print summary metrics for a preprocessed flight.
    Reads interim/*_std.csv produced by 'pfa preprocess'.
    Saves figures to <flight_dir>/figures/.
    """
    import math

    from .analyze import analyze_flight

    fpath = Path(flight_dir)
    if not (fpath / "interim").exists():
        typer.echo(f"No interim/ directory found in {fpath}. Run 'pfa preprocess' first.")
        raise typer.Exit(code=1)

    summary = analyze_flight(fpath, verbose=verbose)

    def _fmt(val: float, fmt: str = ".0f") -> str:
        return (f"{val:{fmt}}") if not math.isnan(val) else "n/a"

    typer.echo(f"\n=== {summary['flight']} ===")
    typer.echo(f"  Sources:          {', '.join(summary['sources'])}")
    typer.echo(
        f"  Apogee AGL:       {_fmt(summary['apogee_m'])} m  ({_fmt(summary['apogee_ft'])} ft)"
    )
    typer.echo(f"  Time to apogee:   {_fmt(summary['time_to_apogee_s'], '.1f')} s")
    typer.echo(
        f"  Max velocity:     {_fmt(summary['max_velocity_mps'])} m/s  "
        f"({_fmt(summary['max_velocity_fps'])} ft/s)"
    )
    typer.echo(f"  Max acceleration: {_fmt(summary['max_accel_g'], '.1f')} G")
    if not math.isnan(summary["burn_time_s"]):
        typer.echo(f"  Motor burn time:  {_fmt(summary['burn_time_s'], '.2f')} s")
    for fig_path in summary["figures"]:
        typer.echo(f"  Saved figure:     {fig_path}")


@app.command()
def compare(
    data_dir: str = typer.Argument("data", help="Root directory containing flight folders"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """
    Print a cross-flight summary table for all preprocessed flights found under data_dir.
    Does not regenerate figures.
    """
    import math

    from .analyze import _load_interim, compute_summary

    data_path = Path(data_dir)
    flight_dirs = sorted(p for p in data_path.iterdir() if p.is_dir() and (p / "interim").exists())

    if not flight_dirs:
        typer.echo(f"No preprocessed flights found under {data_path}")
        raise typer.Exit(code=1)

    summaries = []
    for fd in flight_dirs:
        try:
            datasets = _load_interim(fd / "interim")
            if not datasets:
                continue
            # Primary source: TeleMega > BlueRaven > FeatherWeight > HR
            primary = None
            for key in ("telemega_std", "blueraven_std", "featherweight_std"):
                if key in datasets:
                    primary = datasets[key]
                    break
            if primary is None:
                primary = next(iter(datasets.values()))
            s = compute_summary(primary)
            s["flight"] = fd.name
            s["sources"] = list(datasets.keys())
            summaries.append(s)
            if verbose:
                typer.echo(f"  Loaded {fd.name}: {list(datasets.keys())}")
        except Exception as exc:
            typer.echo(f"  Warning: {fd.name}: {exc}")

    if not summaries:
        typer.echo("No summaries could be computed.")
        raise typer.Exit(code=1)

    def _f(v: float, fmt: str = ".0f") -> str:
        return f"{v:{fmt}}" if not math.isnan(v) else "n/a"

    w = 34  # flight name column width
    typer.echo("")
    typer.echo(
        f"{'Flight':<{w}} {'Apogee(m)':>10} {'Apogee(ft)':>11} "
        f"{'t_apo(s)':>9} {'MaxVel(m/s)':>12} {'MaxG':>6} {'Burn(s)':>8}  Sources"
    )
    typer.echo("-" * (w + 10 + 11 + 9 + 12 + 6 + 8 + 30))
    for s in summaries:
        src_str = ", ".join(k.replace("_std", "") for k in s["sources"])
        typer.echo(
            f"{s['flight']:<{w}} "
            f"{_f(s['apogee_m']):>10} "
            f"{_f(s['apogee_ft']):>11} "
            f"{_f(s['time_to_apogee_s'], '.1f'):>9} "
            f"{_f(s['max_velocity_mps'], '.0f'):>12} "
            f"{_f(s['max_accel_g'], '.1f'):>6} "
            f"{_f(s['burn_time_s'], '.2f'):>8}  "
            f"{src_str}"
        )
    typer.echo("")

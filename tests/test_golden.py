"""`pfa preprocess` must reproduce the committed interim outputs exactly.

A parser change that alters any committed `interim/*_std.csv` fails here.
When the change is intended, regenerate the interim files with
`pfa preprocess` and commit them together with the code.
"""

from __future__ import annotations

import json

from conftest import DATA, copy_flight
from typer.testing import CliRunner

from pfa.cli import app

runner = CliRunner()


def _preprocess(flight_dir) -> None:
    result = runner.invoke(app, ["preprocess", str(flight_dir)])
    assert result.exit_code == 0, result.output


def test_interim_csv_matches_committed(flight_name, tmp_path):
    out = copy_flight(flight_name, tmp_path)
    _preprocess(out)

    committed = sorted(p.name for p in (DATA / flight_name / "interim").glob("*_std.csv"))
    produced = sorted(p.name for p in (out / "interim").glob("*_std.csv"))
    assert produced == committed

    for name in committed:
        expected = (DATA / flight_name / "interim" / name).read_bytes()
        actual = (out / "interim" / name).read_bytes()
        assert actual == expected, f"{flight_name}/interim/{name} differs from the committed file"


def test_meta_matches_committed(flight_name, tmp_path):
    """Meta files match apart from the generation timestamp, on any OS and cwd."""
    out = copy_flight(flight_name, tmp_path)
    _preprocess(out)

    committed = sorted(p.name for p in (DATA / flight_name / "interim").glob("*.meta.json"))
    produced = sorted(p.name for p in (out / "interim").glob("*.meta.json"))
    assert produced == committed

    for name in committed:
        expected = json.loads((DATA / flight_name / "interim" / name).read_text(encoding="utf-8"))
        actual = json.loads((out / "interim" / name).read_text(encoding="utf-8"))
        expected.pop("generated_at_utc")
        actual.pop("generated_at_utc")
        assert actual == expected, f"{flight_name}/interim/{name} differs from the committed file"


def test_meta_input_paths_are_relative_posix(flight_name):
    for meta in (DATA / flight_name / "interim").glob("*.meta.json"):
        for entry in json.loads(meta.read_text(encoding="utf-8"))["input_files"]:
            path = entry["path"]
            assert "\\" not in path, path
            assert path.startswith("raw/"), path
            assert (DATA / flight_name / path).is_file(), path

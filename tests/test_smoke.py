"""`pfa analyze` and `pfa compare` run on the committed interim data."""

from __future__ import annotations

from conftest import FLIGHTS, copy_flight
from typer.testing import CliRunner

from pfa.cli import app

runner = CliRunner()


def test_analyze_exits_zero(flight_name, tmp_path):
    out = copy_flight(flight_name, tmp_path, with_interim=True)
    result = runner.invoke(app, ["analyze", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "figures" / "flight_profile.png").is_file()


def test_compare_lists_every_flight(tmp_path):
    for name in FLIGHTS:
        copy_flight(name, tmp_path, with_interim=True)
    result = runner.invoke(app, ["compare", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for name in FLIGHTS:
        assert name in result.output

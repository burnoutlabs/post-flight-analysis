from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

# Plots are written to files only; never open a window.
os.environ.setdefault("MPLBACKEND", "Agg")

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FLIGHTS = sorted(p.name for p in DATA.iterdir() if (p / "raw").is_dir())


def copy_flight(name: str, dest_root: Path, *, with_interim: bool = False) -> Path:
    """Copy a flight's raw/ (and optionally interim/) into dest_root/<name>."""
    src = DATA / name
    dst = dest_root / name
    shutil.copytree(src / "raw", dst / "raw")
    if with_interim:
        shutil.copytree(src / "interim", dst / "interim")
    return dst


@pytest.fixture(params=FLIGHTS)
def flight_name(request) -> str:
    return request.param

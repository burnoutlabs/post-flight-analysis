"""`_sniff_kind` recognises each supported device file by its content."""

from __future__ import annotations

import pytest
from conftest import DATA

from pfa.cli import _sniff_kind

LC25 = DATA / "2025-08-21_hyperion2_lc25" / "raw"
SAC24 = DATA / "2024-06-21_hyperion1_sac24" / "raw"
SAC22 = DATA / "2022-06-24_prometheus_sac22" / "raw"


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        (LC25 / "src" / "2025-08-21-serial-6583-flight-0005.csv", "telemega"),
        (LC25 / "src" / "WERT FBR LR_08-21-2025_14_11_45.csv", "blueraven"),
        (LC25 / "src" / "WERT FBR HR_08-21-2025_14_11_45.csv", "blueraven_hr"),
        (LC25 / "src" / "FthrWt03337_08-21-2025_13_28_45.csv", "featherweight"),
        (SAC24 / "FthrWt03337_09-19-2024_20_12_48.xlsx", "featherweight"),
        (SAC22 / "2022-06-24-serial-5115-flight-0001.csv", "altusmetrum"),
        (LC25 / "src" / "WERT FBR_summary_08-21-2025_14_11_45_.csv", "blueraven_summary"),
    ],
    ids=lambda v: v if isinstance(v, str) else v.name,
)
def test_sniff_known_devices(path, kind):
    assert _sniff_kind(path) == kind


@pytest.mark.parametrize(
    "path",
    [
        LC25 / "src" / "2025-08-21-serial-6583-flight-0005.eeprom",
        LC25 / "src" / "BR_deploy_settings__08-21-2025_14_11_45.xlsx",
        LC25 / "src" / "FthrWt03337_fw2kml_08-21-2025_13_28_45.kml",
        LC25 / "src" / "2025-08-21-serial-6583-flight-0005.kml",
        SAC22 / "2022-06-24-serial-6583-flight-0003.kml",
    ],
    ids=lambda p: p.name,
)
def test_sniff_ignores_other_files(path):
    assert _sniff_kind(path) is None


def test_sniff_unknown_csv(tmp_path):
    p = tmp_path / "other.csv"
    p.write_text("a,b,c\n1,2,3\n")
    assert _sniff_kind(p) is None

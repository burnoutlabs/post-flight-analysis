"""Blue Raven flight summary CSV (Featherweight app export).

The file is a key/value list, one ``key,value`` pair per line
(``Rocket Name``, ``Firmware``, ``Serial number``, ``Max Altitude``, ...).
pfa reads it only for the device identity; the flight figures are not used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


def read_blueraven_summary(path: Path) -> Dict[str, str]:
    """Return the summary as {key: value}, value being everything after the first comma."""
    fields: Dict[str, str] = {}
    text = Path(path).read_bytes().decode("utf-8-sig", errors="replace")
    for line in text.splitlines():
        if "," not in line:
            continue
        key, value = line.split(",", 1)
        key = key.strip()
        if key and key not in fields:
            fields[key] = value.strip()
    return fields


def blueraven_identity(path: Path) -> Dict[str, Optional[str]]:
    """Serial and firmware from a summary file.

    The app writes the serial as ``SN628 WERT FBR``: the serial followed by
    the rocket name. The rocket name is dropped when it is there.
    """
    fields = read_blueraven_summary(path)
    serial = fields.get("Serial number") or None
    name = fields.get("Rocket Name")
    if serial and name and serial.endswith(name) and serial != name:
        serial = serial[: -len(name)].strip()
    return {"serial": serial, "firmware": fields.get("Firmware") or None}

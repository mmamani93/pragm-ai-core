#!/usr/bin/env python3
"""Build the per-user PragmAI Windows installer with NSIS."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_SOURCE = ROOT / "adapters" / "pragm_ai_connector.py"
STANDALONE = ROOT / "dist" / "standalone" / "pragmai.exe"
NSIS_SCRIPT = ROOT / "installer" / "windows" / "pragmai.nsi"
DIST_DIR = ROOT / "dist" / "installer"
OUTPUT_NAME = "pragmai-windows-x64-setup.exe"


def connector_version() -> str:
    source = CONNECTOR_SOURCE.read_text(encoding="utf-8")
    match = re.search(r'^VERSION = "(\d+\.\d+\.\d+)"$', source, re.MULTILINE)
    if not match:
        raise RuntimeError("The connector version could not be determined.")
    return match.group(1)


def nsis_compiler() -> str:
    found = shutil.which("makensis")
    if found:
        return found
    candidates = (
        Path(r"C:\Program Files (x86)\NSIS\makensis.exe"),
        Path(r"C:\Program Files\NSIS\makensis.exe"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("NSIS makensis was not found.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="Remove prior installer output first.")
    args = parser.parse_args()

    if sys.platform != "win32":
        raise RuntimeError("The Windows installer must be built on Windows.")
    if not STANDALONE.is_file():
        raise RuntimeError("Build dist/standalone/pragmai.exe before the installer.")
    if args.clean:
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    version = connector_version()
    command = [
        nsis_compiler(),
        "/V4",
        f"/DAPP_VERSION={version}",
        f"/DAPP_EXE={STANDALONE.resolve()}",
        f"/DOUTPUT_DIR={DIST_DIR.resolve()}",
        str(NSIS_SCRIPT),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        return completed.returncode
    installer = DIST_DIR / OUTPUT_NAME
    if not installer.is_file():
        raise RuntimeError("The NSIS installer was not created.")
    print(installer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

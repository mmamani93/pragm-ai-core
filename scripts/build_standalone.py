#!/usr/bin/env python3
"""Build the PragmAI connector as a platform-native standalone executable."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONNECTOR = ROOT / "adapters" / "pragm_ai_connector.py"
SKILL_DIR = ROOT / "adapters" / "skills" / "pragm-ai-updater"
DIST_DIR = ROOT / "dist" / "standalone"
BUILD_DIR = ROOT / "build" / "standalone"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="Remove prior standalone output first.")
    args = parser.parse_args()

    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError(
            "PyInstaller is required only on the release machine. Install the build dependencies first."
        )
    if args.clean:
        shutil.rmtree(DIST_DIR, ignore_errors=True)
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "pragmai",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        "--add-data",
        f"{SKILL_DIR}:skills/pragm-ai-updater",
        "--collect-data",
        "certifi",
        str(CONNECTOR),
    ]
    environment = os.environ.copy()
    environment.setdefault("PYINSTALLER_CONFIG_DIR", str(BUILD_DIR / "cache"))
    completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    if completed.returncode:
        return completed.returncode
    executable = DIST_DIR / ("pragmai.exe" if sys.platform == "win32" else "pragmai")
    if not executable.is_file():
        raise RuntimeError("The standalone executable was not created.")
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Exercise the compiled NSIS installer and uninstaller on a Windows runner."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import time
import winreg


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "dist" / "installer" / "pragmai-windows-x64-setup.exe"
INSTALL_DIR = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "PragmAI"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PragmAI"


def connector_version() -> str:
    source = (ROOT / "adapters" / "pragm_ai_connector.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION = "(\d+\.\d+\.\d+)"$', source, re.MULTILINE)
    if not match:
        raise AssertionError("The connector version could not be determined")
    return match.group(1)


def user_path() -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            return winreg.QueryValueEx(key, "Path")[0]
        except FileNotFoundError:
            return ""


def set_user_path(value: str) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, value)


def normalized_path_entries(value: str) -> list[str]:
    return [
        os.path.normcase(os.path.normpath(os.path.expandvars(entry.strip())))
        for entry in value.split(";")
        if entry.strip()
    ]


def wait_until_removed(path: Path) -> None:
    for _ in range(50):
        if not path.exists():
            return
        time.sleep(0.1)
    raise AssertionError(f"Installer path was not removed: {path}")


def main() -> int:
    if sys.platform != "win32":
        return 0
    assert INSTALLER.is_file(), "The NSIS installer was not built"
    original_path = user_path()
    seeded_entries = ([original_path] if original_path else []) + [
        rf"C:\Synthetic\Path\{index:04d}" for index in range(300)
    ]
    seeded_path = ";".join(seeded_entries)
    try:
        set_user_path(seeded_path)
        subprocess.run([str(INSTALLER), "/S"], check=True, timeout=120)

        executable = INSTALL_DIR / "pragmai.exe"
        helper = INSTALL_DIR / "update_user_path.ps1"
        uninstaller = INSTALL_DIR / "Uninstall.exe"
        assert executable.is_file()
        assert helper.is_file()
        assert uninstaller.is_file()
        version = connector_version()
        reported = subprocess.run(
            [str(executable), "--version"], check=True, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        assert reported == version
        assert str(INSTALL_DIR).lower() in [part.lower() for part in user_path().split(";")]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            assert winreg.QueryValueEx(key, "DisplayVersion")[0] == version
            assert winreg.QueryValueEx(key, "InstallLocation")[0] == str(INSTALL_DIR)

        subprocess.run([str(uninstaller), "/S"], check=True, timeout=120)
        wait_until_removed(INSTALL_DIR)
        assert normalized_path_entries(user_path()) == normalized_path_entries(seeded_path)
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("The uninstall registry entry was retained")
    finally:
        set_user_path(original_path)
    print("Windows installer: install, version, PATH registration and uninstall passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

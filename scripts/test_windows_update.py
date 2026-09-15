"""Exercise the compiled Windows update helper in an isolated synthetic installation."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def main():
    if sys.platform != "win32":
        return 0
    built = Path('dist/standalone/pragmai.exe').resolve()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        user = root / 'User Space'
        (user / '.claude').mkdir(parents=True)
        local = user / 'AppData' / 'Local'
        env = {**os.environ, 'USERPROFILE': str(user), 'LOCALAPPDATA': str(local),
               'PYINSTALLER_RESET_ENVIRONMENT': '1'}
        setup = subprocess.run([str(built), 'setup', '--client', 'claude-code',
                                '--company-id', 'SyntheticTest', '--employee-email', 'test@example.com',
                                '--consent-confirmed', '--ingest-secret-stdin',
                                '--optimization-mode', 'always-on'],
                               input='synthetic-credential-not-a-real-secret\n', text=True,
                               env=env, capture_output=True, timeout=60)
        assert setup.returncode == 0, 'Synthetic setup failed'
        installed = local / 'PragmAI' / 'pragmai.exe'
        config = local / 'PragmAI' / 'config.json'
        before = json.loads(config.read_text())
        stage = root / 'New Release'
        stage.mkdir()
        helper = stage / 'pragmai.exe'
        shutil.copy2(built, helper)
        digest = hashlib.sha256(helper.read_bytes()).hexdigest()
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                       ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        # Permit reads (backup) but deny replacement until the simulated old process exits.
        handle = kernel.CreateFileW(str(installed), 0x80000000, 1, None, 3, 0, None)
        assert handle not in (None, ctypes.c_void_p(-1).value)
        child = None
        try:
            child = subprocess.Popen([str(helper), '_complete-update', '--target', str(installed),
                                      '--sha256', digest], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)
            assert child.poll() is None, 'Helper should wait for the locked executable'
        finally:
            kernel.CloseHandle(handle)
        stdout, stderr = child.communicate(timeout=120)
        assert child.returncode == 0, 'Update helper failed'
        after = json.loads(config.read_text())
        for key in ('company_id', 'employee_id', 'ingest_secret', 'fingerprint_key',
                    'optimization_mode', 'installed_clients'):
            assert before[key] == after[key], 'Installation identity or preferences changed'
        assert hashlib.sha256(installed.read_bytes()).hexdigest() == digest
        assert json.loads((local / 'PragmAI' / 'update-state.json').read_text())['status'] == 'complete'
        assert list(installed.parent.glob('pragmai.exe.pragm-ai-backup-*'))
        check = subprocess.run([str(installed), 'doctor'], env=env, capture_output=True, timeout=30)
        assert check.returncode == 0
        print('Windows frozen update: locked replacement, backup, identity preservation and doctor passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

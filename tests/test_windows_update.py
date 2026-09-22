import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('updater', Path(__file__).parents[1] / 'adapters/pragm_ai_connector.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def archive(name='pragmai.exe', data=b'MZsynthetic-binary'):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr(name, data)
    return stream.getvalue()


def asset(data):
    return {'name': 'pragmai-windows-x64.zip', 'browser_download_url': c.GITHUB_RELEASE_BASE + '0.7.20/pragmai-windows-x64.zip',
            'digest': 'sha256:' + hashlib.sha256(data).hexdigest(), 'size': len(data)}


class WindowsUpdateTests(unittest.TestCase):
    def test_github_requires_stable_tag_exact_asset_and_digest(self):
        good = {'tag_name': 'v0.7.20', 'draft': False, 'prerelease': False, 'assets': [asset(archive())]}
        with mock.patch.object(c, 'fetch_bytes', return_value=json.dumps(good).encode()):
            self.assertEqual(c.github_release_asset('0.7.20'), good['assets'][0])
        for bad in [dict(good, draft=True), dict(good, prerelease=True), dict(good, tag_name='v0.7.19'),
                    dict(good, assets=[]), dict(good, assets=good['assets'] * 2),
                    dict(good, assets=[dict(good['assets'][0], digest='')]),
                    dict(good, assets=[dict(good['assets'][0], browser_download_url='https://evil.example/file')])]:
            with mock.patch.object(c, 'fetch_bytes', return_value=json.dumps(bad).encode()), self.assertRaises(RuntimeError):
                c.github_release_asset('0.7.20')

    def test_missing_winget_or_unavailable_package_falls_back(self):
        data = archive()
        for binary, code in [(None, 0), ('winget', 0x8A150014), ('winget', -1978335209)]:
            with tempfile.TemporaryDirectory() as d, mock.patch.object(c.shutil, 'which', return_value=binary), \
                    mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], code)), \
                    mock.patch.object(c, 'fetch_bytes', return_value=data) as fetch:
                self.assertEqual(c.download_windows_archive('0.7.20', Path(d), asset(data)), data)
                fetch.assert_called_once()

    def test_winget_security_and_other_failures_do_not_fall_back(self):
        for code in [0x8A150011, 0x8A15001A, 0x8A150005, 0x8A150019, 1]:
            with tempfile.TemporaryDirectory() as d, mock.patch.object(c.shutil, 'which', return_value='winget'), \
                    mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], code)), \
                    mock.patch.object(c, 'fetch_bytes') as fetch, self.assertRaises(RuntimeError):
                c.download_windows_archive('0.7.20', Path(d), asset(archive()))
            fetch.assert_not_called()

    def test_winget_success_and_github_downloads_require_digest(self):
        data = archive()
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            (directory / 'download.zip').write_bytes(data)
            with mock.patch.object(c.shutil, 'which', return_value='winget'), \
                    mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                    mock.patch.object(c, 'fetch_bytes') as fetch:
                self.assertEqual(c.download_windows_archive('0.7.20', directory, asset(data)), data)
                fetch.assert_not_called()
                with self.assertRaises(RuntimeError):
                    c.download_windows_archive('0.7.20', directory, dict(asset(data), digest='sha256:' + '0' * 64))
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c.shutil, 'which', return_value=None), \
                mock.patch.object(c, 'fetch_bytes', return_value=b'bad'), self.assertRaises(RuntimeError):
            c.download_windows_archive('0.7.20', Path(d), asset(data))

    def test_archive_rejects_traversal_and_non_executables(self):
        for data in [archive('../pragmai.exe'), archive('other.exe'), archive(data=b'not executable')]:
            with tempfile.TemporaryDirectory() as d, self.assertRaises(RuntimeError):
                c.extract_windows_executable(data, Path(d))
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(c.extract_windows_executable(archive(), Path(d)).read_bytes(), b'MZsynthetic-binary')

    def test_handoff_checks_version_and_does_not_report_success_early(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c, 'load_config'), \
                mock.patch.object(c, 'fetch_update_manifest', return_value={'version': '0.7.20'}), \
                mock.patch.object(c, 'github_release_asset', return_value=asset(archive())), \
                mock.patch.object(c, 'download_windows_archive', return_value=archive()), \
                mock.patch.object(c.tempfile, 'mkdtemp', return_value=d), \
                mock.patch.object(c, 'record_update_state') as record, \
                mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='0.7.20\n')), \
                mock.patch.object(c.subprocess, 'Popen') as launch:
            self.assertEqual(c.windows_update(), 0)
            record.assert_called_once_with('pending', '0.7.20')
            self.assertEqual(launch.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')
            self.assertIn('_complete-update', launch.call_args.args[0])

    def test_wrong_executable_version_stops_before_handoff(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(c, 'load_config'), \
                mock.patch.object(c, 'fetch_update_manifest', return_value={'version': '0.7.20'}), \
                mock.patch.object(c, 'github_release_asset', return_value=asset(archive())), \
                mock.patch.object(c, 'download_windows_archive', return_value=archive()), \
                mock.patch.object(c.tempfile, 'mkdtemp', return_value=d), \
                mock.patch.object(c, 'record_update_state'), \
                mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='0.7.17')), \
                mock.patch.object(c.subprocess, 'Popen') as launch, self.assertRaises(RuntimeError):
            c.windows_update()
        launch.assert_not_called()

    def test_replacement_retries_locked_file_then_runs_repair_and_doctor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root / 'old' / 'pragmai.exe'
            old.parent.mkdir()
            old.write_bytes(b'old')
            staged = root / 'pragmai.exe'
            staged.write_bytes(b'new')
            write = c.atomic_write_bytes
            attempts = []
            def replace(path, data, mode):
                attempts.append(path)
                if len(attempts) == 1:
                    raise PermissionError()
                write(path, data, mode)
            with mock.patch.object(c, 'current_artifact_path', return_value=staged), \
                    mock.patch.object(c, 'atomic_write_bytes', side_effect=replace), \
                    mock.patch.object(c.time, 'sleep'), \
                    mock.patch.object(c, 'record_update_state') as state, \
                    mock.patch.object(c.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
                self.assertEqual(c.complete_windows_update(old, hashlib.sha256(b'new').hexdigest()), 0)
                self.assertEqual([call.args[0][1] for call in run.call_args_list], ['repair', 'doctor'])
                state.assert_called_once_with('complete', c.VERSION)
                self.assertEqual(old.read_bytes(), b'new')
                self.assertEqual(next(old.parent.glob('*.pragm-ai-backup-*')).read_bytes(), b'old')

    def test_failed_doctor_never_marks_update_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / 'pragmai.exe'
            target.write_bytes(b'old')
            source = root / 'new.exe'
            source.write_bytes(b'new')
            with mock.patch.object(c, 'current_artifact_path', return_value=source), \
                    mock.patch.object(c, 'record_update_state') as state, \
                    mock.patch.object(c.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1)]), \
                    self.assertRaises(RuntimeError):
                c.complete_windows_update(target, hashlib.sha256(b'new').hexdigest())
            state.assert_called_once_with('failed', c.VERSION)

    def test_downgrade_is_rejected_before_download(self):
        with mock.patch.object(c, 'load_config'), mock.patch.object(c, 'fetch_update_manifest', return_value={'version': '0.1.0'}), \
                mock.patch.object(c, 'github_release_asset') as download, self.assertRaises(RuntimeError):
            c.windows_update()
        download.assert_not_called()

    def test_redirects_cannot_leave_official_https_hosts(self):
        request = c.Request('https://github.com/mmamani93/pragm-ai-core')
        for url in ['http://github.com/file', 'https://evil.example/file', 'https://github.com@evil.example/file', 'https://github.com:8080/file']:
            with self.assertRaises(RuntimeError):
                c.GitHubReleaseRedirect().redirect_request(request, None, 302, '', {}, url)

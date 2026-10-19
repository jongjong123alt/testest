"""설치 실패 시 웹앱을 시작하지 않고, 준비된 환경을 재사용하는지 검사합니다."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.requirements = self.base / 'requirements.txt'
        self.requirements.write_text('Flask==3.1.2\n', encoding='utf-8')
        self.python = bootstrap.environment_python(self.base / '.venv')
        self.python.parent.mkdir(parents=True)
        self.python.touch()
        for mocked in (patch.object(bootstrap, '__file__', str(self.base / 'bootstrap.py')),
                       patch.object(bootstrap.sys, 'argv', ['app.py', '--original', '--port', '5001'])):
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_ready_environment_does_not_install_or_restart(self):
        with patch.object(bootstrap, 'dependencies_ready', return_value=True), \
             patch.object(bootstrap.subprocess, 'run') as run, \
             patch.object(bootstrap.os, 'execv') as restart:
            bootstrap.ensure_dependencies()
        run.assert_not_called()
        restart.assert_not_called()

    def test_reuse_local_environment_preserves_arguments(self):
        with patch.object(bootstrap, 'dependencies_ready', return_value=False), \
             patch.object(bootstrap.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run, \
             patch.object(bootstrap.os, 'execv') as restart, contextlib.redirect_stdout(io.StringIO()):
            bootstrap.ensure_dependencies()
        self.assertEqual(run.call_count, 1)  # 상태 확인만 실행하고 pip는 호출하지 않습니다.
        restart.assert_called_once_with(str(self.python),
            [str(self.python), str(self.base / 'app.py'), '--original', '--port', '5001'])

    def test_install_failure_stops_before_restart(self):
        results = [subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0),
                   subprocess.CalledProcessError(1, ['pip', 'install'])]
        error = io.StringIO()
        with patch.object(bootstrap, 'dependencies_ready', return_value=False), \
             patch.object(bootstrap.subprocess, 'run', side_effect=results), \
             patch.object(bootstrap.os, 'execv') as restart, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as caught:
                bootstrap.ensure_dependencies()
        self.assertEqual(caught.exception.code, 1)
        self.assertIn('인터넷 연결', error.getvalue())
        restart.assert_not_called()

    def test_missing_pip_uses_ensurepip_and_pinned_requirements(self):
        results = [subprocess.CompletedProcess([], n) for n in (1, 1, 0, 0, 0)]
        with patch.object(bootstrap, 'dependencies_ready', return_value=False), \
             patch.object(bootstrap.subprocess, 'run', side_effect=results) as run, \
             patch.object(bootstrap.os, 'execv') as restart, contextlib.redirect_stdout(io.StringIO()):
            bootstrap.ensure_dependencies()
        self.assertEqual(run.call_args_list[2].args[0],
                         [str(self.python), '-m', 'ensurepip', '--upgrade'])
        install = run.call_args_list[3].args[0]
        self.assertEqual(install[:4], [str(self.python), '-m', 'pip', 'install'])
        self.assertEqual(install[-2:], ['-r', str(self.requirements)])
        restart.assert_called_once()

    def test_version_mismatch_requires_install(self):
        with patch.object(bootstrap.metadata, 'version', return_value='3.0.0'):
            self.assertFalse(bootstrap.dependencies_ready(self.requirements))

    def test_broken_import_requires_install(self):
        with patch.object(bootstrap.metadata, 'version', return_value='3.1.2'), \
             patch.object(bootstrap.importlib, 'import_module', side_effect=ImportError('broken')):
            self.assertFalse(bootstrap.dependencies_ready(self.requirements))

    def test_missing_requirements_explains_incomplete_extraction(self):
        self.requirements.unlink()
        with self.assertRaisesRegex(SystemExit, 'ZIP 전체'):
            bootstrap.ensure_dependencies()


if __name__ == '__main__':
    unittest.main()

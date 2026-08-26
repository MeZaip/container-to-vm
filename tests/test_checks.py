import unittest
from unittest.mock import patch

from container2vm.checks import collect_checks


class CollectChecksTests(unittest.TestCase):
    @patch("container2vm.checks.docker_daemon_available", return_value=True)
    @patch("container2vm.checks.shutil.which", return_value="/usr/bin/tool")
    @patch("container2vm.checks.running_as_root", return_value=True)
    @patch("container2vm.checks.platform.system", return_value="Linux")
    def test_reports_a_ready_linux_host(
        self,
        _platform_system,
        _running_as_root,
        _which,
        _docker_daemon_available,
    ):
        results = collect_checks()

        self.assertTrue(all(result.ok for result in results))
        self.assertEqual(results[0].detail, "Linux")
        self.assertEqual(results[1].detail, "running as root")

    @patch("container2vm.checks.docker_daemon_available", return_value=False)
    @patch("container2vm.checks.shutil.which", return_value=None)
    @patch("container2vm.checks.running_as_root", return_value=False)
    @patch("container2vm.checks.platform.system", return_value="Windows")
    def test_reports_missing_requirements(
        self,
        _platform_system,
        _running_as_root,
        _which,
        _docker_daemon_available,
    ):
        results = collect_checks()

        self.assertFalse(all(result.ok for result in results))
        self.assertEqual(results[0].detail, "Windows")
        self.assertEqual(results[1].detail, "run with sudo")
        self.assertNotIn("Docker daemon", [result.name for result in results])

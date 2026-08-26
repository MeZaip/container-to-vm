import sys
import unittest
from unittest.mock import patch

from container2vm.cli import main


class CheckCommandTests(unittest.TestCase):
    def test_check_fails(self):
        with (
            patch.object(sys, "argv", ["container2vm", "check"]),
            patch("container2vm.cli.run_environment_check", return_value=False),
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 1)

    def test_check_succeeds(self):
        with (
            patch.object(sys, "argv", ["container2vm", "check"]),
            patch("container2vm.cli.run_environment_check", return_value=True),
        ):
            main()

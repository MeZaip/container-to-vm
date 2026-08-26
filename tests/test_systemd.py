import unittest
from unittest.mock import MagicMock, patch

from container2vm.models import ContainerConfig
from container2vm.systemd import (
    install_container_service,
    resolve_executable,
)


class ContainerServiceTests(unittest.TestCase):
    def test_resolves_entrypoint_from_the_image_path(self):
        container_root = MagicMock()
        candidate = container_root / "usr/local/bin" / "docker-entrypoint.sh"
        candidate.is_file.return_value = True

        executable = resolve_executable(
            container_root,
            "docker-entrypoint.sh",
            ContainerConfig(env={"PATH": "/usr/local/bin:/usr/bin"}),
        )

        self.assertEqual(executable, "/usr/local/bin/docker-entrypoint.sh")

    def test_uses_container_root_for_the_working_directory(self):
        rootfs = MagicMock()
        service_dir = MagicMock()
        service_file = MagicMock()

        rootfs.__truediv__.side_effect = lambda path: {
            "etc/systemd/system": service_dir,
            "var/log/container": MagicMock(),
            "opt/container": MagicMock(),
        }[path]
        service_dir.__truediv__.return_value = service_file

        with (
            patch(
                "container2vm.systemd.resolve_executable",
                return_value="/usr/local/bin/docker-entrypoint.sh",
            ),
            patch("container2vm.systemd.enable_service"),
        ):
            install_container_service(
                rootfs,
                ContainerConfig(
                    entrypoint=["docker-entrypoint.sh"],
                    cmd=["redis-server"],
                    working_dir="/data",
                ),
            )

        service = service_file.write_text.call_args.args[0]

        self.assertIn("RootDirectory=/opt/container", service)
        self.assertIn("WorkingDirectory=/data", service)
        self.assertIn(
            "ExecStart=/usr/local/bin/docker-entrypoint.sh redis-server",
            service,
        )

    def test_rejects_a_container_without_a_command(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "Container has no entrypoint or command",
        ):
            install_container_service(MagicMock(), ContainerConfig())

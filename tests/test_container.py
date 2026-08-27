import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from container2vm.container import (
    extract_container_or_image,
    inspect_container_or_image,
)


class InspectContainerOrImageTests(unittest.TestCase):
    @patch("container2vm.container.subprocess.run")
    def test_prefers_container_metadata_when_container_exists(self, mock_run):
        container_inspect = MagicMock(
            returncode=0,
            stdout='[{"Id":"cid","Path":"redis-server","Args":["--appendonly","yes"],'
            '"Config":{"Image":"redis:7","Env":["A=B"],"WorkingDir":"/data","User":"1000"},'
            '"Mounts":[{"Destination":"/data"}]}]',
        )
        image_inspect = MagicMock(
            returncode=0,
            stdout='[{"Id":"imgid","Architecture":"amd64","Os":"linux","Size":123}]',
        )
        mock_run.side_effect = [container_inspect, image_inspect]

        info = inspect_container_or_image("redis-live")

        self.assertEqual(info.image, "redis-live")
        self.assertEqual(info.image_id, "imgid")
        self.assertEqual(info.config.entrypoint, ["redis-server"])
        self.assertEqual(info.config.cmd, ["--appendonly", "yes"])
        self.assertEqual(info.config.env["A"], "B")
        self.assertIn("/data", info.config.volumes)

    @patch("container2vm.container.subprocess.run")
    def test_falls_back_to_image_command_when_container_has_only_it_flags(self, mock_run):
        container_inspect = MagicMock(
            returncode=0,
            stdout='[{"Id":"cid","Path":"docker-entrypoint.sh","Args":["-it"],'
            '"Config":{"Image":"nginx:latest","Env":["A=B"],"WorkingDir":"/","User":"root"}}]',
        )
        image_inspect = MagicMock(
            returncode=0,
            stdout='[{"Id":"imgid","Architecture":"amd64","Os":"linux","Size":123,'
            '"Config":{"Entrypoint":["/docker-entrypoint.sh"],'
            '"Cmd":["nginx","-g","daemon off;"]}}]',
        )
        mock_run.side_effect = [container_inspect, image_inspect]

        info = inspect_container_or_image("nginx-live")

        self.assertEqual(info.config.entrypoint, ["/docker-entrypoint.sh"])
        self.assertEqual(info.config.cmd, ["nginx", "-g", "daemon off;"])


class ExtractContainerOrImageTests(unittest.TestCase):
    @patch("container2vm.container._copy_container_mounts")
    @patch("container2vm.container._extract_exported_rootfs")
    @patch("container2vm.container._resolve_reference")
    def test_extracts_running_container_with_mount_copy(
        self,
        mock_resolve,
        mock_extract_rootfs,
        mock_copy_mounts,
    ):
        mock_resolve.return_value = (
            "container",
            {
                "Id": "container-id",
                "Mounts": [{"Destination": "/data"}],
            },
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            extract_container_or_image("redis-live", Path(temp_dir))

        mock_extract_rootfs.assert_called_once()
        mock_copy_mounts.assert_called_once()

    @patch("container2vm.container._extract_exported_rootfs")
    @patch("container2vm.container._resolve_reference")
    @patch("container2vm.container.subprocess.run")
    def test_extracts_image_via_temp_container(
        self,
        mock_run,
        mock_resolve,
        mock_extract_rootfs,
    ):
        mock_resolve.return_value = ("image", {"Id": "imgid"})
        mock_run.side_effect = [
            MagicMock(stdout="tmp-container\n"),
            MagicMock(),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            extract_container_or_image("redis:7", Path(temp_dir))

        self.assertEqual(mock_run.call_args_list[0].args[0], ["docker", "create", "redis:7"])
        self.assertEqual(mock_run.call_args_list[-1].args[0][:2], ["docker", "rm"])
        mock_extract_rootfs.assert_called_once_with("tmp-container", Path(temp_dir))

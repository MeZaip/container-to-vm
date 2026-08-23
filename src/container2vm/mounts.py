from contextlib import contextmanager
from pathlib import Path
import subprocess


CONTAINER_ROOT = Path("/opt/container")


@contextmanager
def mounted_rootfs(rootfs: Path):
    mounts = [
        ("/dev", rootfs / "dev", "bind"),
        ("/dev/pts", rootfs / "dev/pts", "bind"),
        ("proc", rootfs / "proc", "proc"),
        ("sysfs", rootfs / "sys", "sysfs"),
    ]

    mounted = []

    try:
        for source, target, filesystem in mounts:
            target.mkdir(parents=True, exist_ok=True)

            if filesystem == "bind":
                subprocess.run(
                    ["mount", "--bind", source, str(target)],
                    check=True,
                )
            else:
                subprocess.run(
                    [
                        "mount",
                        "-t",
                        filesystem,
                        filesystem,
                        str(target),
                    ],
                    check=True,
                )

            mounted.append(target)

        yield rootfs

    finally:
        for target in reversed(mounted):
            subprocess.run(
                ["umount", str(target)],
                check=False,
            )


def configure_container_mounts(rootfs: Path) -> None:
    service_dir = rootfs / "etc/systemd/system"
    service_dir.mkdir(parents=True, exist_ok=True)

    service = service_dir / "container-mounts.service"
    service.write_text(
        """[Unit]
Description=Container filesystem mounts
Before=container.service
After=local-fs.target

[Service]
Type=oneshot
ExecStartPre=/bin/mkdir -p /opt/container/dev
ExecStart=/bin/mount --rbind /dev /opt/container/dev
ExecStartPre=/bin/mkdir -p /opt/container/proc
ExecStart=/bin/mount -t proc proc /opt/container/proc
ExecStartPre=/bin/mkdir -p /opt/container/sys
ExecStart=/bin/mount -t sysfs sysfs /opt/container/sys
ExecStartPre=/bin/mkdir -p /opt/container/run
ExecStart=/bin/mount --bind /run /opt/container/run
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""",
        encoding="utf-8",
    )

    wants_dir = (
        rootfs
        / "etc/systemd/system/multi-user.target.wants"
    )
    wants_dir.mkdir(parents=True, exist_ok=True)

    target = wants_dir / "container-mounts.service"

    if target.exists() or target.is_symlink():
        target.unlink()

    target.symlink_to(
        "/etc/systemd/system/container-mounts.service"
    )
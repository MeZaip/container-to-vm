from pathlib import Path
import subprocess

from .application import install_container
from .models import VMConfig

DEBIAN_RELEASE = "bookworm"
DEBIAN_MIRROR = "http://deb.debian.org/debian"

def install_packages(rootfs: Path) -> None:
    mounts = [
        ("/dev", rootfs / "dev", "--bind"),
        ("/dev/pts", rootfs / "dev/pts", "--bind"),
        ("/proc", rootfs / "proc", "-t proc"),
        ("/sys", rootfs / "sys", "-t sysfs"),
    ]

    mounted = []

    try:
        for source, target, option in mounts:
            target.mkdir(parents=True, exist_ok=True)

            if option.startswith("-t"):
                filesystem = option.split()[1]
                subprocess.run(
                    ["mount", "-t", filesystem, source, str(target)],
                    check=True,
                )
            else:
                subprocess.run(
                    ["mount", "--bind", source, str(target)],
                    check=True,
                )

            mounted.append(target)

        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "update",
            ],
            check=True,
        )

        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "install",
                "-y",
                "linux-image-amd64",
                "systemd",
                "systemd-sysv",
                "iproute2",
            ],
            check=True,
        )

    finally:
        for target in reversed(mounted):
            subprocess.run(
                ["umount", str(target)],
                check=False,
            )

def create_user(rootfs: Path, config: VMConfig) -> None:
    if not config.username:
        return

    subprocess.run(
        [
            "chroot",
            str(rootfs),
            "useradd",
            "-m",
            "-s",
            "/bin/bash",
            config.username,
        ],
        check=True,
    )

    if config.password is not None:
        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "chpasswd",
            ],
            input=f"{config.username}:{config.password}\n",
            text=True,
            check=True,
        )

def configure_system(
    rootfs: Path,
    config: VMConfig,
) -> None:
    (rootfs / "etc/hostname").write_text(
        f"{config.hostname}\n",
        encoding="utf-8",
    )

    (rootfs / "etc/hosts").write_text(
        "127.0.0.1 localhost\n"
        f"127.0.1.1 {config.hostname}\n",
        encoding="utf-8",
    )

    create_user(rootfs, config)


def create_rootfs(output_dir: Path) -> None:
    output_dir = output_dir.resolve()

    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(
            f"Output directory is not empty: {output_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "debootstrap",
        "--arch=amd64",
        "--variant=minbase",
        DEBIAN_RELEASE,
        str(output_dir),
        DEBIAN_MIRROR,
    ]

    subprocess.run(command, check=True)


def build_rootfs(
    output_dir: Path,
    vm_config: VMConfig | None = None,
) -> None:
    if vm_config is None:
        vm_config = VMConfig()

    create_rootfs(output_dir)
    install_packages(output_dir)
    configure_system(output_dir, vm_config)

def build_base_rootfs(
    output_dir: Path,
    vm_config: VMConfig | None = None,
) -> None:
    output_dir = output_dir.resolve()

    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(
            f"Output directory is not empty: {output_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    build_rootfs(output_dir, vm_config)

def build_final_rootfs(
    container_rootfs: Path,
    output_rootfs: Path,
    config,
    vm_config: VMConfig | None = None,
) -> None:
    build_rootfs(output_rootfs, vm_config)

    install_container(
        container_rootfs,
        output_rootfs,
        config,
    )
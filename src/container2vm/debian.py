from pathlib import Path
import subprocess

from .application import install_container
from .models import VMConfig, ContainerConfig
from .systemd import install_container_service
from .mounts import configure_container_mounts, mounted_rootfs

DEBIAN_RELEASE = "bookworm"
DEBIAN_MIRROR = "http://deb.debian.org/debian"

def install_packages(rootfs: Path) -> None:
    with mounted_rootfs(rootfs):
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
                "grub-pc",
                "systemd",
                "systemd-sysv",
                "iproute2",
                "sudo",
            ],
            check=True,
        )

def create_user(rootfs: Path, config: VMConfig) -> None:
    subprocess.run(
        [
            "chroot",
            str(rootfs),
            "useradd",
            "-m",
            "-s",
            "/bin/bash",
            "-G",
            "sudo",
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

    network_dir = rootfs / "etc/systemd/network"
    network_dir.mkdir(parents=True, exist_ok=True)

    (network_dir / "20-ens3.network").write_text(
        "[Match]\n"
        "Name=ens3\n\n"
        "[Network]\n"
        "DHCP=yes\n",
        encoding="utf-8",
    )

    network_target = (
        rootfs
        / "etc/systemd/system/multi-user.target.wants/systemd-networkd.service"
    )

    network_target.parent.mkdir(parents=True, exist_ok=True)

    network_service = (
        rootfs / "lib/systemd/system/systemd-networkd.service"
    )

    if not network_service.exists():
        raise RuntimeError(
            "systemd-networkd.service not found in rootfs."
        )

    network_target.symlink_to(
        "/lib/systemd/system/systemd-networkd.service"
    )

    grub_config = rootfs / "etc/default/grub"

    grub_config.write_text(
        'GRUB_DEFAULT=0\n'
        'GRUB_TIMEOUT=0\n'
        'GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"\n',
        encoding="utf-8",
    )

    with mounted_rootfs(rootfs):
        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "update-grub",
            ],
            check=True,
        )

    serial_getty = (
        rootfs
        / "etc/systemd/system/getty.target.wants/serial-getty@ttyS0.service"
    )

    serial_getty.parent.mkdir(parents=True, exist_ok=True)

    serial_getty.symlink_to(
        "/lib/systemd/system/serial-getty@.service"
    )

    configure_container_mounts(rootfs)
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
    config: ContainerConfig,
    vm_config: VMConfig,
) -> None:
    build_rootfs(output_rootfs, vm_config)

    install_container(
        container_rootfs,
        output_rootfs,
        config,
    )

    install_container_service(
        output_rootfs,
        config,
    )
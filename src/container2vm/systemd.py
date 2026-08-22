from pathlib import Path
import shlex

from .models import ContainerConfig


def install_container_service(
    rootfs: Path,
    config: ContainerConfig,
) -> None:
    service_dir = rootfs / "etc/systemd/system"
    service_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "/usr/sbin/chroot",
        "/opt/container",
        *config.entrypoint,
        *config.cmd,
    ]

    exec_start = " ".join(shlex.quote(value) for value in command)

    lines = [
        "[Unit]",
        "Description=Containerized application",
        "After=network-online.target serial-getty@ttyS0.service",
        "Wants=network-online.target",
        "Conflicts=serial-getty@ttyS0.service",
        "",
        "[Service]",
        "Type=simple",
        f"ExecStart={exec_start}",
        "StandardInput=tty",
        "StandardOutput=tty",
        "StandardError=tty",
        "TTYPath=/dev/ttyS0",
        "TTYReset=yes",
        "TTYVHangup=yes",
        "Restart=always",
    ]

    if config.working_dir:
        lines.append(
            f"WorkingDirectory={config.working_dir}"
        )

    for key, value in config.env.items():
        lines.append(
            f"Environment={shlex.quote(f'{key}={value}')}"
        )

    lines.extend([
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])

    service_file = service_dir / "container.service"

    service_file.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    enable_service(rootfs)


def enable_service(rootfs: Path) -> None:
    wants_dir = (
        rootfs
        / "etc/systemd/system/multi-user.target.wants"
    )

    wants_dir.mkdir(parents=True, exist_ok=True)

    service_file = (
        rootfs
        / "etc/systemd/system/container.service"
    )

    symlink = wants_dir / "container.service"

    if symlink.exists() or symlink.is_symlink():
        symlink.unlink()

    symlink.symlink_to(
        service_file
    )
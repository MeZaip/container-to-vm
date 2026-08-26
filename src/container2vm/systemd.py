import posixpath
from pathlib import Path
import shlex

from .models import ContainerConfig


CONTAINER_ROOT = "/opt/container"
DEFAULT_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def normalize_container_path(path: str, working_dir: str = "/") -> str:
    if not path.startswith("/"):
        path = posixpath.join(working_dir, path)

    normalized = posixpath.normpath(path)

    return normalized if normalized.startswith("/") else f"/{normalized}"


def resolve_executable(
    container_root: Path,
    executable: str,
    config: ContainerConfig,
) -> str:
    working_dir = normalize_container_path(config.working_dir or "/")

    if executable.startswith("/"):
        return normalize_container_path(executable)

    if "/" in executable:
        return normalize_container_path(executable, working_dir)

    search_path = config.env.get("PATH", DEFAULT_PATH)

    for directory in search_path.split(":"):
        executable_path = normalize_container_path(directory or "/")
        candidate = container_root / executable_path.lstrip("/") / executable

        if candidate.is_file():
            return f"{executable_path.rstrip('/')}/{executable}"

    raise RuntimeError(
        f"Container executable not found in image PATH: {executable}"
    )


def install_container_service(
    rootfs: Path,
    config: ContainerConfig,
) -> None:
    command = [*config.entrypoint, *config.cmd]

    if not command:
        raise RuntimeError("Container has no entrypoint or command.")

    service_dir = rootfs / "etc/systemd/system"
    service_dir.mkdir(parents=True, exist_ok=True)

    (rootfs / "var/log/container").mkdir(parents=True, exist_ok=True)

    container_root = rootfs / CONTAINER_ROOT.lstrip("/")
    command[0] = resolve_executable(container_root, command[0], config)

    exec_start = " ".join(shlex.quote(value) for value in command)

    lines = [
        "[Unit]",
        "Description=Containerized application",
        "After=network-online.target container-mounts.service",
        "Wants=network-online.target",
        "Requires=container-mounts.service",
        "",
        "[Service]",
        "Type=simple",
        f"RootDirectory={CONTAINER_ROOT}",
        f"ExecStart={exec_start}",
        "StandardInput=null",
        "StandardOutput=append:/var/log/container/stdout.log",
        "StandardError=append:/var/log/container/stderr.log",
        "Restart=always",
    ]

    if config.working_dir:
        lines.append(
            f"WorkingDirectory={normalize_container_path(config.working_dir)}"
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

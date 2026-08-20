import shutil
from pathlib import Path

from .models import ContainerConfig
from .service import generate_systemd_service


def enable_container_service(vm_rootfs: Path) -> None:
    wants_dir = (
        vm_rootfs
        / "etc"
        / "systemd"
        / "system"
        / "multi-user.target.wants"
    )

    wants_dir.mkdir(parents=True, exist_ok=True)

    link_path = wants_dir / "container-app.service"

    if link_path.exists():
        link_path.unlink()

    link_path.symlink_to(
        "../container-app.service"
    )


def install_container(
    container_rootfs: Path,
    vm_rootfs: Path,
    config: ContainerConfig,
) -> None:
    application_root = vm_rootfs / "opt" / "container"

    if application_root.exists():
        raise RuntimeError(
            f"Application directory already exists: {application_root}"
        )

    shutil.copytree(
        container_rootfs,
        application_root,
        symlinks=True,
    )

    service_path = (
        vm_rootfs
        / "etc"
        / "systemd"
        / "system"
        / "container-app.service"
    )

    generate_systemd_service(
        config,
        service_path,
    )

    enable_container_service(vm_rootfs)
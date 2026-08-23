import shutil
from pathlib import Path

from .models import ContainerConfig

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

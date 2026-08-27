import json
import posixpath
import subprocess
import tarfile
from pathlib import Path

from .models import ContainerConfig, ContainerInfo


def _parse_environment(config: dict) -> dict[str, str]:
    environment = {}

    for variable in config.get("Env") or []:
        key, separator, value = variable.partition("=")

        if separator:
            environment[key] = value

    return environment


def _inspect(entity_type: str, reference: str) -> dict | None:
    result = subprocess.run(
        ["docker", entity_type, "inspect", reference],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    data = json.loads(result.stdout or "[]")

    if not data:
        return None

    return data[0]


def _resolve_reference(reference: str) -> tuple[str, dict]:
    container_data = _inspect("container", reference)

    if container_data is not None:
        return "container", container_data

    image_data = _inspect("image", reference)

    if image_data is not None:
        return "image", image_data

    raise RuntimeError(
        f"Could not find a Docker image or container named '{reference}'."
    )


def inspect_container_or_image(reference: str) -> ContainerInfo:
    reference_type, data = _resolve_reference(reference)
    config = data.get("Config", {})

    entrypoint = config.get("Entrypoint") or []
    cmd = config.get("Cmd") or []

    if reference_type == "container" and data.get("Path"):
        entrypoint = [data["Path"]]
        cmd = data.get("Args") or []

    volume_paths = set((config.get("Volumes") or {}).keys())

    if reference_type == "container":
        for mount in data.get("Mounts") or []:
            destination = mount.get("Destination")

            if destination:
                volume_paths.add(destination)

    image_data = data

    if reference_type == "container":
        image_reference = config.get("Image") or data.get("Image")
        inspected_image = _inspect("image", image_reference or "")

        if inspected_image is not None:
            image_data = inspected_image

    container_config = ContainerConfig(
        entrypoint=entrypoint,
        cmd=cmd,
        env=_parse_environment(config),
        working_dir=config.get("WorkingDir") or "",
        user=config.get("User") or "",
        volumes=sorted(volume_paths),
        exposed_ports=list((config.get("ExposedPorts") or {}).keys()),
    )

    return ContainerInfo(
        image=reference,
        image_id=image_data.get("Id", ""),
        architecture=image_data.get("Architecture", ""),
        os=image_data.get("Os", ""),
        size=image_data.get("Size", 0),
        config=container_config,
    )


def _extract_exported_rootfs(container_id: str, output_dir: Path) -> None:
    archive_path = output_dir / "rootfs.tar"

    with archive_path.open("wb") as archive:
        subprocess.run(
            ["docker", "export", container_id],
            stdout=archive,
            check=True,
        )

    with tarfile.open(archive_path) as tar:
        tar.extractall(output_dir)

    archive_path.unlink()


def _copy_container_mounts(container_id: str, output_dir: Path, mounts: list[dict]) -> None:
    root = output_dir.resolve()

    for mount in mounts:
        destination = mount.get("Destination")

        if not destination:
            continue

        normalized = posixpath.normpath(destination)

        if not normalized.startswith("/"):
            continue

        relative_destination = normalized.lstrip("/")
        host_destination = (root / relative_destination).resolve()

        if host_destination != root and root not in host_destination.parents:
            continue

        host_destination.parent.mkdir(parents=True, exist_ok=True)

        copy_result = subprocess.run(
            ["docker", "cp", f"{container_id}:{normalized}/.", str(host_destination)],
            capture_output=True,
            text=True,
            check=False,
        )

        if copy_result.returncode == 0:
            continue

        subprocess.run(
            ["docker", "cp", f"{container_id}:{normalized}", str(host_destination.parent)],
            check=True,
        )


def extract_container_or_image(reference: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_type, data = _resolve_reference(reference)

    if reference_type == "container":
        container_id = data.get("Id") or reference
        _extract_exported_rootfs(container_id, output_dir)
        _copy_container_mounts(container_id, output_dir, data.get("Mounts") or [])
        return

    create_result = subprocess.run(["docker", "create", reference], capture_output=True, text=True, check=True)

    container_id = create_result.stdout.strip()

    if not container_id:
        raise RuntimeError("Docker did not return a container ID.")

    try:
        _extract_exported_rootfs(container_id, output_dir)

    finally:
        subprocess.run(
            ["docker", "rm", container_id],
            capture_output=True,
            check=False,
        )


def inspect_image(image: str) -> ContainerInfo:
    return inspect_container_or_image(image)


def extract_image(image: str, output_dir: Path) -> None:
    extract_container_or_image(image, output_dir)
import json
import subprocess

from .models import ContainerConfig, ContainerInfo


def inspect_image(image: str) -> ContainerInfo:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    if not data:
        raise RuntimeError(f"No information returned for image: {image}")

    image_data = data[0]
    config = image_data.get("Config", {})

    environment = {}

    for variable in config.get("Env") or []:
        key, separator, value = variable.partition("=")

        if separator:
            environment[key] = value

    container_config = ContainerConfig(
        entrypoint=config.get("Entrypoint") or [],
        cmd=config.get("Cmd") or [],
        env=environment,
        working_dir=config.get("WorkingDir") or "",
        user=config.get("User") or "",
        volumes=list((config.get("Volumes") or {}).keys()),
        exposed_ports=list((config.get("ExposedPorts") or {}).keys()),
    )

    return ContainerInfo(
        image=image,
        image_id=image_data["Id"],
        architecture=image_data.get("Architecture", ""),
        os=image_data.get("Os", ""),
        size=image_data.get("Size", 0),
        config=container_config,
    )
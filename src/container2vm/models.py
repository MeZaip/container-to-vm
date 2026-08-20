from dataclasses import dataclass, field


@dataclass
class VMConfig:
    hostname: str = "container-vm"
    username: str | None = None
    password: str | None = None


@dataclass
class ContainerConfig:
    entrypoint: list[str] = field(default_factory=list)
    cmd: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    working_dir: str = ""
    user: str = ""
    volumes: list[str] = field(default_factory=list)
    exposed_ports: list[str] = field(default_factory=list)


@dataclass
class ContainerInfo:
    image: str
    image_id: str
    architecture: str
    os: str
    size: int
    config: ContainerConfig
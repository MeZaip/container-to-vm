from dataclasses import dataclass, field


@dataclass
class VMConfig:
    hostname: str = "container-vm"
    username: str = "user"
    password: str | None = None
    memory_mb: int = 1024
    cpus: int = 1
    disk_size: str = "4G"


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
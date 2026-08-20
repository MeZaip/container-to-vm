from pathlib import Path

from .models import ContainerConfig


def build_command(config: ContainerConfig) -> str:
    command = config.entrypoint + config.cmd

    if not command:
        raise ValueError("Container has no entrypoint or command.")

    return " ".join(_quote_argument(argument) for argument in command)


def _quote_argument(argument: str) -> str:
    if not argument:
        return '""'

    if any(character in argument for character in ' \t"\\'):
        escaped = argument.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    return argument


def generate_systemd_service(
    config: ContainerConfig,
    output: Path,
    application_root: str = "/opt/container",
) -> None:
    command = build_command(config)

    lines = [
        "[Unit]",
        "Description=Containerized application",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
        "RootDirectory=/opt/container",
        f"ExecStart={command}",
        "Restart=always",
    ]

    if config.working_dir:
        working_dir = config.working_dir

        if not working_dir.startswith("/"):
            working_dir = f"{application_root}/{working_dir}"

        lines.append(f"WorkingDirectory={working_dir}")

    for key, value in config.env.items():
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'Environment="{key}={escaped_value}"')

    lines.extend(
        [
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
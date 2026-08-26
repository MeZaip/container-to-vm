from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import shutil
import subprocess


REQUIRED_COMMANDS = (
    "docker",
    "debootstrap",
    "qemu-img",
    "parted",
    "losetup",
    "mkfs.ext4",
    "grub-install",
    "mount",
    "umount",
    "chroot",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def running_as_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return geteuid is not None and geteuid() == 0


def docker_daemon_available() -> bool:
    result = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def collect_checks() -> list[CheckResult]:
    is_root = running_as_root()

    results = [
        CheckResult(
            name="Platform",
            ok=platform.system() == "Linux",
            detail=platform.system(),
        ),
        CheckResult(
            name="Privileges",
            ok=is_root,
            detail="running as root" if is_root else "run with sudo",
        ),
    ]

    available_commands = set()

    for command in REQUIRED_COMMANDS:
        path = shutil.which(command)
        if path:
            available_commands.add(command)
        results.append(
            CheckResult(
                name=command,
                ok=path is not None,
                detail=path or "not found",
            )
        )

    if "docker" in available_commands:
        try:
            daemon_available = docker_daemon_available()
        except OSError:
            daemon_available = False

        results.append(
            CheckResult(
                name="Docker daemon",
                ok=daemon_available,
                detail="available" if daemon_available else "not reachable",
            )
        )

    return results


def run_environment_check() -> bool:
    print("Container2VM environment check")

    results = collect_checks()

    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    ready = all(result.ok for result in results)

    if ready:
        print("\nEnvironment is ready for conversion.")
    else:
        print("\nEnvironment is not ready for conversion.")

    return ready

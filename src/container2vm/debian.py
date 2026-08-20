from pathlib import Path
import subprocess


DEBIAN_RELEASE = "bookworm"
DEBIAN_MIRROR = "http://deb.debian.org/debian"

def install_packages(rootfs: Path) -> None:
    mounts = [
        ("/dev", rootfs / "dev", "--bind"),
        ("/dev/pts", rootfs / "dev/pts", "--bind"),
        ("/proc", rootfs / "proc", "-t proc"),
        ("/sys", rootfs / "sys", "-t sysfs"),
    ]

    mounted = []

    try:
        for source, target, option in mounts:
            target.mkdir(parents=True, exist_ok=True)

            if option.startswith("-t"):
                filesystem = option.split()[1]
                subprocess.run(
                    ["mount", "-t", filesystem, source, str(target)],
                    check=True,
                )
            else:
                subprocess.run(
                    ["mount", "--bind", source, str(target)],
                    check=True,
                )

            mounted.append(target)

        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "update",
            ],
            check=True,
        )

        subprocess.run(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "install",
                "-y",
                "linux-image-amd64",
                "systemd",
                "systemd-sysv",
                "iproute2",
            ],
            check=True,
        )

    finally:
        for target in reversed(mounted):
            subprocess.run(
                ["umount", str(target)],
                check=False,
            )

def configure_system(rootfs: Path) -> None:
    (rootfs / "etc/hostname").write_text(
        "container-vm\n",
        encoding="utf-8",
    )

    (rootfs / "etc/hosts").write_text(
        "127.0.0.1 localhost\n"
        "127.0.1.1 container-vm\n",
        encoding="utf-8",
    )


def create_rootfs(output_dir: Path) -> None:
    output_dir = output_dir.resolve()

    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(
            f"Output directory is not empty: {output_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "debootstrap",
        "--arch=amd64",
        "--variant=minbase",
        DEBIAN_RELEASE,
        str(output_dir),
        DEBIAN_MIRROR,
    ]

    subprocess.run(command, check=True)

def build_rootfs(output_dir: Path) -> None:
    create_rootfs(output_dir)
    install_packages(output_dir)
    configure_system(output_dir)
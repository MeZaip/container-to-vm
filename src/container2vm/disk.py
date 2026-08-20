from pathlib import Path
import shutil
import subprocess


def create_raw_image(output: Path, size: str = "4G") -> None:
    subprocess.run(
        [
            "qemu-img",
            "create",
            "-f",
            "raw",
            str(output),
            size,
        ],
        check=True,
    )


def format_ext4(image: Path) -> None:
    subprocess.run(
        [
            "mkfs.ext4",
            "-F",
            str(image),
        ],
        check=True,
    )


def mount_image(image: Path, mount_point: Path) -> None:
    mount_point.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "mount",
            "-o",
            "loop",
            str(image),
            str(mount_point),
        ],
        check=True,
    )


def copy_rootfs(rootfs: Path, mount_point: Path) -> None:
    subprocess.run(
        [
            "cp",
            "-a",
            f"{rootfs}/.",
            str(mount_point),
        ],
        check=True,
    )


def unmount_image(mount_point: Path) -> None:
    subprocess.run(
        ["umount", str(mount_point)],
        check=True,
    )

def build_disk(rootfs: Path, output: Path) -> None:
    raw_image = output.with_suffix(".raw")
    mount_point = output.parent / f".{output.stem}-mount"

    try:
        create_raw_image(raw_image)
        format_ext4(raw_image)

        mount_image(raw_image, mount_point)

        copy_rootfs(rootfs, mount_point)

    finally:
        subprocess.run(
            ["umount", str(mount_point)],
            check=False,
        )

    subprocess.run(
        [
            "qemu-img",
            "convert",
            "-f",
            "raw",
            "-O",
            "qcow2",
            str(raw_image),
            str(output),
        ],
        check=True,
    )

    raw_image.unlink()
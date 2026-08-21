from pathlib import Path
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


def partition_image(image: Path) -> None:
    subprocess.run(
        [
            "parted",
            "-s",
            str(image),
            "mklabel",
            "msdos",
        ],
        check=True,
    )

    subprocess.run(
        [
            "parted",
            "-s",
            str(image),
            "mkpart",
            "primary",
            "ext4",
            "1MiB",
            "100%",
        ],
        check=True,
    )

    subprocess.run(
        [
            "parted",
            "-s",
            str(image),
            "set",
            "1",
            "boot",
            "on",
        ],
        check=True,
    )


def attach_loop_device(image: Path) -> str:
    result = subprocess.run(
        [
            "losetup",
            "--find",
            "--show",
            "--partscan",
            str(image),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def get_partition(loop_device: str) -> str:
    if loop_device[-1].isdigit():
        return f"{loop_device}p1"

    return f"{loop_device}p1"


def format_partition(partition: str) -> None:
    subprocess.run(
        [
            "mkfs.ext4",
            "-F",
            partition,
        ],
        check=True,
    )


def mount_partition(
    partition: str,
    mount_point: Path,
) -> None:
    mount_point.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "mount",
            partition,
            str(mount_point),
        ],
        check=True,
    )


def copy_rootfs(
    rootfs: Path,
    mount_point: Path,
) -> None:
    subprocess.run(
        [
            "cp",
            "-a",
            f"{rootfs}/.",
            str(mount_point),
        ],
        check=True,
    )

def create_grub_config(mount_point: Path) -> None:
    grub_dir = mount_point / "boot/grub"
    grub_dir.mkdir(parents=True, exist_ok=True)

    kernels = sorted(
        (mount_point / "boot").glob("vmlinuz-*")
    )

    if not kernels:
        raise RuntimeError("No Linux kernel found in root filesystem.")

    kernel = kernels[-1].name
    initrds = sorted(
        (mount_point / "boot").glob("initrd.img-*")
    )

    if not initrds:
        raise RuntimeError("No initramfs found in root filesystem.")

    initrd = initrds[-1].name

    config = f"""\
set timeout=0
set default=0

menuentry 'Container VM' {{
    linux /boot/{kernel} root=/dev/sda1 rw
    initrd /boot/{initrd}
}}
"""

    (grub_dir / "grub.cfg").write_text(
        config,
        encoding="utf-8",
    )

def install_grub(
    loop_device: str,
    mount_point: Path,
) -> None:
    subprocess.run(
        [
            "grub-install",
            "--target=i386-pc",
            "--boot-directory",
            str(mount_point / "boot"),
            "--recheck",
            loop_device,
        ],
        check=True,
    )


def unmount(mount_point: Path) -> None:
    subprocess.run(
        ["umount", str(mount_point)],
        check=False,
    )


def detach_loop_device(loop_device: str) -> None:
    subprocess.run(
        ["losetup", "-d", loop_device],
        check=False,
    )


def build_disk(
    rootfs: Path,
    output: Path,
    size: str = "4G",
) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    raw_image = output.with_suffix(".raw")
    mount_point = output.parent / f".{output.stem}-mount"

    loop_device = None

    try:
        print("  Creating raw disk...")
        create_raw_image(raw_image, size)

        print("  Creating partition table...")
        partition_image(raw_image)

        print("  Attaching loop device...")
        loop_device = attach_loop_device(raw_image)

        partition = get_partition(loop_device)

        print(f"  Disk:      {loop_device}")
        print(f"  Partition: {partition}")

        print("  Formatting filesystem...")
        format_partition(partition)

        print("  Mounting filesystem...")
        mount_partition(partition, mount_point)

        print("  Copying root filesystem...")
        copy_rootfs(rootfs, mount_point)

        create_grub_config(mount_point)

        print("  Installing GRUB...")
        install_grub(loop_device, mount_point)

    finally:
        if mount_point.exists():
            unmount(mount_point)

        if loop_device is not None:
            detach_loop_device(loop_device)

    print("  Converting raw image to QCOW2...")

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
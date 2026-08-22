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

def convert_raw_to_vmdk(
    raw_image: Path,
    output: Path,
) -> None:
    subprocess.run(
        [
            "qemu-img",
            "convert",
            "-f",
            "raw",
            "-O",
            "vmdk",
            str(raw_image),
            str(output),
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
        raise RuntimeError(
            "No Linux kernel found in root filesystem."
        )

    kernel = kernels[-1].name

    initrds = sorted(
        (mount_point / "boot").glob("initrd.img-*")
    )

    if not initrds:
        raise RuntimeError(
            "No initramfs found in root filesystem."
        )

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


def create_bootable_raw_disk(
    rootfs: Path,
    raw_image: Path,
    size: str = "4G",
) -> None:
    raw_image = raw_image.resolve()
    raw_image.parent.mkdir(parents=True, exist_ok=True)

    mount_point = (
        raw_image.parent
        / f".{raw_image.stem}-mount"
    )

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

        print("  Creating GRUB configuration...")
        create_grub_config(mount_point)

        print("  Installing GRUB...")
        install_grub(loop_device, mount_point)

    finally:
        if mount_point.exists():
            unmount(mount_point)

        if loop_device is not None:
            detach_loop_device(loop_device)


def convert_image(
    source: Path,
    output: Path,
    output_format: str,
) -> None:
    command = [
        "qemu-img",
        "convert",
        "-f",
        "raw",
        "-O",
        output_format,
    ]

    if output_format == "vmdk":
        command.extend(["-o", "subformat=monolithicSparse"])

    command.extend([
        str(source),
        str(output),
    ])

    subprocess.run(command, check=True)


def build_disk(
    rootfs: Path,
    output: Path,
    size: str = "4G",
    keep_raw: bool = False,
) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    raw_image = output.parent / f".{output.stem}.raw"

    try:
        create_bootable_raw_disk(
            rootfs,
            raw_image,
            size,
        )

        output_format = output.suffix.lstrip(".").lower()

        if output_format not in {"qcow2", "vmdk"}:
            raise ValueError(
                f"Unsupported disk format: {output_format}"
            )

        print(
            f"  Converting raw image to {output_format.upper()}..."
        )

        convert_image(
            raw_image,
            output,
            output_format,
        )

        if keep_raw:
            return raw_image

        return output

    finally:
        pass
        if raw_image.exists() and not keep_raw:
            raw_image.unlink()
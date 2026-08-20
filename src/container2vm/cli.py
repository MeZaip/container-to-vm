import argparse

from pathlib import Path

from .container import extract_image, inspect_image
from .debian import build_rootfs, build_final_rootfs
from .disk import build_disk
from .models import VMConfig
import shutil

def main():
    parser = argparse.ArgumentParser(
        prog="container2vm",
        description="Convert Docker/OCI container images into virtual machines.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a container image.",
    )
    inspect_parser.add_argument(
        "image",
        help="Container image to inspect.",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract a container filesystem.",
    )

    extract_parser.add_argument(
        "image",
        help="Container image to extract.",
    )

    extract_parser.add_argument(
        "output",
        help="Directory where the filesystem will be extracted.",
    )

    build_parser = subparsers.add_parser(
        "build-base",
        help="Build a bootable Debian base VM.",
    )

    build_parser.add_argument(
        "--output",
        required=True,
        help="Output QCOW2 image.",
    )

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a container image into a VM image.",
    )

    convert_parser.add_argument(
        "image",
        help="Container image to convert.",
    )

    convert_parser.add_argument(
        "--output",
        required=True,
        help="Output QCOW2 image.",
    )

    args = parser.parse_args()

    if args.command == "inspect":
        try:
            inspect_container(args.image)
        except Exception as error:
            parser.error(str(error))
    elif args.command == "extract":
        try:
            extract_image(args.image, Path(args.output))
        except Exception as error:
            parser.error(str(error))
    elif args.command == "build-base":
        output = Path(args.output).resolve()

        rootfs = output.parent / f".{output.stem}-rootfs"

        try:
            print("[1/2] Building Debian root filesystem...")
            build_rootfs(rootfs)

            print("[2/2] Creating QCOW2 image...")
            build_disk(rootfs, output)

            print(f"VM image created: {output}")

        except Exception as error:
            parser.error(str(error))

        finally:
            # if rootfs.exists():
            #     import shutil
            #     shutil.rmtree(rootfs, ignore_errors=True)
            pass
    elif args.command == "convert":
        output = Path(args.output).resolve()

        work_dir = output.parent / f".{output.stem}-work"
        container_rootfs = work_dir / "container-rootfs"
        vm_rootfs = work_dir / "vm-rootfs"

        try:
            print("[1/4] Inspecting container image...")
            info = inspect_image(args.image)

            print("[2/4] Extracting container filesystem...")
            extract_image(args.image, container_rootfs)

            print("[3/4] Building VM root filesystem...")
            build_final_rootfs(
                container_rootfs,
                vm_rootfs,
                info.config,
                VMConfig(),
            )

            print("[4/4] Creating QCOW2 image...")
            build_disk(vm_rootfs, output)

            print(f"VM image created: {output}")

        except Exception as error:
            parser.error(str(error))

        finally:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

def inspect_container(image: str):
    info = inspect_image(image)

    print(f"Image:         {info.image}")
    print(f"Image ID:      {info.image_id}")
    print(f"Architecture:  {info.architecture}")
    print(f"OS:            {info.os}")
    print(f"Size:          {info.size / (1024 * 1024):.2f} MB")

    print("\nContainer configuration:")

    print(f"  Entrypoint:   {info.config.entrypoint}")
    print(f"  Cmd:          {info.config.cmd}")
    print(f"  Working dir:  {info.config.working_dir or '/'}")
    print(f"  User:         {info.config.user or 'root'}")

    print("\n  Environment:")
    for key, value in info.config.env.items():
        print(f"    {key}={value}")

    print("\n  Exposed ports:")
    for port in info.config.exposed_ports:
        print(f"    {port}")

    print("\n  Volumes:")
    for volume in info.config.volumes:
        print(f"    {volume}")


if __name__ == "__main__":
    main()
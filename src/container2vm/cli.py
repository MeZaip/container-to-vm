import argparse

from pathlib import Path

from .container import extract_image, inspect_image
from .debian import build_rootfs

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
    help="Build a minimal Debian root filesystem.",
    )

    build_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the Debian root filesystem.",
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
        try:
            build_rootfs(Path(args.output))
            print(f"Debian base system created at: {args.output}")
        except Exception as error:
            parser.error(str(error))

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
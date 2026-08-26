# container-to-vm

Convert a Linux Docker/OCI image into a bootable Debian virtual machine.

`container2vm` extracts an image filesystem, creates a minimal Debian VM around
it, configures a systemd service for the container command, and exports the
result as either a QCOW2 disk image or an OVA appliance.

```text
Docker/OCI image
	  |
	  v
image filesystem + metadata
	  |
	  v
bootable Debian VM
	  |
	  +--> .qcow2
	  +--> .ova
```

## Current scope

The project currently supports:

- Linux Docker images for the amd64 / x86_64 architecture;
- a Debian Bookworm VM base;
- QCOW2 and OVA output;
- Docker image `Entrypoint`, `Cmd`, environment variables, and exposed-port
  metadata;
- Linux and WSL as build environments.

The VM runs the image filesystem in a `chroot`; it does not install Docker
inside the resulting VM.

## Requirements

Required dependency commands:

```text
docker        debootstrap   qemu-img    parted
losetup       mkfs.ext4     grub-install
mount         umount        chroot
```

On Debian or Ubuntu, the non-Docker tools can usually be installed with:

```sh
sudo apt update
sudo apt install debootstrap qemu-utils parted grub-pc grub-pc-bin e2fsprogs util-linux
```


## Installation

Clone the repository, create a virtual environment, and install the project in
editable mode:

```sh
git clone https://github.com/MeZaip/container-to-vm
cd container-to-vm

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For a convenient system-wide command, run:

```sh
sudo ./scripts/install-system.sh
```

This creates `/usr/local/bin/container2vm`, pointing at the project's virtual
environment. If the project is moved or `.venv` is recreated, run the command
again.

## Check the environment

Before building an image, run:

```sh
sudo container2vm check
```

The command checks the platform, root privileges, required commands, and access
to the Docker daemon.

## Usage

Inspect an available Docker image:

```sh
sudo container2vm inspect <docker_image>
```

Extract its filesystem without creating a VM:

```sh
sudo container2vm extract <docker_image> ./nginx-rootfs
```

Create a minimal Debian base VM:

```sh
sudo container2vm build-base --output debian-base.qcow2
```

Convert an image to QCOW2:

```sh
sudo container2vm convert <docker_image> --output nginx.qcow2
```

Convert an image to an OVA appliance:

```sh
sudo container2vm convert <docker_image> --output nginx.ova
```

`convert` asks for the password of the VM user. The OVA can be imported into
VirtualBox or another compatible virtualization product. CPU, memory, and other
VM settings can be adjusted after import.

`<docker_image>` is an image available from the `docker images` list.

## Project layout

```text
src/container2vm/
  cli.py            Command-line interface
  checks.py         Host environment validation
  container.py      Docker image inspection and extraction
  debian.py         Debian root filesystem creation and configuration
  disk.py           Partitioning, bootloader, and disk-image conversion
  systemd.py        Generated service for the container command
  ova.py            OVA/OVF and manifest generation
scripts/
  install-system.sh Installs the system-wide command symlink
tests/
  test_checks.py    Environment-check tests
  test_cli.py       CLI tests
```

## Limitations

- ARM and Windows container images are not supported.
- The generated VM is BIOS/MBR based.
- Docker volumes are not transferred as persistent data volumes.
- Exposed ports are recorded as image metadata; networking and port forwarding
  are configured in the virtualization product.
- Images that require special kernel modules, Docker privileges, or a different
  CPU architecture may not run in the generated VM.

## License

Licensed under the Apache License, Version 2.0.

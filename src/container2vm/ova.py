from pathlib import Path
import hashlib
import json
import subprocess
import tarfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def get_virtual_disk_size(path: Path) -> int:
    result = subprocess.run(
        [
            "qemu-img",
            "info",
            "--output=json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    info = json.loads(result.stdout)

    return int(info["virtual-size"])


def create_ovf(
    output: Path,
    vm_name: str,
    disk_name: str,
    disk_file_size: int,
    disk_capacity: int,
    memory_mb: int,
    cpus: int,
    disk_format: str = "monolithicSparse",
) -> None:
    format_uri = (
        "http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"
        if disk_format == "streamOptimized"
        else "http://www.vmware.com/interfaces/specifications/vmdk.html#sparse"
    )

    ovf = f"""<?xml version="1.0" encoding="UTF-8"?>
<Envelope
    ovf:version="1.0"
    xmlns="http://schemas.dmtf.org/ovf/envelope/1"
    xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
    xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
    xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"
    xmlns:vbox="http://www.virtualbox.org/ovf/machine">

    <References>
        <File
            ovf:id="disk1"
            ovf:href="{disk_name}"
            ovf:size="{disk_file_size}" />
    </References>

    <DiskSection>
        <Info>Virtual disk information</Info>
        <Disk
            ovf:diskId="vmdisk1"
            ovf:fileRef="disk1"
            ovf:capacity="{disk_capacity}"
            ovf:capacityAllocationUnits="byte"
            ovf:format="{format_uri}" />
    </DiskSection>

    <NetworkSection>
        <Info>Virtual network information</Info>
        <Network ovf:name="VM Network">
            <Description>Default virtual network</Description>
        </Network>
    </NetworkSection>

    <VirtualSystem ovf:id="{vm_name}">
        <Info>Virtual machine</Info>
        <Name>{vm_name}</Name>

        <OperatingSystemSection ovf:id="96">
            <Info>The kind of installed guest operating system</Info>
            <Description>Debian_64</Description>
            <vbox:OSType ovf:required="false">Debian_64</vbox:OSType>
        </OperatingSystemSection>

        <VirtualHardwareSection>
            <Info>Virtual hardware</Info>

            <System>
                <vssd:VirtualSystemType>vmx-07</vssd:VirtualSystemType>
            </System>

            <Item>
                <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
                <rasd:Description>Number of virtual CPUs</rasd:Description>
                <rasd:ElementName>{cpus} virtual CPU(s)</rasd:ElementName>
                <rasd:InstanceID>1</rasd:InstanceID>
                <rasd:ResourceType>3</rasd:ResourceType>
                <rasd:VirtualQuantity>{cpus}</rasd:VirtualQuantity>
            </Item>

            <Item>
                <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
                <rasd:Description>Memory</rasd:Description>
                <rasd:ElementName>{memory_mb} MB of memory</rasd:ElementName>
                <rasd:InstanceID>2</rasd:InstanceID>
                <rasd:ResourceType>4</rasd:ResourceType>
                <rasd:VirtualQuantity>{memory_mb}</rasd:VirtualQuantity>
            </Item>

            <Item>
                <rasd:Address>0</rasd:Address>
                <rasd:Description>SATA Controller</rasd:Description>
                <rasd:ElementName>SATA Controller</rasd:ElementName>
                <rasd:InstanceID>3</rasd:InstanceID>
                <rasd:ResourceSubType>AHCI</rasd:ResourceSubType>
                <rasd:ResourceType>20</rasd:ResourceType>
            </Item>

            <Item>
                <rasd:AddressOnParent>0</rasd:AddressOnParent>
                <rasd:ElementName>Virtual Disk</rasd:ElementName>
                <rasd:HostResource>ovf:/disk/vmdisk1</rasd:HostResource>
                <rasd:InstanceID>4</rasd:InstanceID>
                <rasd:Parent>3</rasd:Parent>
                <rasd:ResourceType>17</rasd:ResourceType>
            </Item>

            <Item>
                <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
                <rasd:Connection>VM Network</rasd:Connection>
                <rasd:Description>Virtual Ethernet Adapter</rasd:Description>
                <rasd:ElementName>Network Adapter</rasd:ElementName>
                <rasd:InstanceID>5</rasd:InstanceID>
                <rasd:ResourceType>10</rasd:ResourceType>
            </Item>

            <Item>
                <rasd:Address>0</rasd:Address>
                <rasd:Description>Serial Port</rasd:Description>
                <rasd:ElementName>Serial Port 0</rasd:ElementName>
                <rasd:InstanceID>6</rasd:InstanceID>
                <rasd:ResourceSubType>16550A</rasd:ResourceSubType>
                <rasd:ResourceType>21</rasd:ResourceType>
            </Item>

        </VirtualHardwareSection>
    </VirtualSystem>
</Envelope>
"""

    output.write_text(
        ovf,
        encoding="utf-8",
    )


def create_manifest(
    output: Path,
    files: list[Path],
) -> None:
    lines = []

    for file in files:
        digest = sha256_file(file)
        lines.append(
            f"SHA256({file.name})={digest}"
        )

    output.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def create_ova(
    output: Path,
    ovf: Path,
    vmdk: Path,
    manifest: Path | None = None,
) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    files = [ovf, vmdk]

    if manifest is not None:
        files.append(manifest)

    with tarfile.open(
        output,
        "w",
        format=tarfile.USTAR_FORMAT,
    ) as archive:
        for file in files:
            archive.add(
                file,
                arcname=file.name,
            )

def build_ova(
    vmdk: Path,
    output: Path,
    vm_name: str,
    memory_mb: int,
    cpus: int,
    disk_format: str = "monolithicSparse",
) -> None:
    output = output.resolve()
    vmdk = vmdk.resolve()

    work_dir = output.parent / f".{output.stem}-ova"

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    ovf = work_dir / f"{vm_name}.ovf"
    manifest = work_dir / f"{vm_name}.mf"

    try:
        disk_file_size = vmdk.stat().st_size
        disk_capacity = get_virtual_disk_size(vmdk)

        print(
            f"  VMDK size:     {disk_file_size} bytes"
        )
        print(
            f"  Disk capacity: {disk_capacity} bytes"
        )

        create_ovf(
            output=ovf,
            vm_name=vm_name,
            disk_name=vmdk.name,
            disk_file_size=disk_file_size,
            disk_capacity=disk_capacity,
            memory_mb=memory_mb,
            cpus=cpus,
            disk_format=disk_format,
        )

        create_manifest(
            manifest,
            [ovf, vmdk],
        )

        create_ova(
            output=output,
            ovf=ovf,
            vmdk=vmdk,
            manifest=manifest,
        )

    finally:
        if work_dir.exists():
            for file in work_dir.iterdir():
                if file.is_file():
                    file.unlink()

            work_dir.rmdir()
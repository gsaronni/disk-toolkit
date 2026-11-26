"""A warning must still be reported when the disk is already critical."""

from smart_parser import DiskInfo, NvmeHealth, SmartAttribute


def _attr(attr_id, name, value, raw):
    return SmartAttribute(
        id=attr_id, name=name, flag="0x0032", value=value, worst=value,
        thresh=0, type="Old_age", updated="Always", when_failed="-",
        raw_value=str(raw),
    )


def _sata_disk(attributes):
    return DiskInfo(
        device="/dev/sda", model="TestDisk", serial="0", capacity="1 TB",
        disk_type="SSD", rotation_rate="Solid State Device",
        smart_enabled=True, smart_health="PASSED",
        attributes={a.id: a for a in attributes},
    )


def test_sata_warning_kept_after_critical(checker):
    # Attribute 5 is checked before 188: 50 reallocated sectors is critical,
    # Command_Timeout VALUE=40 is a warning (threshold 1, warning 50).
    disk = _sata_disk([
        _attr(5, "Reallocated_Sector_Ct", 100, 50),
        _attr(188, "Command_Timeout", 40, 0),
    ])
    checker.analyze_disk(disk)
    found = {(i["attribute"], i["severity"]) for i in disk.issues}
    assert ("Reallocated_Sector_Ct", "CRITICAL") in found
    assert ("Command_Timeout", "WARNING") in found
    assert disk.overall_status == "CRITICAL"


def test_nvme_warning_kept_after_critical(checker):
    disk = DiskInfo(
        device="/dev/nvme0n1", model="TestNVMe", serial="0", capacity="1 TB",
        disk_type="NVMe", rotation_rate="N/A (NVMe)",
        smart_enabled=True, smart_health="PASSED",
        nvme=NvmeHealth(critical_warning=0x1, percentage_used_pct=95),
    )
    checker.analyze_disk(disk)
    found = {(i["attribute"], i["severity"]) for i in disk.issues}
    assert ("Critical_Warning", "CRITICAL") in found
    assert ("Percentage_Used", "WARNING") in found
    assert disk.overall_status == "CRITICAL"


def test_warning_alone_sets_warning_status(checker):
    disk = _sata_disk([_attr(188, "Command_Timeout", 40, 0)])
    checker.analyze_disk(disk)
    assert [i["severity"] for i in disk.issues] == ["WARNING"]
    assert disk.overall_status == "WARNING"

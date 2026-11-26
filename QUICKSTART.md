# Quick Setup Guide

## Health Checker: no config, works immediately

```bash
sudo bin/disk-health-checker.py                  # full report
sudo bin/disk-health-checker.py -v               # also the monitored attribute values
sudo bin/disk-health-checker.py -q               # summary only
sudo bin/disk-health-checker.py --critical       # critical disks only
sudo bin/disk-health-checker.py --json           # structured snapshot to stdout
sudo bin/disk-health-checker.py --json-out FILE  # the same snapshot written to FILE
```

`rich` is optional (`sudo apt install python3-rich`, or `pip3 install rich --break-system-packages`): without it the script falls back to plain text with the same structure.

---

## Temperature Monitor: 5-Minute Setup

### 1. Find Your Disks

```bash
lsblk
sudo smartctl -i /dev/sda
```

### 2. Find the Temperature Attribute

```bash
sudo smartctl -a /dev/sda | grep -i temp
```

The monitor takes field 10 (RAW_VALUE) of the last line matching your pattern, so the pattern must match an ATA attribute row, for example:

```
194 Temperature_Celsius     0x0022   036   040   000    Old_age   Always       -       36
190 Airflow_Temperature_Cel 0x0022   064   052   045    Old_age   Always       -       36
```

`Temperature_Celsius` (attribute 194) is the common one. NVMe disks (`Temperature: 36 Celsius`) and SAS disks (`Current Drive Temperature: 36 C`) report temperature in a different layout and read as `N/A`.

### 3. Configure Disks

```bash
cp etc/disks.conf.template etc/disks.conf
$EDITOR etc/disks.conf
```

Format is `device_path,friendly_name,grep_pattern`, one disk per line; lines starting with `#` are ignored:

```
/dev/sda,SystemDrive,Temperature_Celsius
/dev/sdb,BackupDrive,Temperature_Celsius
```

`etc/disks.conf` is gitignored: it describes your machine, not the project.

### 4. Start Monitoring

```bash
sudo bin/monitor-temp.sh
```

Let it run for at least 10 to 15 minutes to collect meaningful data. The log goes to `temperature_log.csv` at the repo root, whatever directory you start the script from, and rotated logs go to `temp_logs_backup/` next to it. Both are gitignored: generated data, not something to commit.

### 5. Analyse Results (optional)

```bash
pip3 install -r analysis/requirements.txt --break-system-packages
python3 analysis/analyze-temp.py    # from the repo root, where the log is
```

It needs at least two disks in the log and graphs the first two. Skip this step for quick spot checks: logging works without it.

---

## Common `etc/disks.conf` Setups

**SSD + HDD:**
```
/dev/sda,System_SSD,Temperature_Celsius
/dev/sdb,Backup_HDD,Temperature_Celsius
```

**SSD reporting only attribute 190:**
```
/dev/sda,System_SSD,Airflow_Temperature_Cel
```

**RAID array (any number of disks):**
```
/dev/sda,RAID_Disk1,Temperature_Celsius
/dev/sdb,RAID_Disk2,Temperature_Celsius
/dev/sdc,RAID_Disk3,Temperature_Celsius
```

---

## Troubleshooting

**"Warning: Could not read any temperatures"** (nothing is logged for that interval)
- Not run as root? SMART data needs it: `sudo bin/monitor-temp.sh`
- Wrong device path? Check with `lsblk`
- Wrong grep pattern? Check with `sudo smartctl -a /dev/sdX | grep -i temp`; the matching line must have the temperature in field 10

**One disk shows `N/A`, the others work**
- Same checks for that disk's line in `etc/disks.conf`; the row is still logged, with `N/A` in that column

**"Error: .../etc/disks.conf not found!"**
- Copy the template first: `cp etc/disks.conf.template etc/disks.conf`

**"ERROR: Must run as root (use sudo)"** from the health checker
- It exits with code 1; run it with `sudo`

**Script will not start**
- Executable bit: `chmod +x bin/monitor-temp.sh bin/disk-health-checker.py`
- Line endings: on a Windows checkout used from WSL, `bin/*.sh` must have LF endings (the repo's `.gitattributes` enforces this for new checkouts)

**`disk-health-checker.py` cannot import `smart_parser`**
- It resolves `lib/` relative to its own location (`bin/../lib`), so keep the repo layout: do not copy `bin/disk-health-checker.py` somewhere on its own without `lib/` beside `bin/`.

---

## Tips

- **Logging interval:** 10 seconds, set by `INTERVAL=10` in `bin/monitor-temp.sh`
- **Log rotation:** above 50 MB, set by `MAX_FILE_SIZE=50000000`
- **Stop logging:** Ctrl+C (trapped for a clean exit)
- **Background logging:** `sudo bin/monitor-temp.sh > /dev/null 2>&1 &`, stop it with `sudo kill <pid>`
- **Health check from cron or monitoring:** rely on the exit code (`0` healthy, `1` warning, `2` critical), not on parsing stdout. Note that `1` also means "not run as root" or "smartctl missing"

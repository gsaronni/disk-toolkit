# Disk Toolkit

> SMART disk health checker and temperature logger for homelab servers: CLI-first, built for SSH-only and rarely powered machines where a web dashboard does not help.

[![ci](https://github.com/gsaronni/disk-toolkit/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/gsaronni/disk-toolkit/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Rich (optional)](https://img.shields.io/badge/rich-optional-purple.svg)](https://github.com/Textualize/rich)

---

## The Problem

[Scrutiny](https://github.com/AnalogJ/scrutiny) and similar web dashboards are excellent for always-on infrastructure, but they do not help when:

- A backup server boots only about 12 days a year: a full web stack and database is overkill for an occasional check
- Access is SSH-only over a mesh VPN, with no convenient path to a web UI
- `smartctl -a` output needs deep SMART knowledge to interpret: "VALUE=1" means nothing without context
- You need an answer *now*, during a maintenance window, not after 30 minutes of looking up attribute IDs

Full background and the incident that triggered this: [`docs/01-problem-definition.md`](docs/01-problem-definition.md).

---

## Two Tools

### Disk Health Checker: `bin/disk-health-checker.py`

Point-in-time SMART analysis with **actionable output**, not raw attribute dumps.

```bash
sudo bin/disk-health-checker.py
```

Sample, plain-text mode (two synthetic disks, header panel omitted):

```
 /dev/sda - ST500LT012-1DG142 (500 GB)
------------------------------------------------------------------------
Type: HDD | Power-On: 31,029h (3.5 years) | Temp: 25C
SMART Health: PASSED | Our Analysis: CRITICAL

!! Load_Cycle_Count (VALUE=1)
   |- Head parking mechanism exhausted - mechanical failure imminent
   `- Action: Replace within 1-4 weeks

[!] /dev/sdb - WDC WD40EFRX-68N32N0 (4.00 TB)
------------------------------------------------------------------------
Type: HDD | Power-On: 9,464h (1.1 years) | Temp: 28C
SMART Health: PASSED | Our Analysis: WARNING

!  Command_Timeout (VALUE=40)
   |- Some command timeouts detected
   `- Action: Monitor. Try different SATA cable first.


--- SUMMARY ------------------------------------------------------------
Healthy   0 disk(s)
Warning   1 disk(s)
Critical  1 disk(s)

Action Required:
  !! /dev/sda: REPLACE WITHIN 24-48H
  !  /dev/sdb: Monitor/test, replace in 1-4 weeks
```

This run exits with code `2`. With `rich` installed the same report is coloured and the rules are drawn with box characters. In plain-text mode the `[OK]` and `[X]` status markers before a disk name are lost (see Known Limitations), which is why the first disk line above starts with a space.

- Discovers `/dev/sd[a-z]` and `/dev/nvme[0-9]n[0-9]`, runs `smartctl -a` on each (10 second timeout) and picks the parser by device path
- SATA: rules on the numbered ATA attribute table, per attribute. Reallocated sectors are judged on the RAW count, Load Cycle Count on the normalised VALUE; HDD-only rules are skipped on SSDs; Seagate `Raw_Read_Error_Rate` is judged on its headroom above the threshold, not on a fixed cutoff
- NVMe: rules on the named `SMART/Health Information` fields
- Exit codes for automation: `0` healthy, `1` warning, `2` critical. Not running as root, or `smartctl` missing, also exits `1`
- `-v` adds the monitored attribute values (NVMe: all parsed health fields), `-q` prints only the summary, `--critical` keeps only critical disks
- `--json` prints a structured snapshot to stdout, `--json-out FILE` writes it to a file. It is a spot check to `jq` or diff by hand, not a history mechanism (JSON Export Format section in [`docs/03-design-decisions.md`](docs/03-design-decisions.md)). It includes serial numbers and the hostname
- `rich` is optional: without it the report falls back to plain text with the same structure, so it runs on hosts where you do not control the Python environment

**Use case:** monthly checkups, pre-backup verification, an immediate assessment after booting an infrequently powered server.

### Temperature Monitor: `bin/monitor-temp.sh` + `analysis/analyze-temp.py`

Continuous SMART temperature logging with rotation, plus optional trend graphs.

```
$ sudo bin/monitor-temp.sh
Found 2 disk(s) to monitor:
  - DataDisk (/dev/sdf)
  - MediaDisk (/dev/sdh)

Starting new temperature log...
Logging every 10 seconds. Press Ctrl+C to stop.
Log file: /opt/disk-toolkit/temperature_log.csv

14:30:15 - DataDisk: 35C MediaDisk: 34C
```

- Config-driven: `etc/disks.conf`, one line per disk, no editing the script itself
- Reads field 10 (RAW_VALUE) of the last `smartctl -a` line matching the disk's pattern, so it works with ATA attribute rows such as `194 Temperature_Celsius`; NVMe and SAS temperature lines have a different layout and read as `N/A`
- Writes `temperature_log.csv` and `temp_logs_backup/` at the repo root, whatever directory it is started from
- Rotates the log above 50 MB (50,000,000 bytes) into `temp_logs_backup/`, gzip-compressed
- `analysis/analyze-temp.py` (optional, needs `pandas` and `rich`) draws terminal graphs and statistics for the first two disks in the CSV

**Use case:** thermal stress testing during RAID scrubs or rebuilds, validating cooling changes, long-running workload monitoring.

---

## Project Structure

```
disk-toolkit/
  bin/
    disk-health-checker.py     point-in-time SMART analysis
    monitor-temp.sh            continuous temperature logger
  lib/
    smart_parser.py            SATA and NVMe smartctl parsing
  etc/
    disks.conf.template        copy to disks.conf, edit for your disks
  analysis/                    optional, see below
    analyze-temp.py
    requirements.txt           pandas + rich, separate from the core tools
  docs/
    01-problem-definition.md
    02-prompt-engineering.md
    03-design-decisions.md
    04-smart-attributes-explained.md
    05-temp-monitor-migration.md
  examples/
    firstSetup.txt             terminal output of an early version (February 2026)
  tests/                       pytest suite, see Testing
  .github/workflows/ci.yml     pytest on Python 3.10 and 3.14, shellcheck
  QUICKSTART.md
  CHANGELOG.md
  LICENSE
```

**Why `analysis/` is separate:** `analyze-temp.py` needs `pandas` and `rich`, which turns "run a script" into "manage a Python environment". For occasional spot checks that is not worth it: `disk-health-checker.py --json` covers the "check the state at one specific moment" case without an install step. Graphing stays available for when you want it, just not on the default path.

---

## Quick Start

```bash
git clone https://github.com/gsaronni/disk-toolkit.git
cd disk-toolkit

# Optional: colour output (plain-text fallback if skipped)
sudo apt install python3-rich   # or: pip3 install rich --break-system-packages

# Health check: no config needed, discovers disks itself
sudo bin/disk-health-checker.py

# Temperature logging: needs a config first
cp etc/disks.conf.template etc/disks.conf
$EDITOR etc/disks.conf          # one line per disk: /dev/sdX,FriendlyName,GrepPattern
sudo bin/monitor-temp.sh

# Optional: trend graphs from the logged CSV, run from the repo root
pip3 install -r analysis/requirements.txt --break-system-packages
python3 analysis/analyze-temp.py
```

Full walkthrough: [`QUICKSTART.md`](QUICKSTART.md).

---

## AI-Assisted Development

This project was built through iterative human-AI collaboration, not one-shot code generation. The design decisions (Python over Bash, hardcoded rules over config files, the exit code strategy, graceful-degradation error handling) were argued through, not accepted by default. The full process, including a real production bug the AI's initial design missed, is documented:

**[Read the full collaboration process](docs/02-prompt-engineering.md)**

Highlights:
- **Phase 3, Fighting Vagueness:** rejecting "test thoroughly" as an output until it became a concrete command with pass/fail criteria
- **[Phase 7, Real-World Bug Discovery](docs/02-prompt-engineering.md#phase-7-real-world-bug-discovery):** a manufacturer-specific false positive (Seagate `Raw_Read_Error_Rate`) found in production and fixed with a threshold-relative check instead of a hardcoded cutoff

What this demonstrates: problem-solving driven by a real operational incident, critical evaluation of AI output rather than blind acceptance, and domain knowledge (SMART attributes, disk failure modes) that the AI did not independently have.

---

## SMART Attribute Rules (selection)

| ID | Attribute | Critical when | Action |
|----|-----------|---------------|--------|
| 5 | Reallocated_Sector_Ct | RAW > 10 | Replace disk NOW |
| 193 | Load_Cycle_Count | VALUE <= 5 | Replace within 1-4 weeks |
| 197 | Current_Pending_Sector | RAW > 0 | Backup NOW, replace within 24h |
| 188 | Command_Timeout | VALUE <= 1 | Check cable, PSU, controller first |

NVMe (no numbered table, named fields instead): Critical Warning bitmap non-zero, Available Spare at or below its threshold, Percentage Used >= 90% (warning) or >= 100% (critical), any Media and Data Integrity Errors.

All rules are in `ATTRIBUTE_RULES` and `analyze_nvme_disk()` in [`bin/disk-health-checker.py`](bin/disk-health-checker.py). Failure mechanics and manufacturer quirks: [`docs/04-smart-attributes-explained.md`](docs/04-smart-attributes-explained.md).

---

## Requirements

**Core (`bin/disk-health-checker.py`, `bin/monitor-temp.sh`):**
- Linux with `smartmontools` (`apt install smartmontools`)
- Python 3.10 or later (CI tests 3.10 and 3.14); bash for the monitor
- Root or sudo: SMART data needs privileges
- `rich`: optional, plain-text fallback if absent

**`analysis/analyze-temp.py` only:**
- `pandas`, `rich` (see `analysis/requirements.txt`)

---

## Known Limitations

- Discovery covers `/dev/sda` to `/dev/sdz` and `/dev/nvme0n1` to `/dev/nvme9n9`: `/dev/sdaa` and later, or `/dev/nvme10n1` and later, are not found
- SAS disks show up as `/dev/sdX`, but their `smartctl` output has no ATA attribute table, so the checker has no rules for them
- Disks where `smartctl` does not report SMART as enabled are left out of the report without a message
- Plain-text mode drops the `[OK]` and `[X]` status markers (it strips them as if they were `rich` markup); `[!]` survives
- `analysis/analyze-temp.py` reads `temperature_log.csv` from the current directory, graphs only the first two disks, and its 35 C and 36 C thresholds are fixed

---

## Roadmap

**Shipped (v1.1.0):**
- NVMe support (previously NVMe disks were silently unparsed, see [`docs/03-design-decisions.md`](docs/03-design-decisions.md))
- `--json` / `--json-out` structured output
- `rich` made optional with a plain-text fallback

**Backlog (deliberately deferred, not forgotten):**
- [ ] RAID/multipath device detection (`smartctl -d megaraid,N` and similar): no RAID controller on current hardware, so this waits until it is needed
- [ ] Historical storage (`~/.disk-health/*.json`) and a diff mode
- [ ] Prometheus exporter path (`smartctl_exporter` into an existing Prometheus/Grafana stack) instead of a bespoke dashboard

---

## Testing

Automated tests live in `tests/` and use synthetic data only; they never call `smartctl`. CI runs them on ubuntu-latest with Python 3.10 and 3.14, and runs shellcheck on `bin/monitor-temp.sh`. The 11 tests cover:

- Warnings still reported once a disk is already critical (SATA and NVMe), and a lone warning setting WARNING status
- The report timestamp carrying the real UTC offset
- `__version__` and `__github__` as real module attributes
- `etc/disks.conf.template` shipping no active lines
- The three scripts stored as executable (`100755`) in git
- `monitor-temp.sh` finding its config and writing its log at the repo root from any working directory, with a fake `smartctl` (needs bash, skipped on Windows)

```bash
python3 -m pip install pytest
python3 -m pytest
```

Not covered by automated tests: parsing real `smartctl` output, disk discovery, and the rendered report. The rules were developed against real disks on the author's homelab, including the `Load_Cycle_Count` incident ([`docs/01-problem-definition.md`](docs/01-problem-definition.md)) and the Seagate false positive (Phase 7 above).

The repo carries a [pre-commit](https://pre-commit.com/) hook that rejects control characters in text files: `pre-commit install` to enable it.

---

## License

MIT, see [LICENSE](LICENSE).

---

## Acknowledgments

- [Scrutiny](https://github.com/AnalogJ/scrutiny): inspiration for attribute interpretation
- [smartmontools](https://www.smartmontools.org/): the underlying SMART tooling
- [Rich](https://github.com/Textualize/rich): terminal formatting, when available

---

**Built for homelab infrastructure where a web dashboard is not the answer.**

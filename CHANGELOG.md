# Changelog

All notable changes to this project are documented here.

## [1.1.1] - Unreleased

### Fixed
- `bin/monitor-temp.sh` resolves `etc/disks.conf`, `temperature_log.csv` and `temp_logs_backup/` from its own location instead of the working directory. Since the 1.1.0 restructure it looked for `disks.conf` in the working directory and never found `etc/disks.conf`.
- `etc/disks.conf.template` ships with every example commented out; in 1.1.0 two example disks were active, so a copied template monitored disks that may not exist.
- The report header labelled local time as UTC; it now prints the local time with its real offset (e.g. `+0100`).
- `__version__`, `__author__`, `__description__` and `__github__` were text inside the module docstring, not attributes; they are now real module attributes, and `__github__` points to this repository.
- A warning was dropped when the disk was already critical (SATA attribute rules and NVMe Percentage Used); both severities are now reported.
- `bin/disk-health-checker.py`, `bin/monitor-temp.sh` and `analysis/analyze-temp.py` are stored as executable (`100755`).
- Two shellcheck warnings in `bin/monitor-temp.sh` (unquoted command substitution in the rotation check, `local` masking a return value).

### Added
- `tests/`: pytest suite on synthetic data (11 tests; the bash test is skipped on Windows).
- GitHub Actions CI: pytest on ubuntu-latest with Python 3.10 and 3.14, and shellcheck.
- pre-commit hook rejecting control characters in text files.
- `.gitattributes` keeping LF line endings on `*.sh`.

### Changed
- README, QUICKSTART and the config template rewritten to match the code: supported Python is 3.10+, discovery limits and other known limitations listed, the Testing section describes the actual tests, temperature patterns limited to ATA attribute rows. SAS is no longer claimed as supported: its `smartctl` output has no ATA attribute table.
- `bin/monitor-temp.sh` prints temperatures on the console as `35C`, without the degree sign, matching the health checker; the CSV is unchanged.
- `--verbose` help text says what it shows: the monitored attributes (all health fields on NVMe).
- Em-dashes replaced with ASCII punctuation in docs and code comments.

## [1.1.0] - 2026-08-17

### Added
- NVMe support in `lib/smart_parser.py`. Previously NVMe disks silently returned zero SMART attributes because only the SATA numbered attribute table was parsed. NVMe's named `SMART/Health Information` block (Critical Warning, Available Spare, Percentage Used, Media and Data Integrity Errors) is now parsed and analysed by a dedicated `analyze_nvme_disk()` rule set.
- `--json` / `--json-out FILE` flags: structured snapshot output, bypassing the rendering path. Explicitly a spot-check tool, not a history or monitoring mechanism (see `docs/03-design-decisions.md`).
- Optional `rich` dependency: falls back to a plain-text renderer with the same report structure (headers, per-issue blocks, summary table) without colour, so the tool runs on hosts without guaranteed `pip` access.

### Changed
- Project restructured from two flat sibling folders (`disk-health-checker/`, `disk-temp-monitor/`) into `bin/`, `lib/`, `etc/`, `docs/`, `examples/`, `analysis/`; shared parsing logic extracted to `lib/smart_parser.py`.
- `analyze-temp.py` (requires `pandas` and `rich`) moved to `analysis/` and marked optional: not part of the default install path.
- `disks.conf` moved to `etc/disks.conf.template`; the real host-specific `etc/disks.conf` is gitignored.
- `temperature_log.csv` and `temp_logs_backup/` are gitignored: generated data, not source.

### Fixed
- Broken cross-reference in `docs/01-problem-definition.md` pointing to a nonexistent `02-ai-collaboration-process.md`, corrected to `02-prompt-engineering.md` with the right section ("Phase 7: Real-World Bug Discovery", not "Phase 5").

## [1.0.0-alpha] - 2026-02-10

### Added
- Initial release: SATA SMART attribute analysis with 10 checked attributes, context-aware rules (HDD/SSD-specific), severity classification (HEALTHY/WARNING/CRITICAL), exit codes (0/1/2) for automation.
- Later in the alpha series:
  - 2026-02-22: manufacturer-specific handling for Seagate `Raw_Read_Error_Rate` (threshold-relative headroom check instead of a hardcoded cutoff) after a real production false positive, see `docs/02-prompt-engineering.md`, Phase 7.
  - 2026-03-05 to 2026-03-07: `monitor-temp.sh` and `analyze-temp.py` temperature logging and trend visualisation added, then moved from hardcoded disk paths to `disks.conf`-driven configuration (see `docs/05-temp-monitor-migration.md`).

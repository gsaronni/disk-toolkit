"""Module metadata, report timestamp, shipped config template, file modes."""

import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest


def test_dunders_are_real_attributes(checker):
    assert checker.__version__ == "1.1.0"
    assert checker.__github__ == "https://github.com/gsaronni/disk-toolkit"


def test_report_timestamp_carries_real_offset(checker):
    # Local time must not be labelled UTC; the offset is printed instead.
    cet = timezone(timedelta(hours=1))
    stamp = checker.report_timestamp(datetime(2026, 11, 23, 14, 5, 0, tzinfo=cet))
    assert stamp == "2026-11-23 14:05:00 +0100"


def test_report_timestamp_defaults_to_now(checker):
    stamp = checker.report_timestamp()
    assert "UTC" not in stamp
    assert stamp[-5] in "+-"


def test_config_template_has_no_active_lines(repo_root):
    text = (repo_root / "etc" / "disks.conf.template").read_text(encoding="utf-8")
    active = [
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert active == []


EXECUTABLES = [
    "analysis/analyze-temp.py",
    "bin/disk-health-checker.py",
    "bin/monitor-temp.sh",
]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
@pytest.mark.parametrize("path", EXECUTABLES)
def test_scripts_are_executable_in_git(repo_root, path):
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--", path],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    assert result.stdout.split()[0] == "100755", result.stdout

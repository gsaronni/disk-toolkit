"""bin/monitor-temp.sh must find etc/disks.conf and write its log at the repo
root whatever the working directory. Needs bash: skipped on Windows, run in
WSL or CI."""

import os
import shutil
import signal
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="bash script; run on Linux"
)

FAKE_SMARTCTL = """#!/bin/sh
echo "194 Temperature_Celsius     0x0022   036   040   000    Old_age   Always       -       36"
"""


def test_runs_from_any_cwd(repo_root, tmp_path):
    root = tmp_path / "toolkit"
    (root / "bin").mkdir(parents=True)
    (root / "etc").mkdir()
    script = root / "bin" / "monitor-temp.sh"
    shutil.copy(repo_root / "bin" / "monitor-temp.sh", script)
    script.chmod(0o755)
    (root / "etc" / "disks.conf").write_text(
        "# test\n/dev/sdz,TestDisk,Temperature_Celsius\n"
    )

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    smartctl = fakebin / "smartctl"
    smartctl.write_text(FAKE_SMARTCTL)
    smartctl.chmod(0o755)

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = dict(os.environ, PATH=f"{fakebin}{os.pathsep}{os.environ['PATH']}")

    log = root / "temperature_log.csv"
    proc = subprocess.Popen(
        ["bash", str(script)], cwd=elsewhere, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and proc.poll() is None:
            if log.exists() and len(log.read_text().splitlines()) >= 2:
                break
            time.sleep(0.1)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
        output = proc.communicate(timeout=5)[0]

    assert log.exists(), output
    lines = log.read_text().splitlines()
    assert lines[0] == "Timestamp,TestDisk_Temperature"
    assert lines[1].endswith(",36")
    assert (root / "temp_logs_backup").is_dir()
    assert list(elsewhere.iterdir()) == []

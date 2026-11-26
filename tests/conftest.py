"""Shared fixtures. bin/disk-health-checker.py has a hyphen in its name, so it
is loaded by path rather than imported."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "lib"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def checker():
    path = REPO_ROOT / "bin" / "disk-health-checker.py"
    spec = importlib.util.spec_from_file_location("disk_health_checker", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["disk_health_checker"] = module
    spec.loader.exec_module(module)
    return module

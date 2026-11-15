"""Runs the import-linter contracts in `backend/.importlinter` as part of the normal test run."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("lint-imports") is None and not (Path(sys.executable).parent / "lint-imports").exists(), reason="import-linter not installed")
def test_import_contracts_hold():
    exe = shutil.which("lint-imports") or str(Path(sys.executable).parent / "lint-imports")
    result = subprocess.run([exe], cwd=BACKEND, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-500:]

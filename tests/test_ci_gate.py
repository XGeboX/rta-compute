# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""The AGPL boundary gate must distinguish clean scans from scanner errors."""

import os
import re
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.mark.parametrize("grep_status,exit_status,stdout,stderr", [
    (2, 2, "", "boundary scan failed (grep status 2)\n"),
    (0, 1, "", "boundary marker found\n"),
    (1, 0, "boundary clean\n", ""),
], ids=["status-2", "status-0", "status-1"])
def test_boundary_scan_propagates_grep_error(
        tmp_path, grep_status, exit_status, stdout, stderr):
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text()
    # Execute the shipping command so the regression cannot drift from CI.
    run = re.search(
        r"^      - name: AGPL boundary check\n"
        r"(?:        #[^\n]*\n)*"
        r"        run: \|\n((?:          [^\n]*\n|\n)+)",
        workflow, re.MULTILINE,
    )
    assert run, "boundary check run command missing"
    command = dedent(run.group(1))

    grep = tmp_path / "grep"
    grep.write_text(f"#!/bin/sh\nexit {grep_status}\n")
    grep.chmod(0o755)
    result = subprocess.run(
        ["bash", "-e", "-c", command],
        cwd=root,
        env={**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == exit_status, result
    assert result.stdout == stdout
    assert result.stderr == stderr

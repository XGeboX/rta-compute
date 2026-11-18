#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
# The retired wording reduces the sky to arithmetic; keep it out of product copy.

import os
from pathlib import Path
import re
import subprocess

import pytest


def test_copy_guard():
    root = Path(__file__).resolve().parents[1]
    if not (root / ".git").exists():
        pytest.skip("Copy guard requires Git metadata; this build has no .git")
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True,
        ).stdout
    except FileNotFoundError:
        pytest.skip("Copy guard requires git, which is unavailable")

    retired = re.compile(r"\bcomp" + r"uted\b", re.IGNORECASE)
    hits = []
    for name in tracked.split(b"\0"):
        if not name:
            continue
        path = Path(os.fsdecode(name))
        if path.parts[0] == "data":
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if retired.search(line):
                hits.append(f"{path}:{number}")

    assert not hits, "Retired wording found:\n" + "\n".join(hits)

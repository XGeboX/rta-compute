#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""The byte-identical contract, stated by the running process itself.

The reproducibility guarantee is scoped per image digest: identical input
to the same image produces identical output. This module echoes the build
identity (RTA_ENGINE_SHA, baked at image build) and the ACTUAL installed
versions of the two computation dependencies — read from package metadata
at import, never hand-claimed, so the echo cannot drift from reality.
"""

import os
from importlib import metadata

ENGINE_SHA = os.environ.get("RTA_ENGINE_SHA", "dev")

CONTRACT = "byte-identical per image digest"


def _installed(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:  # pragma: no cover
        return "absent"


PINS = {
    "pyjhora": _installed("PyJHora"),
    "pyswisseph": _installed("pyswisseph"),
}


def engine_version() -> dict:
    """The version block carried by /healthz and every Instant response."""
    return {"sha": ENGINE_SHA, **PINS, "contract": CONTRACT}

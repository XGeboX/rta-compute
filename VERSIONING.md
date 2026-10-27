# Versioning and the Byte-Identical Contract

## The contract

**Byte-identical per image digest.** Identical input sent to the same
published image (`ghcr.io/xgebox/rta-compute@sha256:...`) produces identical
output, byte for byte. The guarantee is scoped to the digest, not to the
project name or a tag: `latest` moves, a digest never does.

Every running instance states its own identity:

- `GET /v1/healthz` returns a `version` block: the git commit the image was
  built from (`sha`), and the **installed** versions of PyJHora and
  pyswisseph, read from package metadata at runtime, never hand-claimed.
- Every `/v1/instant` response carries the same block under `engine`, so any
  reading can be traced to the exact engine that computed it.

## Why the determinism holds

- PyJHora is pinned exactly (`PyJHora==4.6.0`), pyswisseph exactly
  (`pyswisseph==2.10.3.2`), in `pyproject.toml`, CI, and the Dockerfile.
- The service is stateless and never consults a clock inside computation
  paths (the only default-to-today is the Instant `asof`, which is echoed in
  the response, making the input fully reconstructible).
- The golden-gate suite runs inside the image build; an image whose
  computations drift from the pinned fixtures cannot exist.

## Dependency bump policy

Any change to a computation dependency (PyJHora, pyswisseph, ephemeris
files, numpy) requires, in one reviewed PR:

1. The pin updated in all three places (pyproject, CI, Dockerfile).
2. The full golden-gate suite green against the new pin.
3. A **fixture-diff review**: regenerate every pinned fixture value and
   review the diff line by line. Differences must be explained (upstream
   bug fixed? ephemeris refinement?) and the explanation recorded in the PR.
   Unexplained drift blocks the merge.
4. A note in this file's history section naming the bump and its effect.

Non-computation dependencies (FastAPI, uvicorn) follow normal review; they
cannot affect computed values, and the golden gates prove it.

## History

- 2026-06-12: contract stated; version echo added to /healthz and Instant
  responses; `GIT_SHA` baked at image build.

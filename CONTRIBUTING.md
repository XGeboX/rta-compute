# Contributing to rta-compute

This is the open computational core of [rtarhythm.com](https://rtarhythm.com): the
math, the pipelines, and the citations behind a jyotiṣa practice that
holds śāstra and software accountable to each other. The project's
standards are unusual, and they are the point. Read them before you open
anything.

## The doctrine

**Computed, not generated.** Every number this service returns is a
deterministic computation against the Swiss Ephemeris under classical
rules. No language model produces, paraphrases, or "improves" any output
or any astrological claim in this repository, and none ever will.
Contributions that introduce model-generated text or numbers will be
declined.

**Cited, not asserted.** Every astrological rule carries its source. A
rule without a citation (text, chapter, verse) is not a rule here, it is
an opinion, and opinions do not merge. New rules arrive with their
provenance or they do not arrive.

**Reproducible, not approximate.** Identical input produces
byte-identical output. The golden gates pin this against the founding
chart and external oracles (JPL Horizons, astropy/ERFA). A change that
moves a verified value must justify the move in the same pull request,
with the oracle that confirms the new value.

**Walled by design.** This repository holds math and citations only.
Editorial prose, business logic, and any real person's birth data live
elsewhere and must never appear here. The only chart in this repository
is the platform's own founding kuṇḍalī, which is public brand data. CI
greps for editorial markers and birth-data literals on every push.

## Working here

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # the gate suite, ~130 checks
uvicorn app.main:app --reload
```

A change is ready when:

- `pytest` is green, including the golden parity gates.
- Any new astrological rule carries `{source, chapter, verse}` in code
  and in the response it produces.
- Determinism holds: run the same request twice, diff the JSON, expect
  nothing.
- `VERSIONING.md` is honored for any dependency change (golden gates plus
  a full fixture-diff review before merge).
- No editorial prose, no model output, no birth data beyond the founding
  chart.

## Reporting an error in the math

The most valuable contribution is a demonstrated wrong number. Open an
issue with the input, the value this service returned, the value you
believe is correct, and the source that settles it (a text, an
ephemeris, an independent computation). "Verify our math" is an
invitation, and a corrected gate is the best pull request this project
can receive.

## Provenance

Developed by Anirudh Sharma. Licensed AGPL-3.0: the source you verify is
the source that runs.

# rta-compute

The open computational core of [rtarhythm.com](https://rtarhythm.com).

**Computed, not generated.** Every number this service returns is a
deterministic computation against the Swiss Ephemeris under classical
jyotiṣa rules, with the rule sources cited in the output. No language
models are involved anywhere in this codebase. Identical input produces
byte-identical output. That claim is auditable: this repository is the
running source.

## What it computes

| Endpoint | Computation |
|---|---|
| `POST /v1/chart` | Sidereal charts (ayanāṁśa: True Pushya default; Lahiri, Raman, KP offered) with divisional charts D1 through D144, or tropical charts with Placidus / equal / whole-sign cusps. Tropical is derived exactly as sidereal + ayanāṁśa(t), the definitional relation. |
| `POST /v1/panchanga` | Tithi, nakṣatra, yoga, karaṇa, vāra, sunrise and sunset for any moment and place. |
| `POST /v1/dasha` | Vimśottarī daśā to five levels: mahā and antar and pratyantar natively, sūkṣma and prāṇa by the classical proportional rule. |
| `POST /v1/sensitivity` | Birth-time sensitivity: the exact clock window within which each varga lagna is stable, bisected against the true ascendant. Depth offered, honesty enforced: when a recorded birth time cannot support a varga, the output says so. |
| `POST /v1/instant` | The deterministic rule engine behind RTA Instant: natal facts, the running daśā stack, classical gochara gate verdicts (aṣṭakavarga bindu-weighting, kakṣyā, vedha, tārā-bala), and fired rules each carrying its śāstric citation. |
| `GET /v1/atlas` | Self-hosted place search: GeoNames cities500 in SQLite FTS5 with diacritic folding and IANA timezone resolution. No third-party geocoding API. |

## Doctrine

- **Sidereal default**: True Pushya (Pushya-pakṣa) ayanāṁśa, mean nodes.
  Alternatives are options, never silent substitutions.
- **Nakṣatras and vargas are sidereal constructs** and are not served in
  the tropical frame.
- **Privacy by architecture**: this service is stateless. Birth data
  exists only inside a request and its computation; nothing is persisted
  and request bodies are never logged.
- **D144 and honesty**: classical practice treats D60 as the working
  ceiling because birth-time precision binds long before the varga does.
  We offer the extended series and we compute, per chart, exactly where
  that binding begins. The criticism is answered with arithmetic.

## Verify it yourself

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m app.atlas.build_atlas --source cities500   # ~10 MB quick start
# (omit --source for the full allCountries build, ~400 MB -- what CI and
# the Docker image ship)
bash scripts/fetch_sky_data.sh         # Sky Atlas raw data, ~15 MB
pytest -q                              # golden gates
uvicorn app.main:app --port 8500
```

Without the atlas build, `tests/test_atlas.py` self-skips; without the Sky
Atlas fetch, `tests/test_sky.py` self-skips. Run both steps above to see
the full suite pass instead of silently skipping those two files.

The golden test fixtures are the founding chart of RTA itself
(28 February 2025, Bradford), cross-validated against an independent
Jagannatha Hora computation to the arcsecond on the lagna.

## Lineage and licenses

- Computation: [PyJHora](https://github.com/naturalstupid/PyJHora)
  (AGPL-3.0) over [Swiss Ephemeris](https://www.astro.com/swisseph/)
  via pyswisseph (AGPL-3.0).
- Atlas data: [GeoNames](https://www.geonames.org/) (CC-BY 4.0).
- This service: AGPL-3.0-or-later. Every HTTP response carries an
  `X-AGPL-Source` header pointing here. If you run a modified copy as a
  network service, §13 obliges you to offer your modified source to its
  users — as we do.

## What this repository is not

The rtarhythm.com platform (site, accounts, orders, editorial prose of the
Instant readings, and the human practice behind RTA RHYTHM) is a separate
proprietary work that communicates with this service over HTTP. The math
is open; the craft is human.

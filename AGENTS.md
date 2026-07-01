# rta-compute

Open computational core of rtarhythm.com: sidereal/tropical charts, pancanga, dasha, birth-time
sensitivity, gochara gates. AGPL-3.0-or-later. FastAPI, Python 3.12+. Repo: XGeboX/rta-compute.

## Run / Test / Build

Venv install via `pip install -e ".[dev]"` FAILS on a fresh clone -- setuptools flat-layout
discovery errors on `Multiple top-level packages discovered: ['app', 'data']` (no
`[tool.setuptools]` packages config in pyproject.toml). Verified 2026-07-02. Use the CI-proven
direct install instead:

```
python3 -m venv .venv && source .venv/bin/activate
pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" \
  "PyJHora==4.6.0" "pyswisseph==2.10.3.2" "timezonefinder>=6.5" \
  "numpy==2.4.2" geocoder geopy pytz python-dateutil requests \
  pytest httpx
```

Atlas build first (required before most tests/runs; self-skips test_atlas.py/test_sky.py without it):
```
python -m app.atlas.build_atlas --source cities500   # fast, CI uses this
bash scripts/fetch_sky_data.sh                        # Sky Atlas raw data
```

Test: `python -m pytest tests -q` -- golden gates pinned to founding chart (28 Feb 2025 17:55:55,
Bradford UK); `tests/test_vara.py` gates pinned to the Drsti panchanga engine (never compute
panchanga by hand -- see root CLAUDE.md).

Run: `uvicorn app.main:app --port 8500` (health at `GET /v1/healthz`).

Docker: `Dockerfile` builds full atlas (`--source allCountries`) at image build, runs `pytest`
inside the build as a ship gate (build fails if tests fail).

## Guardrails

- **Stateless, no request-body logging.** Birth data lives only inside a request/response cycle.
- **Sidereal True Pushya is the default ayanamsa.** Alternatives are opt-in, never silent swaps.
- **AGPL boundary: editorial prose never enters this repo.** CI step `AGPL boundary check` greps
  `app/` for `INSTANT_TEMPLATE` and must return empty -- that marker belongs only to the private
  platform's templates. Do not introduce prose/copy generation here.
- **Byte-identical determinism.** No LLMs anywhere in this codebase's compute path. Identical
  input must produce identical output -- this is the auditable claim of the repo.
- **Multi-worker PROCESSES only, never threads** -- PyJHora holds global state serialized per
  process (see Dockerfile CMD comment).
- No em/en dashes in headings or shipped surfaces (docs, API errors, code comments) -- use `--`.
- No AI-attribution markers anywhere (commits, PRs, code, comments). Attribute to role/date only.
- No competitive framing in any shipped surface or doc.

## Git + deploy

GitHub Flow: feature branch -> PR -> Greptile 5/5 -> merge to `main` -> delete branch. `main` is
protected by CI (`test` job must pass before `docker` job runs). Worktree-per-agent for code
tasks: `~/hq/rta-compute-<task>`, never work directly in the shared `~/Thorn/rta-compute` tree
for feature branches.

CI (`.github/workflows/ci.yml`) on push/PR to `main`: install deps directly (not `pip install -e`),
build atlas (`cities500`), fetch sky data, run `pytest tests -q`, AGPL boundary grep. On `main`
push only: Docker build + push to `ghcr.io/xgebox/rta-compute:latest` and `:<sha>`.

Receipts for meaningful work: `python3 /Users/ani/Thorn/scripts/gebo/receipts/receipt.py`.

## Cross-repo notes

- Canonical open compute core. `rta-platform` (private Next.js) is the proprietary consumer --
  site, accounts, orders, editorial prose -- and talks to this service only over HTTP. Editorial
  content belongs there, never here.
- `rta-khagola` (WebGPU pancanga renderer) and `hermes-deploy` (Drsti pancanga server on Sani,
  `:9999`) are separate consumers/siblings; do not duplicate their pancanga logic here.
- Living cross-session context (decisions, session notes, project state) lives in the private
  `x-gebo` vault repo (`~/Thorn/X Gebo`, github.com/XGeboX/x-gebo), not in this repo.

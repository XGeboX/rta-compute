# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
FROM python:3.12-slim AS base

# The byte-identical contract is scoped per image digest; the build stamps
# its commit so /healthz and every Instant response can name it.
ARG GIT_SHA=dev
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 RTA_ENGINE_SHA=$GIT_SHA
WORKDIR /srv

COPY pyproject.toml LICENSE README.md ./
# pyswisseph ships no slim-compatible wheel; it needs the full C/C++
# toolchain (gcc AND g++) to build, dropped again after install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir \
       "fastapi>=0.115" "uvicorn[standard]>=0.30" \
       "PyJHora==4.6.0" "pyswisseph==2.10.3.2" "timezonefinder>=6.5" \
       "numpy==2.4.2" geocoder geopy pytz python-dateutil requests \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# The sky gate needs its raw catalogs (about 15 MB; the script pins the star
# catalog by checksum). Without them test_sky.py skipped here and the gate
# passed unchecked. Fetched before the code is copied so a code change does
# not refetch; curl is only needed for the fetch. The data ships with its
# licenses (CC BY-SA and CC BY require the notice).
COPY scripts/fetch_sky_data.sh ./scripts/fetch_sky_data.sh
COPY data/sky/DATA-LICENSES.md ./data/sky/DATA-LICENSES.md
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && bash scripts/fetch_sky_data.sh \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY tests ./tests

# Build the atlas at image build (GeoNames allCountries, P-class filtered,
# CC-BY 4.0): every populated place on earth, so village-born clients
# resolve by name. The 400MB download layer is cached across CI runs.
RUN python -m app.atlas.build_atlas --data-dir /tmp/geonames \
       --source allCountries \
    && rm -rf /tmp/geonames

# The suite is the gate: an image that fails its golden tests must not ship.
# The workflow test needs .github files that the image does not ship.
RUN pip install --no-cache-dir pytest httpx \
    && RTA_REQUIRE_SKY=1 python -m pytest tests -q --ignore=tests/test_ci_gate.py

# Non-root at runtime. The atlas and data baked above stay root-owned and
# world-readable; the service only reads them (the atlas opens mode=ro). A
# chown -R here would copy the whole atlas into a second layer.
RUN useradd --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 8500
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request as u; \
sys.exit(0 if u.urlopen('http://127.0.0.1:8500/v1/healthz', timeout=3).status == 200 else 1)"
# Multiple worker PROCESSES (never threads) — PyJhora global state is
# serialized per process by the frame lock.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500", "--workers", "4"]

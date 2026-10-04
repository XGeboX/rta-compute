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

COPY app ./app
COPY tests ./tests

# Build the atlas at image build (GeoNames allCountries, P-class filtered,
# CC-BY 4.0): every populated place on earth, so village-born clients
# resolve by name. The 400MB download layer is cached across CI runs.
RUN python -m app.atlas.build_atlas --data-dir /tmp/geonames \
       --source allCountries \
    && rm -rf /tmp/geonames

# The suite is the gate: an image that fails its golden tests must not ship.
RUN pip install --no-cache-dir pytest httpx && python -m pytest tests -q

# Non-root at runtime. Atlas and any fetched data are baked at build time
# above, while running as root; chown once, then drop privilege for good.
RUN useradd --no-create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /srv
USER app

EXPOSE 8500
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request as u; \
sys.exit(0 if u.urlopen('http://127.0.0.1:8500/v1/healthz', timeout=3).status == 200 else 1)"
# Multiple worker PROCESSES (never threads) — PyJhora global state is
# serialized per process by the frame lock.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500", "--workers", "4"]

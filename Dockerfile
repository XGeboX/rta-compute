# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

COPY pyproject.toml LICENSE README.md ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115" "uvicorn[standard]>=0.30" \
    "PyJHora==4.6.0" "pyswisseph==2.10.3.2" "timezonefinder>=6.5"

COPY app ./app
COPY tests ./tests

# Build the atlas at image build (GeoNames cities500, CC-BY 4.0).
RUN python -m app.atlas.build_atlas --data-dir /tmp/geonames \
    && rm -rf /tmp/geonames

# The suite is the gate: an image that fails its golden tests must not ship.
RUN pip install --no-cache-dir pytest httpx && python -m pytest tests -q

EXPOSE 8500
# Multiple worker PROCESSES (never threads) — PyJhora global state is
# serialized per process by the frame lock.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500", "--workers", "4"]

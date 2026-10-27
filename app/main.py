#!/usr/bin/env python3
# This file is part of rta-compute.
#
# rta-compute is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details: LICENSE.
"""rta-compute: the open computational core of rtarhythm.com.

Computed, not generated. Sidereal and tropical chart computation, pañcāṅga,
five-level Vimśottarī, classical gochara gates, birth-time sensitivity, and
the deterministic Instant rule engine, all auditable against this source.

Privacy: this service is stateless. Birth data exists only inside a request
and its computation; nothing is persisted, request bodies are never logged.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

SOURCE_URL = os.environ.get(
    "RTA_COMPUTE_SOURCE_URL", "https://github.com/XGeboX/rta-compute")

app = FastAPI(
    title="rta-compute",
    summary="The open computational core of rtarhythm.com, computed, not generated.",
    version="0.1.0",
    license_info={"name": "AGPL-3.0-or-later",
                  "url": "https://www.gnu.org/licenses/agpl-3.0.html"},
)

_origins = [o.strip() for o in os.environ.get(
    "RTA_CORS_ORIGINS", "https://rtarhythm.com,https://www.rtarhythm.com,http://localhost:3000"
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)


@app.middleware("http")
async def agpl_source_header(request, call_next):
    """AGPL §13: every response names where the running source lives."""
    response = await call_next(request)
    response.headers["X-AGPL-Source"] = SOURCE_URL
    return response


app.include_router(router, prefix="/v1")

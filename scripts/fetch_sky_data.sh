#!/bin/bash
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
# Fetch the Sky Atlas raw datasets into data/sky/raw/ (licenses:
# data/sky/DATA-LICENSES.md). Idempotent; ~15MB total.
set -euo pipefail

RAW="$(cd "$(dirname "$0")/.." && pwd)/data/sky/raw"
mkdir -p "$RAW"

fetch() {
  local url="$1" out="$2"
  if [ -s "$RAW/$out" ]; then
    echo "have $out"
    return
  fi
  echo "fetching $out"
  curl -fsSL -o "$RAW/$out" "$url"
}

# AT-HYG v3.3 was replaced by v4.0 on upstream's main branch (25-07-2026) and
# its branch URL now returns 404. Pin the last v3.3 revision and its checksum
# so the star catalog can never change underneath the sky tests silently.
ATHYG_COMMIT=fc08ca5a74ff6e595dab75a03a5ff3dc02b2793e
ATHYG_SHA256=7fa789a1d30ab0ce94ea38c55cab87bf3dc10cb46bfd9409e198a5c00ab43df2
fetch "https://codeberg.org/astronexus/athyg/media/commit/$ATHYG_COMMIT/data/subsets/hyglike_from_athyg_v33.csv.gz" \
      "hyglike_from_athyg_v33.csv.gz"
fetch "https://raw.githubusercontent.com/dcf21/constellation-stick-figures/master/constellation_lines_iau.dat" \
      "constellation_lines_iau.dat"
fetch "https://cdsarc.cds.unistra.fr/ftp/VI/49/bound_20.dat.gz" \
      "bound_20.dat.gz"
if [ -s "$RAW/bound_20.dat.gz" ]; then
  gunzip -f "$RAW/bound_20.dat.gz"
fi

# sanity: the gz is real and the VI/49 row count is the regression value
gunzip -t "$RAW/hyglike_from_athyg_v33.csv.gz"
if command -v sha256sum >/dev/null; then
  sum=$(sha256sum "$RAW/hyglike_from_athyg_v33.csv.gz" | cut -d' ' -f1)
else
  sum=$(shasum -a 256 "$RAW/hyglike_from_athyg_v33.csv.gz" | cut -d' ' -f1)
fi
if [ "$sum" != "$ATHYG_SHA256" ]; then
  echo "AT-HYG v3.3 checksum mismatch: got $sum" >&2
  exit 1
fi
rows=$(wc -l < "$RAW/bound_20.dat" | tr -d ' ')
if [ "$rows" != "12948" ]; then
  echo "VI/49 regression: expected 12948 rows, got $rows" >&2
  exit 1
fi
echo "sky raw data ready in $RAW"

#!/bin/bash
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
# Fetch the Sky Atlas raw datasets into data/sky/raw/ (licenses:
# data/sky/DATA-LICENSES.md). Idempotent; ~15MB total.
set -euo pipefail

RAW="$(cd "$(dirname "$0")/.." && pwd)/data/sky/raw"
mkdir -p "$RAW"

# fetch <file> <source> [<source>...]: sources are tried in order, so one
# server being down does not fail the run while another holds the same bytes.
# The download lands under a second name first; a transfer cut short must not
# be taken for the file on the next run.
fetch() {
  local out="$1" url
  shift
  if [ -s "$RAW/$out" ]; then
    echo "have $out"
    return
  fi
  for url in "$@"; do
    echo "fetching $out from $url"
    if curl -fsSL --connect-timeout 20 -o "$RAW/$out.part" "$url"; then
      mv "$RAW/$out.part" "$RAW/$out"
      return
    fi
    echo "no answer from $url" >&2
  done
  echo "could not fetch $out" >&2
  return 1
}

sha256_of() {
  if command -v sha256sum >/dev/null; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

# AT-HYG v3.3 was replaced by v4.0 on upstream's main branch (25-07-2026) and
# its branch URL now returns 404. Pin the last v3.3 revision and its checksum
# so the star catalog can never change underneath the sky tests silently.
ATHYG_COMMIT=fc08ca5a74ff6e595dab75a03a5ff3dc02b2793e
ATHYG_SHA256=7fa789a1d30ab0ce94ea38c55cab87bf3dc10cb46bfd9409e198a5c00ab43df2
fetch "hyglike_from_athyg_v33.csv.gz" \
      "https://codeberg.org/astronexus/athyg/media/commit/$ATHYG_COMMIT/data/subsets/hyglike_from_athyg_v33.csv.gz"
fetch "constellation_lines_iau.dat" \
      "https://raw.githubusercontent.com/dcf21/constellation-stick-figures/master/constellation_lines_iau.dat"

# VI/49 is served by CDS in Strasbourg, with the VizieR mirror at CfA Harvard
# as a second source: CDS did not answer for hours on 17-11-2026 and every CI
# run failed on this one file. A second source needs a pin, so the checksum is
# of the unpacked file (a mirror may pack it differently): the copy fetched
# from CDS on 12-06-2026 and the CfA copy read on 17-11-2026 both have it.
# The unpacked file is the one that counts as present, so a run that already
# has it asks no server.
BOUND_SHA256=425e75a944260d4b08819a6e12c9990890981288a44068f8c4499ac64986c513
if [ -s "$RAW/bound_20.dat" ]; then
  echo "have bound_20.dat"
else
  fetch "bound_20.dat.gz" \
        "https://cdsarc.cds.unistra.fr/ftp/VI/49/bound_20.dat.gz" \
        "https://vizier.cfa.harvard.edu/ftp/cats/VI/49/bound_20.dat.gz"
  gunzip -f "$RAW/bound_20.dat.gz"
fi

# sanity: the gz is real, both catalogues are the pinned bytes, and the VI/49
# row count is the regression value
gunzip -t "$RAW/hyglike_from_athyg_v33.csv.gz"
sum=$(sha256_of "$RAW/hyglike_from_athyg_v33.csv.gz")
if [ "$sum" != "$ATHYG_SHA256" ]; then
  echo "AT-HYG v3.3 checksum mismatch: got $sum" >&2
  exit 1
fi
sum=$(sha256_of "$RAW/bound_20.dat")
if [ "$sum" != "$BOUND_SHA256" ]; then
  echo "VI/49 checksum mismatch: got $sum" >&2
  exit 1
fi
rows=$(wc -l < "$RAW/bound_20.dat" | tr -d ' ')
if [ "$rows" != "12948" ]; then
  echo "VI/49 regression: expected 12948 rows, got $rows" >&2
  exit 1
fi
echo "sky raw data ready in $RAW"

#!/bin/bash
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
# Fetch the Sky Atlas raw datasets into data/sky/raw/ (licenses:
# data/sky/DATA-LICENSES.md). Idempotent; ~15MB total.
set -euo pipefail

RAW="${SKY_RAW_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data/sky/raw}"
mkdir -p "$RAW"

# Without a hasher no file can be judged. Stopping here keeps a good file
# from being moved aside and every server from being blamed for a mismatch.
if command -v sha256sum >/dev/null; then
  hasher=(sha256sum)
elif command -v shasum >/dev/null; then
  hasher=(shasum -a 256)
else
  echo "hashing failed: neither sha256sum nor shasum was found" >&2
  exit 1
fi

# The file goes in on standard input so that no path reaches the hasher's
# output: GNU sha256sum marks its line when a path holds a backslash or a
# newline. A digest that cannot be taken says nothing about the file, so
# callers stop on it and never read it as a mismatch.
sha256_of() {
  local line
  if ! line="$("${hasher[@]}" < "$1")"; then
    echo "hashing failed for $1" >&2
    return 1
  fi
  echo "${line%% *}"
}

# BSD wc pads its count with spaces, which a message must not carry.
size_of() {
  wc -c < "$1" | tr -d ' '
}

# fetch <file> <pin> <gzip|raw> <byte-cap> <whitespace-separated-sources>
# Cache entries and fresh transfers earn the final name by the same pin.
# A server returning the wrong bytes must not prevent a good mirror winning.
fetch() {
  local out="$1" pin="$2" format="$3" cap="$4" url candidate failure
  local final="$RAW/$out" part="$RAW/$out.part" unpacked="$RAW/$out.unpacked.part"
  local path seen reason left newline=$'\n'
  local -a sources transfer
  # A list may span lines, so read runs to its end; with no NUL to stop at it
  # then reports the end of input, which is not a failure.
  IFS=$' \t\n' read -r -d '' -a sources <<< "$5" || true
  # rm -f stops the script on a directory with rm's words and no reason, and
  # a directory in the store is not this script's to delete.
  for path in "$final" "$part" "$unpacked"; do
    if [ -e "$path" ] && [ ! -f "$path" ]; then
      echo "$path is not a regular file; remove it and run again" >&2
      exit 1
    fi
  done
  rm -f "$part" "$unpacked"
  if [ -e "$final" ]; then
    seen="$(sha256_of "$final")" || exit 1
    if [ "$seen" = "$pin" ]; then
      echo "have $out"
      return
    fi
    mv -f "$final" "$final.bad"
    echo "$out checksum mismatch (sha256 $seen, $(size_of "$final.bad") bytes);" \
         "moved to $out.bad" >&2
    # A restored cache is saved again only after a miss, so a bad entry is
    # healed on every run and never replaced while the step stays green.
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
      echo "::warning::the restored cache holds a bad copy of $out;" \
           "delete the cache entry so a verified copy is saved"
    fi
  fi
  if [ "${#sources[@]}" -eq 0 ]; then
    echo "no sources for $out" >&2
    exit 1
  fi
  left="${#sources[@]}"
  for url in "${sources[@]}"; do
    left="$((left - 1))"
    echo "fetching $out from $url"
    failure=""
    candidate="$part"
    # A stall rule ends a source that connects and then goes quiet, so the
    # total limit can be loose enough for the 15 MB archive on a slow line.
    transfer=(-fsSL --connect-timeout 20 --speed-limit 1024 --speed-time 30
              --max-time 600 --max-filesize "$cap")
    # A retry spent while a mirror waits only delays the mirror.
    if [ "$left" -eq 0 ]; then
      transfer+=(--retry 2 --retry-max-time 120)
    fi
    # A transfer reported good may leave no file; an empty one fails its pin
    # like any other wrong answer, so the next source is still asked.
    : > "$part"
    # After --url an entry that begins with a dash cannot be taken for an option.
    if ! reason="$(curl "${transfer[@]}" -o "$part" --url "$url" 2>&1)"; then
      # A reason may span lines, and the log keeps one line per failed source.
      failure="curl failed (transfer or size cap): ${reason//$newline/ }"
    elif [ "$(wc -c < "$part")" -gt "$cap" ]; then
      # --max-filesize refuses up front only a declared length, and older
      # curl lets a body of no declared length run past it.
      failure="transfer size cap exceeded"
    elif [ "$format" = "gzip" ]; then
      candidate="$unpacked"
      # The extra byte distinguishes a file at the cap from a clipped stream;
      # pipefail also rejects a truncated gzip even if its output has the pin.
      if ! gzip -dc "$part" 2>/dev/null | head -c "$((cap + 1))" > "$unpacked"; then
        failure="unpack failed or size cap exceeded"
      elif [ "$(wc -c < "$unpacked")" -gt "$cap" ]; then
        failure="unpacked size cap exceeded"
      fi
    fi
    if [ -z "$failure" ]; then
      seen="$(sha256_of "$candidate")" || exit 1
      if [ "$seen" = "$pin" ]; then
        mv "$candidate" "$final"
        rm -f "$part" "$unpacked"
        return
      fi
      failure="checksum mismatch (sha256 $seen, $(size_of "$candidate") bytes)"
    fi
    rm -f "$part" "$unpacked"
    echo "$out source $url failed: $failure" >&2
  done
  echo "could not fetch $out: every source failed" >&2
  return 1
}

# Source overrides support offline tests; they never override the pins.
# AT-HYG v3.3 was replaced by v4.0 on upstream's main branch (25-07-2026) and
# its branch URL now returns 404. Pin the last v3.3 revision and its checksum
# so the star catalog can never change underneath the sky tests silently.
ATHYG_COMMIT=fc08ca5a74ff6e595dab75a03a5ff3dc02b2793e
ATHYG_SHA256=7fa789a1d30ab0ce94ea38c55cab87bf3dc10cb46bfd9409e198a5c00ab43df2
fetch "hyglike_from_athyg_v33.csv.gz" \
      "$ATHYG_SHA256" raw "$((32 * 1024 * 1024))" \
      "${SKY_SOURCES_ATHYG:-https://codeberg.org/astronexus/athyg/media/commit/$ATHYG_COMMIT/data/subsets/hyglike_from_athyg_v33.csv.gz}"

# Pin the last commit touching the figures so a branch update cannot change
# the sky silently. Checked on 17-11-2026: this address and the copy fetched
# from master that day both had this checksum (11,626 bytes).
FIGURES_COMMIT=a2ee540c95e2c689615fa745494bca1a80756e64
FIGURES_SHA256=e7b9b064c967a53913ef1862626aa3385094cf6b6784e98ba67558af763193fc
fetch "constellation_lines_iau.dat" \
      "$FIGURES_SHA256" raw "$((1024 * 1024))" \
      "${SKY_SOURCES_FIGURES:-https://raw.githubusercontent.com/dcf21/constellation-stick-figures/$FIGURES_COMMIT/constellation_lines_iau.dat}"

# VI/49 is served by CDS in Strasbourg, with the VizieR mirror at CfA Harvard
# as a second source: CDS did not answer for hours on 17-11-2026 and every CI
# run failed on this one file. A second source needs a pin, so the checksum is
# of the unpacked file (a mirror may pack it differently): the copy fetched
# from CDS on 12-06-2026 and the CfA copy read on 17-11-2026 both have it.
# The unpacked file is the one that counts as present, so a run that already
# has it asks no server.
BOUND_SHA256=425e75a944260d4b08819a6e12c9990890981288a44068f8c4499ac64986c513
fetch "bound_20.dat" "$BOUND_SHA256" gzip "$((4 * 1024 * 1024))" \
      "${SKY_SOURCES_BOUND:-https://cdsarc.cds.unistra.fr/ftp/VI/49/bound_20.dat.gz https://vizier.cfa.harvard.edu/ftp/cats/VI/49/bound_20.dat.gz}"

# Keep the row regression as a sanity check alongside the byte-level pins.
rows=$(wc -l < "$RAW/bound_20.dat" | tr -d ' ')
if [ "$rows" != "12948" ]; then
  echo "VI/49 regression: expected 12948 rows, got $rows" >&2
  exit 1
fi
echo "sky raw data ready in $RAW"

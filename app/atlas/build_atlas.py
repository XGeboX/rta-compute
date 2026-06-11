#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Build the self-hosted atlas: GeoNames cities500 -> SQLite FTS5.

Run once at image build (or locally):
    python3 -m app.atlas.build_atlas [--data-dir /tmp/geonames]

Produces app/atlas/atlas.db with an FTS5 table `places`:
    name (indexed, includes diacritic-folded alternates), country, admin1,
    lat, lon, tz (IANA, via timezonefinder), population.

GeoNames data is CC-BY 4.0 (https://www.geonames.org/) — attribution is
carried in the API docs and the platform's methodology page."""

import argparse
import csv
import io
import sqlite3
import sys
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

GEONAMES_URL = "https://download.geonames.org/export/dump/cities500.zip"
DB_PATH = Path(__file__).parent / "atlas.db"


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).lower()


def build(data_dir: Path, db_path: Path = DB_PATH):
    data_dir.mkdir(parents=True, exist_ok=True)
    zpath = data_dir / "cities500.zip"
    if not zpath.exists():
        print(f"downloading {GEONAMES_URL} ...")
        urllib.request.urlretrieve(GEONAMES_URL, zpath)
    print("loading timezonefinder ...")
    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()

    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE VIRTUAL TABLE places USING fts5("
        "terms, display UNINDEXED, country UNINDEXED, admin1 UNINDEXED, "
        "lat UNINDEXED, lon UNINDEXED, tz UNINDEXED, population UNINDEXED, "
        "tokenize='unicode61 remove_diacritics 2')")

    n = 0
    with zipfile.ZipFile(zpath) as zf:
        with zf.open("cities500.txt") as fh:
            reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"),
                                delimiter="\t", quoting=csv.QUOTE_NONE)
            batch = []
            for row in reader:
                # geonames columns: 1=name 3=alternatenames 4=lat 5=lon
                # 8=country 10=admin1 14=population 17=timezone
                name, alts = row[1], row[3]
                lat, lon = float(row[4]), float(row[5])
                country, admin1 = row[8], row[10]
                pop = int(row[14] or 0)
                tz = row[17] or tf.timezone_at(lat=lat, lng=lon) or ""
                # index: primary name + folded form + a few alternates
                terms = {name, _fold(name)}
                for a in alts.split(",")[:12]:
                    a = a.strip()
                    if a and len(a) > 1:
                        terms.add(a)
                batch.append((" ; ".join(sorted(terms)), name, country,
                              admin1, lat, lon, tz, pop))
                n += 1
                if len(batch) >= 5000:
                    con.executemany(
                        "INSERT INTO places VALUES (?,?,?,?,?,?,?,?)", batch)
                    batch.clear()
            if batch:
                con.executemany(
                    "INSERT INTO places VALUES (?,?,?,?,?,?,?,?)", batch)
    con.commit()
    con.close()
    print(f"atlas built: {n} places -> {db_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/tmp/geonames")
    ap.add_argument("--out", default=str(DB_PATH))
    args = ap.parse_args()
    build(Path(args.data_dir), Path(args.out))
    sys.exit(0)

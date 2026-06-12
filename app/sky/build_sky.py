#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Build the Sky Atlas static assets.

    python3 -m app.sky.build_sky --raw-dir data/sky/raw --out dist/sky

Inputs (downloaded by scripts/fetch_sky_data.sh, licenses in
data/sky/DATA-LICENSES.md):
    hyglike_from_athyg_v33.csv.gz   ATHYG v3.3 HYGLike (CC BY-SA 4.0)
    constellation_lines_iau.dat     dcf21 IAU stick figures (CC BY 4.0)
    bound_20.dat                    VizieR VI/49 J2000 boundaries

Outputs: content-hashed stars/lines/bounds binaries + asterisms.json +
names.json + sky-manifest.json (the only mutable name).
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from . import asterisms, catalog, figures


def _hashed(path: Path) -> Path:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    target = path.with_name(f"{path.stem}.{digest}{path.suffix}")
    shutil.move(path, target)
    return target


def build(raw_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    lines_raw = figures.parse_lines(raw_dir / "constellation_lines_iau.dat")
    force = figures.referenced_hips(lines_raw)
    stars = catalog.load_athyg(
        raw_dir / "hyglike_from_athyg_v33.csv.gz", force_hips=force)

    stars_tmp = out_dir / "stars-v1.bin"
    hip_index = catalog.encode(
        stars, stars_tmp, yogatara_hips=asterisms.yogatara_hips())

    lines_tmp = out_dir / "lines-iau-v1.bin"
    pair_count, dropped = figures.encode_lines(lines_raw, hip_index, lines_tmp)

    strips = figures.parse_boundaries(raw_dir / "bound_20.dat")
    bounds_tmp = out_dir / "bounds-iau-v1.bin"
    point_count = figures.encode_boundaries(strips, bounds_tmp)

    asterisms_tmp = out_dir / "asterisms-v1.json"
    asterisms_tmp.write_text(json.dumps(
        asterisms.as_manifest(), ensure_ascii=False, indent=1))

    names_tmp = out_dir / "names-v1.json"
    names = {str(hip_index[s["hip"]]):
             {"proper": s["proper"], "bayer": s["bayer"], "con": s["con"]}
             for s in stars
             if s["hip"] in hip_index and (s["proper"] or s["bayer"])}
    names_tmp.write_text(json.dumps(names, ensure_ascii=False))

    entries = {}
    for logical, tmp in [("stars", stars_tmp), ("lines", lines_tmp),
                         ("bounds", bounds_tmp),
                         ("asterisms", asterisms_tmp),
                         ("names", names_tmp)]:
        hashed = _hashed(tmp)
        entries[logical] = {
            "file": hashed.name,
            "sha256": hashlib.sha256(hashed.read_bytes()).hexdigest(),
            "bytes": hashed.stat().st_size,
        }
    manifest = {
        "version": 1,
        "epoch_jd": catalog.EPOCH_JD,
        "counts": {"stars": len(stars), "line_pairs": pair_count,
                   "boundary_points": point_count,
                   "nakshatras": len(asterisms.NAKSHATRAS)},
        # no silent truncation: segments dropped over catalog gaps are
        # named here and budget-gated in the suite
        "dropped_line_hips": dropped,
        "license": {
            "stars": "ATHYG v3.3 (David Nash, astronexus.com), CC BY-SA 4.0",
            "lines": "IAU/Sky & Telescope via dcf21, CC BY 4.0",
            "bounds": "Davenhall & Leggett 1989, VizieR VI/49, "
                      "CDS DOI 10.26093/cds/vizier",
        },
        "assets": entries,
    }
    (out_dir / "sky-manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/sky/raw")
    ap.add_argument("--out", default="dist/sky")
    args = ap.parse_args()
    m = build(Path(args.raw_dir), Path(args.out))
    print(json.dumps(m["counts"]))
    sys.exit(0)

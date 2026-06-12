# Sky data licenses

The AGPL-3.0 license of this repository covers the CODE. The datasets
below keep their own licenses and are not relicensed by inclusion;
processed artifacts derived from them inherit the stated terms.
`scripts/fetch_sky_data.sh` downloads them into `data/sky/raw/` (not
committed).

| Dataset | File | License | Attribution |
|---|---|---|---|
| ATHYG v3.3, HYGLike subset | `hyglike_from_athyg_v33.csv.gz` | CC BY-SA 4.0 | David Nash, The Astronomy Nexus (astronexus.com); Gaia DR3 astrometry: ESA/Gaia/DPAC. Star assets built from it (stars-v1 binaries) are published under CC BY-SA 4.0. |
| IAU constellation stick figures | `constellation_lines_iau.dat` | CC BY 4.0 | IAU and Sky & Telescope magazine (Roger Sinnott & Rick Fienberg); machine-readable figures: Dominic Ford (dcf21/constellation-stick-figures). |
| Constellation boundaries (J2000) | `bound_20.dat` | CDS/VizieR usage terms, cited | Davenhall A.C., Leggett S.K. 1989, VizieR VI/49; VizieR catalogue access tool, CDS, Strasbourg (DOI 10.26093/cds/vizier). |

The yogatara identifications in `app/sky/asterisms.py` are traditional;
each entry is cross-checked at test time against the Swiss Ephemeris
fixed-star registry (sefstars), which encodes the classical names. The
Surya Siddhanta dhruva coordinates ship once transcribed from the text;
the field is pending, never invented.

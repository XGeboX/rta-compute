#!/usr/bin/env python3
# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""The 28 nakshatra yogatara table.

Identification discipline: every entry carries `swe_name`, the Swiss
Ephemeris fixed-star designator, and the test suite cross-checks the
catalog position of `hip` against swe.fixstar2_ut(swe_name) to within
arcseconds. A misremembered HIP cannot survive the gates; the registry
of record is the ephemeris itself, which encodes the traditional
identifications.

Variants: where the tradition genuinely differs on the yogatara, the
alternates are carried in `variant_hips` with a note, never silently
chosen. `ss_polar` (the Surya Siddhanta VIII dhruva coordinates) ships
None until transcribed from the text itself; the citation-completeness
gate treats it as pending, not absent.

Spans are sidereal degrees. The Abhijit span follows the common
convention (last quarter of Uttara-Ashadha through the first 1/15th of
Shravana); conventions differ and the variant note says so.
"""

CITE_SWE = {"source": "Swiss Ephemeris fixed-star registry (sefstars)",
            "note": "traditional identification, cross-checked in gates"}
CITE_PVR = {"source": "PVR Narasimha Rao, Vedic Astrology: An Integrated "
                      "Approach", "note": "yogatara tables"}

NAKSHATRAS: list[dict] = [
    {"id": 1, "name_iast": "Aśvinī", "deity": "Aśvinīkumārau",
     "yogatara_hip": 8903, "swe_name": "Sheratan", "variant_hips": [],
     "span_sid": (0.0, 13.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 2, "name_iast": "Bharaṇī", "deity": "Yama",
     "yogatara_hip": 13209, "swe_name": "Bharani", "variant_hips": [],
     "span_sid": (13.333333, 26.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 3, "name_iast": "Kṛttikā", "deity": "Agni",
     "yogatara_hip": 17702, "swe_name": "Alcyone", "variant_hips": [],
     "span_sid": (26.666667, 40.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 4, "name_iast": "Rohiṇī", "deity": "Prajāpati",
     "yogatara_hip": 21421, "swe_name": "Aldebaran", "variant_hips": [],
     "span_sid": (40.0, 53.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 5, "name_iast": "Mṛgaśīrṣa", "deity": "Soma",
     "yogatara_hip": 26207, "swe_name": ",laOri", "variant_hips": [],
     "span_sid": (53.333333, 66.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 6, "name_iast": "Ārdrā", "deity": "Rudra",
     "yogatara_hip": 27989, "swe_name": "Betelgeuse", "variant_hips": [],
     "span_sid": (66.666667, 80.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 7, "name_iast": "Punarvasu", "deity": "Aditi",
     "yogatara_hip": 37826, "swe_name": "Pollux", "variant_hips": [],
     "span_sid": (80.0, 93.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 8, "name_iast": "Puṣya", "deity": "Bṛhaspati",
     "yogatara_hip": 42911, "swe_name": ",deCnc", "variant_hips": [],
     "span_sid": (93.333333, 106.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 9, "name_iast": "Āśleṣā", "deity": "Sarpāḥ",
     "yogatara_hip": 43109, "swe_name": ",epHya",
     "variant_hips": [46390],
     "variant_note": "epsilon Hydrae (head) vs Alphard (alpha Hydrae); "
                     "traditions differ",
     "span_sid": (106.666667, 120.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 10, "name_iast": "Maghā", "deity": "Pitṛs",
     "yogatara_hip": 49669, "swe_name": "Regulus", "variant_hips": [],
     "span_sid": (120.0, 133.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 11, "name_iast": "Pūrva Phālgunī", "deity": "Bhaga",
     "yogatara_hip": 54872, "swe_name": "Zosma", "variant_hips": [],
     "span_sid": (133.333333, 146.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 12, "name_iast": "Uttara Phālgunī", "deity": "Aryaman",
     "yogatara_hip": 57632, "swe_name": "Denebola", "variant_hips": [],
     "span_sid": (146.666667, 160.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 13, "name_iast": "Hasta", "deity": "Savitṛ",
     "yogatara_hip": 60965, "swe_name": ",deCrv",
     "variant_hips": [59803],
     "variant_note": "delta Corvi vs gamma Corvi (Gienah); both attested",
     "span_sid": (160.0, 173.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 14, "name_iast": "Citrā", "deity": "Tvaṣṭṛ",
     "yogatara_hip": 65474, "swe_name": "Spica", "variant_hips": [],
     "span_sid": (173.333333, 186.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 15, "name_iast": "Svātī", "deity": "Vāyu",
     "yogatara_hip": 69673, "swe_name": "Arcturus", "variant_hips": [],
     "span_sid": (186.666667, 200.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 16, "name_iast": "Viśākhā", "deity": "Indrāgnī",
     "yogatara_hip": 72622, "swe_name": "Zuben Elgenubi",
     "variant_hips": [74785],
     "variant_note": "alpha Librae vs beta Librae; both attested",
     "span_sid": (200.0, 213.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 17, "name_iast": "Anurādhā", "deity": "Mitra",
     "yogatara_hip": 78401, "swe_name": ",deSco", "variant_hips": [],
     "span_sid": (213.333333, 226.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 18, "name_iast": "Jyeṣṭhā", "deity": "Indra",
     "yogatara_hip": 80763, "swe_name": "Antares", "variant_hips": [],
     "span_sid": (226.666667, 240.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 19, "name_iast": "Mūla", "deity": "Nirṛti",
     "yogatara_hip": 85927, "swe_name": "Shaula", "variant_hips": [],
     "span_sid": (240.0, 253.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 20, "name_iast": "Pūrva Āṣāḍhā", "deity": "Āpas",
     "yogatara_hip": 89931, "swe_name": ",deSgr", "variant_hips": [],
     "span_sid": (253.333333, 266.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 21, "name_iast": "Uttara Āṣāḍhā", "deity": "Viśvedevāḥ",
     "yogatara_hip": 92855, "swe_name": "Nunki", "variant_hips": [],
     "span_sid": (266.666667, 280.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 28, "name_iast": "Abhijit", "deity": "Brahmā",
     "yogatara_hip": 91262, "swe_name": "Vega", "variant_hips": [],
     "span_sid": (276.666667, 280.888889),
     "variant_note": "span conventions differ; this is the common "
                     "last-quarter-of-UA through 1/15th-of-Shravana scheme",
     "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 22, "name_iast": "Śravaṇa", "deity": "Viṣṇu",
     "yogatara_hip": 97649, "swe_name": "Altair", "variant_hips": [],
     "span_sid": (280.0, 293.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 23, "name_iast": "Dhaniṣṭhā", "deity": "Vasavaḥ",
     "yogatara_hip": 101769, "swe_name": ",beDel", "variant_hips": [],
     "span_sid": (293.333333, 306.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 24, "name_iast": "Śatabhiṣaj", "deity": "Varuṇa",
     "yogatara_hip": 112961, "swe_name": ",laAqr", "variant_hips": [],
     "span_sid": (306.666667, 320.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 25, "name_iast": "Pūrva Bhādrapadā", "deity": "Aja Ekapāda",
     "yogatara_hip": 113963, "swe_name": "Markab", "variant_hips": [],
     "span_sid": (320.0, 333.333333), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 26, "name_iast": "Uttara Bhādrapadā", "deity": "Ahir Budhnya",
     "yogatara_hip": 1067, "swe_name": "Algenib", "variant_hips": [677],
     "variant_note": "gamma Pegasi vs alpha Andromedae (Alpheratz); "
                     "both attested",
     "span_sid": (333.333333, 346.666667), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
    {"id": 27, "name_iast": "Revatī", "deity": "Pūṣan",
     "yogatara_hip": 5737, "swe_name": ",zePsc", "variant_hips": [],
     "span_sid": (346.666667, 360.0), "ss_polar": None,
     "citations": [CITE_SWE, CITE_PVR]},
]


def yogatara_hips() -> set[int]:
    return {n["yogatara_hip"] for n in NAKSHATRAS} | \
           {h for n in NAKSHATRAS for h in n["variant_hips"]}


def as_manifest() -> list[dict]:
    """The asterisms.json payload: everything the renderer needs, nothing
    it doesn't. Member figures land in S3."""
    return [{
        "id": n["id"],
        "name_iast": n["name_iast"],
        "deity": n["deity"],
        "yogatara_hip": n["yogatara_hip"],
        "variant_hips": n["variant_hips"],
        "variant_note": n.get("variant_note"),
        "span_sid": n["span_sid"],
        "ss_polar": n["ss_polar"],
        "citations": n["citations"],
        "culture": "vedic",
    } for n in NAKSHATRAS]

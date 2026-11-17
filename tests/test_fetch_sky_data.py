# This file is part of rta-compute. AGPL-3.0-or-later; see LICENSE.
"""Exercise the shipping fetcher with local sources, never outside servers."""

import gzip
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "ATHYG": (
        "hyglike_from_athyg_v33.csv.gz",
        "7fa789a1d30ab0ce94ea38c55cab87bf3dc10cb46bfd9409e198a5c00ab43df2",
        32 * 1024 * 1024,
    ),
    "FIGURES": (
        "constellation_lines_iau.dat",
        "e7b9b064c967a53913ef1862626aa3385094cf6b6784e98ba67558af763193fc",
        1024 * 1024,
    ),
    "BOUND": (
        "bound_20.dat",
        "425e75a944260d4b08819a6e12c9990890981288a44068f8c4499ac64986c513",
        4 * 1024 * 1024,
    ),
}


@pytest.fixture(scope="module")
def good_sources(tmp_path_factory):
    raw = ROOT / "data" / "sky" / "raw"
    missing = [name for name, _, _ in DATASETS.values() if not (raw / name).is_file()]
    if missing:
        pytest.skip("sky raw data not fetched: " + ", ".join(missing))
    sources = tmp_path_factory.mktemp("sky sources")
    contents, paths = {}, {}
    for key, (name, pin, _) in DATASETS.items():
        data = (raw / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == pin, f"fixture pin mismatch: {name}"
        contents[key] = data
        paths[key] = sources / (name + ".gz" if key == "BOUND" else name)
        paths[key].write_bytes(gzip.compress(data) if key == "BOUND" else data)
    return contents, paths


@pytest.fixture
def fetch(tmp_path, good_sources):
    real_curl = shutil.which("curl")
    if not real_curl:
        pytest.skip("curl is required to exercise the fetch script")
    raw = tmp_path / "raw data"
    raw.mkdir()
    calls = tmp_path / "curl-calls.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    # Even the red run must stay offline if the old script ignores the seams.
    curl.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" >> "$CURL_CALLS"\n'
        f'exec {shlex.quote(real_curl)} -q "$@" --proto \'=file\' --proto-redir \'=file\'\n'
    )
    curl.chmod(0o755)
    _, paths = good_sources

    def run(sources=None, pins=None):
        env = {**os.environ, "SKY_RAW_DIR": str(raw), "CURL_CALLS": str(calls),
               "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        env.update({f"SKY_SOURCES_{key}": path.as_uri() for key, path in paths.items()})
        for key, choices in (sources or {}).items():
            env[f"SKY_SOURCES_{key}"] = " ".join(path.as_uri() for path in choices)
        env.update(pins or {})
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "fetch_sky_data.sh")],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
        )

    return raw, calls, run


def assert_ready(raw, result):
    assert result.returncode == 0, result.stderr
    for name, pin, _ in DATASETS.values():
        assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == pin
    assert_no_temps(raw)


def assert_no_temps(raw):
    final_names = {name for name, _, _ in DATASETS.values()}
    allowed = final_names | {name + ".bad" for name in final_names}
    assert {path.name for path in raw.iterdir()} <= allowed


def test_good_sources(fetch):
    """Catch missing files, unverified publication and retained transfer artifacts."""
    raw, _, run = fetch
    assert_ready(raw, run())


@pytest.mark.parametrize("key", DATASETS)
@pytest.mark.parametrize("kind", ["missing", "html", "truncated", "other-content"])
def test_bad_source_tries_next(fetch, good_sources, tmp_path, key, kind):
    """Catch fallback limited to curl errors or acceptance of a damaged gzip stream."""
    raw, _, run = fetch
    _, paths = good_sources
    bad = tmp_path / "bad source"
    if kind == "html":
        bad.write_bytes(b"<html>maintenance</html>")
    elif kind == "truncated":
        archive = (paths["ATHYG"] if key == "ATHYG" else paths["BOUND"]).read_bytes()
        bad.write_bytes(archive[:-8])
    elif kind == "other-content":
        bad.write_bytes(gzip.compress(b"another catalogue\n"))
    result = run({key: [bad, paths[key]]})
    assert_ready(raw, result)
    assert bad.as_uri() in result.stderr
    assert "failed" in result.stderr


@pytest.mark.parametrize("key", DATASETS)
@pytest.mark.parametrize("cached_bad", [False, True])
def test_all_sources_wrong(fetch, tmp_path, key, cached_bad):
    """Catch poisoned final files surviving after every source has failed."""
    raw, _, run = fetch
    name, _, _ = DATASETS[key]
    if cached_bad:
        (raw / name).write_bytes(b"bad cached bytes")
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"<html>maintenance</html>")
    second.write_bytes(gzip.compress(b"wrong catalogue"))
    result = run({key: [first, second]})
    assert result.returncode != 0
    assert not (raw / name).exists()
    assert name in result.stderr
    assert first.as_uri() in result.stderr
    assert second.as_uri() in result.stderr
    if cached_bad:
        assert (raw / (name + ".bad")).read_bytes() == b"bad cached bytes"
    assert_no_temps(raw)


def test_verified_files_ask_no_source(fetch, good_sources, tmp_path):
    """Catch needless downloads or replacement of a verified cache entry."""
    raw, calls, run = fetch
    contents, _ = good_sources
    for key, (name, _, _) in DATASETS.items():
        (raw / name).write_bytes(contents[key])
    before = {path.name: path.stat() for path in raw.iterdir()}
    result = run({key: [tmp_path / "absent"] for key in DATASETS})
    assert_ready(raw, result)
    assert not calls.exists()
    for name, stat in before.items():
        assert f"have {name}" in result.stdout
        assert (raw / name).stat().st_ino == stat.st_ino
        assert (raw / name).stat().st_mtime_ns == stat.st_mtime_ns


@pytest.mark.parametrize("key", DATASETS)
def test_bad_final_is_quarantined_and_replaced(fetch, key):
    """Catch corrupt cached data being trusted, or blocking its own repair."""
    raw, _, run = fetch
    name, _, _ = DATASETS[key]
    (raw / name).write_bytes(b"bad cached bytes")
    (raw / (name + ".bad")).write_bytes(b"older bad bytes")
    result = run()
    assert_ready(raw, result)
    assert (raw / (name + ".bad")).read_bytes() == b"bad cached bytes"
    assert name in result.stderr
    assert ".bad" in result.stderr


@pytest.mark.parametrize("key", DATASETS)
def test_download_cap_tries_next(fetch, good_sources, tmp_path, key):
    """Catch a transfer rejected only by its checksum after exceeding the cap."""
    raw, _, run = fetch
    _, paths = good_sources
    _, _, cap = DATASETS[key]
    oversized = tmp_path / "oversized"
    with oversized.open("wb") as stream:
        stream.truncate(cap + 1)
    result = run({key: [oversized, paths[key]]})
    assert_ready(raw, result)
    assert oversized.as_uri() in result.stderr
    assert "cap" in result.stderr


def test_gzip_expansion_cap_tries_next(fetch, good_sources, tmp_path):
    """Catch a small gzip bypassing the disk bound during decompression."""
    raw, _, run = fetch
    _, paths = good_sources
    _, _, cap = DATASETS["BOUND"]
    oversized = tmp_path / "oversized.gz"
    oversized.write_bytes(gzip.compress(b"x" * (cap * 4)))
    assert oversized.stat().st_size < cap
    result = run({"BOUND": [oversized, paths["BOUND"]]})
    assert_ready(raw, result)
    assert oversized.as_uri() in result.stderr
    assert "cap" in result.stderr


def test_cache_leftovers_do_no_harm(fetch):
    """Catch stale partial transfers being accepted or blocking a fresh attempt."""
    raw, _, run = fetch
    for name, _, _ in DATASETS.values():
        for suffix in (".part", ".unpacked.part", ".bad"):
            (raw / (name + suffix)).write_bytes(b"old bytes")
    assert_ready(raw, run())
    for name, _, _ in DATASETS.values():
        assert (raw / (name + ".bad")).read_bytes() == b"old bytes"


@pytest.mark.parametrize("key", DATASETS)
def test_environment_cannot_replace_pin(fetch, tmp_path, key):
    """Catch source overrides being allowed to redefine which bytes are trusted."""
    raw, _, run = fetch
    data = b"wrong bytes\n"
    wrong = tmp_path / "wrong"
    wrong.write_bytes(gzip.compress(data) if key == "BOUND" else data)
    result = run({key: [wrong]}, {f"{key}_SHA256": hashlib.sha256(data).hexdigest()})
    assert result.returncode != 0
    assert not (raw / DATASETS[key][0]).exists()
    assert wrong.as_uri() in result.stderr
    assert_no_temps(raw)

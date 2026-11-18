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


# Stands in for curl. It logs each call, closed by an empty line, then hands
# the call to the real curl. A file:// source cannot show every case, so for
# the one address in CURL_PART_ADDRESS it plays a part instead: it fails with
# CURL_PART_ERROR as its reason, or it reports success after writing
# CURL_PART_BODY (nothing when that is unset) to the output file, as older
# curl does when a body of no declared length outgrows --max-filesize.
CURL_STUB = r"""#!/bin/sh
printf '%s\n' "$@" "" >> "$CURL_CALLS"
for address; do :; done
if [ -n "${CURL_PART_ADDRESS:-}" ] && [ "$address" = "$CURL_PART_ADDRESS" ]; then
  if [ -n "${CURL_PART_ERROR:-}" ]; then
    printf '%s\n' "$CURL_PART_ERROR" >&2
    exit 1
  fi
  while [ "$#" -gt 1 ]; do
    if [ "$1" = "-o" ] && [ -n "${CURL_PART_BODY:-}" ]; then
      cat "$CURL_PART_BODY" > "$2"
    fi
    shift
  done
  exit 0
fi
exec "$REAL_CURL" -q "$@" --proto '=file' --proto-redir '=file'
"""


@pytest.fixture
def bin_dir(tmp_path):
    """Leads PATH for the script, so a stub placed here stands in for a tool."""
    path = tmp_path / "bin"
    path.mkdir()
    return path


@pytest.fixture
def fetch(tmp_path, good_sources, bin_dir):
    real_curl = shutil.which("curl")
    if not real_curl:
        pytest.skip("curl is required to exercise the fetch script")
    raw = tmp_path / "raw data"
    raw.mkdir()
    calls = tmp_path / "curl-calls.txt"
    curl = bin_dir / "curl"
    # Even the red run must stay offline if the old script ignores the seams.
    curl.write_text(CURL_STUB)
    curl.chmod(0o755)
    _, paths = good_sources

    def run(sources=None, pins=None, **extra):
        env = {**os.environ, "SKY_RAW_DIR": str(raw), "CURL_CALLS": str(calls),
               "REAL_CURL": real_curl,
               "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        # Where the tests run must not decide whether the cache warning shows.
        env.pop("GITHUB_ACTIONS", None)
        env.update({f"SKY_SOURCES_{key}": path.as_uri() for key, path in paths.items()})
        for key, choices in (sources or {}).items():
            env[f"SKY_SOURCES_{key}"] = " ".join(path.as_uri() for path in choices)
        env.update(pins or {})
        env.update(extra)
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "fetch_sky_data.sh")],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
        )

    return raw, calls, run


def curl_calls(calls):
    """The words of each curl call, in the order the calls were made."""
    if not calls.exists():
        return []
    return [call.split("\n") for call in calls.read_text().split("\n\n") if call]


def value_of(call, option):
    """The word that follows an option in a curl call, or None without the option."""
    return call[call.index(option) + 1] if option in call else None


def stderr_line(result, marker):
    """The one line of stderr that holds the marker."""
    lines = [line for line in result.stderr.splitlines() if marker in line]
    assert len(lines) == 1, result.stderr
    return lines[0]


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


def test_only_last_source_is_retried(fetch, good_sources, tmp_path):
    """Catch retries spent on a dead source while a mirror waits to be asked."""
    raw, calls, run = fetch
    _, paths = good_sources
    dead = tmp_path / "dead"
    assert_ready(raw, run({"BOUND": [dead, paths["BOUND"]]}))
    asked = curl_calls(calls)
    assert [call[-1] for call in asked] == [
        paths["ATHYG"].as_uri(), paths["FIGURES"].as_uri(),
        dead.as_uri(), paths["BOUND"].as_uri(),
    ]
    assert not [word for word in asked[2] if word.startswith("--retry")]
    retries = {"--retry": "2", "--retry-max-time": "120"}
    for call in asked[:2] + asked[3:]:
        assert {option: value_of(call, option) for option in retries} == retries


def test_every_transfer_has_a_stall_rule(fetch, good_sources, tmp_path):
    """Catch a source that connects and stalls holding the job, or a slow line cut off early."""
    raw, calls, run = fetch
    _, paths = good_sources
    assert_ready(raw, run({"BOUND": [tmp_path / "dead", paths["BOUND"]]}))
    limits = {"--connect-timeout": "20", "--speed-limit": "1024",
              "--speed-time": "30", "--max-time": "600"}
    asked = curl_calls(calls)
    assert len(asked) == 4
    for call in asked:
        assert {option: value_of(call, option) for option in limits} == limits


def test_failed_source_gives_curls_reason(fetch, good_sources, tmp_path):
    """Catch curl's reason thrown away, so a missing file and a timeout read alike."""
    raw, _, run = fetch
    _, paths = good_sources
    absent = tmp_path / "absent"
    result = run({"FIGURES": [absent, paths["FIGURES"]]})
    assert_ready(raw, result)
    # 37 is curl's own code for a file address that it cannot read.
    assert "curl: (37)" in stderr_line(result, f"source {absent.as_uri()} failed:")


def test_curl_reason_stays_on_the_failed_line(fetch, good_sources):
    """Catch a reason of several lines, as after a refused certificate, spilling over."""
    raw, _, run = fetch
    _, paths = good_sources
    refused = "file:///refused"
    result = run(
        SKY_SOURCES_FIGURES=f"{refused} {paths['FIGURES'].as_uri()}",
        CURL_PART_ADDRESS=refused,
        CURL_PART_ERROR="curl: (60) SSL certificate problem\nMore details here",
    )
    assert_ready(raw, result)
    line = stderr_line(result, f"source {refused} failed:")
    assert "curl: (60) SSL certificate problem" in line
    assert "More details here" in line


@pytest.mark.parametrize("key", DATASETS)
def test_mismatch_gives_digest_and_size(fetch, good_sources, tmp_path, key):
    """Catch a mismatch that says neither which bytes were seen nor how many."""
    raw, _, run = fetch
    _, paths = good_sources
    name, _, _ = DATASETS[key]
    cached, served = b"bad cached bytes", b"another catalogue\n"
    (raw / name).write_bytes(cached)
    wrong = tmp_path / "wrong"
    wrong.write_bytes(gzip.compress(served) if key == "BOUND" else served)
    result = run({key: [wrong, paths[key]]})
    assert_ready(raw, result)
    for data, marker in ((cached, f"moved to {name}.bad"),
                         (served, f"source {wrong.as_uri()} failed:")):
        line = stderr_line(result, marker)
        assert hashlib.sha256(data).hexdigest() in line
        assert f"{len(data)} bytes" in line


def test_unreadable_file_is_not_a_mismatch(fetch, good_sources):
    """Catch a hashing failure read as a mismatch: a good file moved aside, the servers blamed."""
    if os.geteuid() == 0:
        pytest.skip("root reads a file of any mode, so hashing cannot be made to fail")
    raw, _, run = fetch
    contents, _ = good_sources
    name, _, _ = DATASETS["FIGURES"]
    present = raw / name
    present.write_bytes(contents["FIGURES"])
    present.chmod(0)
    result = run()
    present.chmod(0o644)
    assert result.returncode != 0
    assert name in stderr_line(result, "hashing failed")
    assert present.read_bytes() == contents["FIGURES"]
    assert not (raw / (name + ".bad")).exists()


def test_no_hasher_names_both_tools(fetch, bin_dir, tmp_path):
    """Catch a machine with no hasher fetching anyway and blaming every server for a mismatch."""
    _, calls, run = fetch
    tools = tmp_path / "tools"
    tools.mkdir()
    for tool in ("bash", "cat", "cut", "dirname", "gzip", "head", "mkdir", "mv", "rm", "tr", "wc"):
        (tools / tool).symlink_to(shutil.which(tool))
    result = run(PATH=f"{bin_dir}{os.pathsep}{tools}")
    assert result.returncode != 0
    line = stderr_line(result, "hashing failed")
    assert "sha256sum" in line
    assert "shasum" in line
    assert not calls.exists()


def test_hasher_is_given_no_path(fetch, bin_dir):
    """Catch a path reaching the hasher: GNU sha256sum marks its line if one has a backslash."""
    raw, _, run = fetch
    real = shutil.which("sha256sum")
    hasher = shlex.quote(real) if real else shlex.quote(shutil.which("shasum")) + " -a 256"
    stub = bin_dir / "sha256sum"
    stub.write_text(
        "#!/bin/sh\n"
        'if [ "$#" -gt 0 ]; then echo "the hasher was given a path" >&2; exit 64; fi\n'
        f"exec {hasher}\n"
    )
    stub.chmod(0o755)
    assert_ready(raw, run())


@pytest.mark.parametrize("key", DATASETS)
def test_transfer_past_cap_reported_good_tries_next(fetch, good_sources, tmp_path, key):
    """Catch a body past the cap that curl calls good, refused by its pin alone or not at all."""
    raw, _, run = fetch
    contents, paths = good_sources
    _, _, cap = DATASETS[key]
    body = tmp_path / "body"
    if key == "BOUND":
        # Empty members pad the archive past the cap; it still unpacks to the pinned bytes.
        empty = gzip.compress(b"")
        body.write_bytes(gzip.compress(contents[key]) + empty * (cap // len(empty) + 1))
    else:
        with body.open("wb") as stream:
            stream.truncate(cap + 1)
    oversized = "file:///oversized"
    result = run(
        CURL_PART_ADDRESS=oversized, CURL_PART_BODY=str(body),
        **{f"SKY_SOURCES_{key}": f"{oversized} {paths[key].as_uri()}"},
    )
    assert_ready(raw, result)
    assert "cap" in stderr_line(result, f"source {oversized} failed:")


def test_good_report_with_no_file_tries_next(fetch, good_sources):
    """Catch a transfer reported good that left no file stopping the script, the mirror unasked."""
    raw, _, run = fetch
    _, paths = good_sources
    hollow = "file:///hollow"
    result = run(
        SKY_SOURCES_FIGURES=f"{hollow} {paths['FIGURES'].as_uri()}",
        CURL_PART_ADDRESS=hollow,
    )
    assert_ready(raw, result)
    assert stderr_line(result, f"source {hollow} failed:")


@pytest.mark.parametrize("blank", [" ", " \t\n "], ids=["spaces", "mixed"])
def test_blank_source_list_stops_before_curl(fetch, blank):
    """Catch curl being run with an empty address when a list holds no entry."""
    _, calls, run = fetch
    name, _, _ = DATASETS["ATHYG"]
    result = run(SKY_SOURCES_ATHYG=blank)
    assert result.returncode != 0
    assert f"no sources for {name}" in result.stderr
    assert not calls.exists()


@pytest.mark.parametrize("gap", ["\n", "\t", " \n\t "], ids=["newline", "tab", "mixed"])
def test_any_whitespace_separates_sources(fetch, good_sources, tmp_path, gap):
    """Catch a list on several lines silently keeping only its first line."""
    raw, _, run = fetch
    _, paths = good_sources
    dead = tmp_path / "dead"
    result = run(SKY_SOURCES_BOUND=gap.join(["", dead.as_uri(), paths["BOUND"].as_uri(), ""]))
    assert_ready(raw, result)
    assert stderr_line(result, f"source {dead.as_uri()} failed:")


def test_dash_entry_is_never_an_option(fetch, good_sources, tmp_path):
    """Catch an entry that begins with a dash reaching curl as an option, here a config to obey."""
    raw, calls, run = fetch
    _, paths = good_sources
    config = tmp_path / "curl.config"
    config.write_text(f'url = "{paths["FIGURES"].as_uri()}"\n')
    entry = f"-K{config}"
    result = run(SKY_SOURCES_FIGURES=f"{entry} {paths['FIGURES'].as_uri()}")
    assert_ready(raw, result)
    assert stderr_line(result, f"source {entry} failed:")
    assert all(call[-2] == "--url" for call in curl_calls(calls))


@pytest.mark.parametrize("suffix", ["", ".part", ".unpacked.part"],
                         ids=["final", "part", "unpacked"])
def test_directory_in_the_store_stops_by_name(fetch, suffix):
    """Catch a directory in the store stopping the script with no word of why, or being moved."""
    raw, _, run = fetch
    blocked = raw / (DATASETS["BOUND"][0] + suffix)
    (blocked / "kept").mkdir(parents=True)
    result = run()
    assert result.returncode != 0
    line = stderr_line(result, "not a regular file")
    assert str(blocked) in line
    assert "remove it" in line
    assert (blocked / "kept").is_dir()


@pytest.mark.parametrize("on_actions", [True, False])
def test_bad_cache_entry_warns_on_actions(fetch, on_actions):
    """Catch a bad cache entry healed in silence on every run and never replaced."""
    raw, _, run = fetch
    name, _, _ = DATASETS["FIGURES"]
    (raw / name).write_bytes(b"bad cached bytes")
    result = run(GITHUB_ACTIONS="true") if on_actions else run()
    assert_ready(raw, result)
    assert stderr_line(result, f"moved to {name}.bad")
    warnings = [line for line in result.stdout.splitlines() + result.stderr.splitlines()
                if line.startswith("::warning::")]
    if not on_actions:
        assert not warnings
        return
    assert len(warnings) == 1
    assert name in warnings[0]
    assert "cache" in warnings[0]
    assert "delete" in warnings[0]

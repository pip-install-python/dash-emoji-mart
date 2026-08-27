"""One fleet Python — image, matrix, render.yaml and healthz must agree.

Adapted from the template's reference implementation (SYNC-1.6.22-1.6.29
item 5, template 1.6.29 @ 5589318). Session-class, not block cargo: it
presumes a Dockerfile and a render.yaml, which not every fork carries.

Found by the ops seat reading the template's tree (2026-08-25): the Dockerfile
said `python:3.11.8-slim` — a PATCH pin, so the image never received a 3.11.x
security release — while the CI matrix said 3.12 and render.yaml said 3.12.0.
Three declared Pythons, the docker boot/battery testing an interpreter the
matrix never ran, and nothing on the wire able to contradict any of them.

This repo contributed the other half of that lesson. Its image moved from
3.12-slim to 3.14-slim through a dependabot merge, alone: `grep ^FROM
Dockerfile` — the cheap half of the item's detect — passed from that moment,
while every other encoding still said 3.12 and /healthz carried no `python`
field at all, so nothing outside the container could contradict either
number. That is why the spec now reads a MISSING healthz `python` as
NOT-ADOPTED rather than not-applicable.

These pins hold every DECLARATION to one minor, sourced from the Dockerfile's
FROM tag. The serving host is held to the same minor by /healthz's `python`
field (lib/health.py) and `python_matches_declared`
(scripts/network_smoke.py), which is the only check of the set that measures
rather than reads.

What is deliberately NOT here: no comparison of the RUNNING interpreter to
the fleet minor. The suite legitimately runs on the window legs, where that
assertion would be false by design.

TWO PYTHONS LIVE IN THIS ci.yml, and this file pins exactly one of them.
The SITE lane — the jobs that install the site's requirements file and
boot/serve the docs app — is held to the image's minor. The PACKAGE lane
tests a wheel whose `requires-python` window is 3.9-3.13; pinning it to a
container base would fail the moment the image moved, and it is not this
file's business. Both lanes are named below, and a job carrying a Python pin
that belongs to neither list fails loudly rather than being read as one or
the other by default.

DIVERGENCE from the template's window rule, recorded in DIVERGENCES.md: the
template requires the two include legs to be adjacent minors (X.Y-1, X.Y-2).
This repo's low leg is 3.10 — the docs site's declared FLOOR, because
python-frontmatter 1.3 imports `typing.TypeGuard`. Adjacency around 3.14
would drop the floor from CI entirely and stop testing the one Python
boundary this repo actually asserts, so the leg is pinned to the floor by
name instead.
"""
from __future__ import annotations

import re

from conftest import REPO_ROOT

# The SITE lane: these jobs install requirements.txt, or build and boot the
# docs image. They run the Python production runs.
SITE_LANE_JOBS = {"smoke", "container", "audit"}

# The PACKAGE lane: these jobs build or exercise the dash-emoji-mart wheel,
# whose supported Python range is the package's own claim (pyproject's
# requires-python), not the site's. Deliberately NOT held to the image.
PACKAGE_LANE_JOBS = {"bundle", "package", "package-python-range"}

# The docs site's floor, and the reason it is not an adjacent minor:
# python-frontmatter 1.3 imports `typing.TypeGuard` (3.10+). ci.yml's header
# states the same constraint in prose; this is the machine copy.
SITE_PYTHON_FLOOR = "3.10"


def _fleet_minor() -> str:
    """The single source: the Dockerfile's FROM tag."""
    for line in (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"FROM\s+python:(\S+)", line)
        if m:
            return m.group(1)
    raise AssertionError("Dockerfile has no `FROM python:` line")


def _uncommented(path) -> list[str]:
    return [
        ln for ln in (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("#")
    ]


def _jobs(path) -> dict[str, list[str]]:
    """`{job id: its lines}` — the scoping the template's version does not need.

    The template's ci.yml has one Python in it, so a file-wide grep is exact
    there. Here a file-wide grep would read the wheel's 3.9-3.13 matrix as a
    site-lane declaration and fail on a correct tree.
    """
    lines = _uncommented(path)
    out: dict[str, list[str]] = {}
    current = None
    in_jobs = False
    for ln in lines:
        if re.match(r"^jobs:\s*$", ln):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if re.match(r"^\S", ln):  # a new top-level key ends the jobs mapping
            break
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", ln)
        if m:
            current = m.group(1)
            out[current] = []
        elif current is not None:
            out[current].append(ln)
    return out


def _pins(job_lines: list[str]) -> list[str]:
    """Literal `python-version: "X.Y"` values in one job block."""
    return [
        m.group(1) for ln in job_lines
        if (m := re.match(r'\s*python-version:\s*"([\d.]+)"', ln))
    ]


def test_dockerfile_tag_is_minor_only():
    """The patch pin IS the security bug: `3.11.8-slim` never receives a
    3.11.x fix release. The minor tag tracks them through Docker Hub."""
    tag = _fleet_minor()
    assert re.fullmatch(r"\d+\.\d+-slim", tag), (
        f"Dockerfile FROM tag is {tag!r} — must be a MINOR tag "
        "(python:X.Y-slim), never a patch pin"
    )


def test_render_yaml_agrees_with_the_image():
    """BRANCHES on the service runtime — this service is `runtime: docker`.

    `runtime: docker` — NOTHING reads PYTHON_VERSION; the image IS the
    interpreter. The key must be ABSENT: a value there reads like the
    platform's setting and can never be true, which is this item's own defect
    class (a declaration nothing holds to reality) arriving through the fix.

    `runtime: python` — the native runtime reads PYTHON_VERSION and requires a
    full X.Y.Z: REQUIRED, and its minor must be the fleet Python. This repo
    does not use that branch, but it is kept live rather than deleted so that
    if the service type ever changes, this test flips by itself instead of
    passing vacuously on a stale assumption.

    Anything else fails loudly: extend the branch deliberately.
    """
    minor = _fleet_minor().removesuffix("-slim")
    lines = _uncommented("render.yaml")

    runtime = None
    for ln in lines:
        m = re.match(r"\s*runtime:\s*(\S+)", ln)
        if m:
            runtime = m.group(1)
            break
    assert runtime, "render.yaml declares no `runtime:`"

    value = None
    for i, ln in enumerate(lines):
        if re.match(r"\s*- key: PYTHON_VERSION$", ln):
            m = re.search(r'value:\s*"([^"]+)"', lines[i + 1])
            value = m and m.group(1)
            break

    if runtime == "docker":
        assert value is None, (
            f"render.yaml declares PYTHON_VERSION {value!r} on a docker "
            "runtime — nothing reads it there; a string that looks like the "
            "platform's setting and can never be true is the drift class this "
            "file exists to kill. Delete the key."
        )
        return

    assert runtime == "python", (
        f"render.yaml runtime is {runtime!r} — this test knows `python` and "
        "`docker`; extend the branch deliberately"
    )
    assert value, "render.yaml declares no PYTHON_VERSION"
    assert re.fullmatch(r"\d+\.\d+\.\d+", value), (
        f"PYTHON_VERSION {value!r} — Render requires full X.Y.Z"
    )
    assert value.startswith(minor + "."), (
        f"render.yaml PYTHON_VERSION {value} vs image python:{minor}-slim — "
        "the native-runtime lane and the image lane disagree"
    )


def test_every_job_with_a_python_pin_is_assigned_to_a_lane():
    """No job gets to be neither. This is the guard that keeps the two lists
    below from silently going stale: a job added later with a Python pin
    lands here first, and whoever adds it has to say which Python it runs.
    Defaulting an unknown job into either lane is how the two Pythons get
    conflated again."""
    jobs = _jobs(".github/workflows/ci.yml")
    assert jobs, "no jobs parsed out of ci.yml — did the file shape change?"
    known = SITE_LANE_JOBS | PACKAGE_LANE_JOBS
    unclassified = sorted(
        name for name, lines in jobs.items()
        if name not in known
        and (_pins(lines) or any("python:" in ln for ln in lines))
    )
    assert not unclassified, (
        f"ci.yml jobs {unclassified} declare a Python and belong to neither "
        "SITE_LANE_JOBS nor PACKAGE_LANE_JOBS. Add them to one — the site "
        "lane runs the site's requirements, the package lane exercises the "
        "wheel."
    )
    missing = sorted(known - set(jobs))
    assert not missing, (
        f"these jobs are classified but no longer exist in ci.yml: {missing}"
    )


def test_the_site_lane_agrees_with_the_image():
    """Every SITE-lane declaration is the image's minor, and there is at least
    one — an empty result would pass vacuously, which is how a grep that
    stopped matching reads exactly like a tree that is correct."""
    minor = _fleet_minor().removesuffix("-slim")
    jobs = _jobs(".github/workflows/ci.yml")

    mains = [
        m.group(1) for ln in jobs["smoke"]
        if (m := re.match(r'\s*python:\s*\["([\d.]+)"\]', ln))
    ]
    assert mains == [minor], (
        f"ci.yml `smoke` matrix main is {mains}, image is python:{minor}-slim"
    )

    for job in sorted(SITE_LANE_JOBS - {"smoke"}):
        pins = _pins(jobs[job])
        assert pins and set(pins) == {minor}, (
            f"ci.yml `{job}` pins {pins}, image is python:{minor}-slim"
        )

    cd_verify = _jobs(".github/workflows/cd.yml")["verify"]
    cd_pins = _pins(cd_verify)
    assert cd_pins and set(cd_pins) == {minor}, (
        f"cd.yml `verify` pins {cd_pins}, image is python:{minor}-slim"
    )


def test_the_package_lane_is_left_alone():
    """The other half of the split, asserted rather than merely omitted.

    A future session reading only the test above could reasonably "finish the
    job" by moving every remaining 3.12 to the fleet minor. This says out loud
    that the package lane is not behind — it is answering a different
    question, and its range comes from the wheel's own requires-python.
    """
    minor = _fleet_minor().removesuffix("-slim")
    jobs = _jobs(".github/workflows/ci.yml")

    matrix = [
        ln for ln in jobs["package-python-range"]
        if re.match(r'\s*python:\s*\[', ln)
    ]
    assert matrix, "the package matrix vanished — where does the wheel get tested?"
    assert minor not in matrix[0], (
        f"the package matrix {matrix[0].strip()} now names the fleet minor "
        f"{minor}. That may well be right — the wheel supporting the site's "
        "Python is a good thing — but it must be a deliberate change to "
        "pyproject's requires-python and this pin together, not drift."
    )


def test_the_matrix_legs_are_the_floor_and_the_adjacent_minor():
    """The compat window: the declared site floor, one adjacent minor, and the
    fleet Python itself.

    DIVERGENCE from the template's rule, which wants both legs adjacent
    (X.Y-1, X.Y-2). Adjacency around 3.14 would put the low leg at 3.12 and
    retire the floor from CI — and the floor is not decoration here: the site
    genuinely requires 3.10+ (python-frontmatter 1.3 needs `typing.TypeGuard`),
    and a floor nothing tests is a floor nobody can trust. Recorded in
    DIVERGENCES.md.

    The legs in this repo are written `- dash: "..."` / `python: "..."` pairs
    — the include varies the PYTHON axis while holding dash at the current
    release, which is the opposite orientation from the template's, so the
    template's `- python:` line regex finds nothing here and would fail on a
    perfectly correct tree.
    """
    major, y = (int(p) for p in _fleet_minor().removesuffix("-slim").split("."))
    fleet = f"{major}.{y}"
    allowed = {fleet, f"{major}.{y - 1}", f"{major}.{y + 1}", SITE_PYTHON_FLOOR}

    smoke = _jobs(".github/workflows/ci.yml")["smoke"]
    include = smoke[smoke.index(next(ln for ln in smoke
                                     if re.match(r"\s*include:\s*$", ln))):]
    legs = [
        m.group(1) for ln in include
        if (m := re.match(r'\s*-?\s*python:\s*"([\d.]+)"', ln))
    ]
    assert legs, "the matrix has no include legs — the window collapsed to one"
    assert SITE_PYTHON_FLOOR in legs, (
        f"no leg at the declared site floor {SITE_PYTHON_FLOOR} — the one "
        "Python boundary this repo asserts is now untested"
    )
    outside = sorted(set(legs) - allowed)
    assert not outside, (
        f"matrix legs {outside} are neither the site floor "
        f"({SITE_PYTHON_FLOOR}) nor adjacent to the fleet Python ({fleet})"
    )


def test_healthz_declares_the_interpreter():
    """The measured encoding — the only one that can contradict the rest.

    Deliberately does NOT compare to the fleet minor: this suite runs on the
    window legs too, where the running interpreter is legitimately not the
    image's. Agreement between the SERVED value and the DECLARED tag is the
    battery's job, against a host — `python_matches_declared` in
    scripts/network_smoke.py.

    What is asserted here is that the field exists and is a real version, so
    that the battery has something to read. Absence is the pre-adoption state
    and counts as a failure (SYNC-1.6.22-1.6.29 item 5, amended 1.6.28).
    """
    import platform

    from lib.health import health_payload

    payload = health_payload("flask")
    assert "python" in payload, (
        "/healthz carries no `python` field — the running host cannot say "
        "which interpreter answered, so the image tag stays an unverifiable "
        "claim and network_smoke's python_matches_declared has nothing to read"
    )
    assert payload["python"] == platform.python_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+\S*", payload["python"]), (
        f"`python` is {payload['python']!r}, expected a version string"
    )

"""Sanity-check the artifacts produced by ``uv build``.

Run locally with::

    uv build && python scripts/check_dist.py

Both the CI and the release workflow call this so that a broken or polluted
package never ends up attached to a GitHub Release.
"""

from __future__ import annotations

import glob
import sys
import tarfile
import zipfile
from pathlib import Path

WHEEL_REQUIRED = (
    "b2t/__init__.py",
    "b2t/cli.py",
    "b2t/templates/index.html",
    "b2t/templates/batch.html",
    "b2t/templates/task.html",
    "b2t/templates/video.html",
)
SDIST_REQUIRED_SUFFIXES = tuple(f"src/{name}" for name in WHEEL_REQUIRED)
# Local caches or virtualenvs must never leak into a release artifact.
JUNK_MARKERS = ("/.uv-cache/", "/.venv", "/__pycache__/", "/.b2t/", "/.pytest_cache/")


def _missing(names: list[str], required: tuple[str, ...]) -> list[str]:
    return [item for item in required if not any(name.endswith(item) for name in names)]


def _junk(names: list[str]) -> list[str]:
    return [name for name in names if any(marker in name for marker in JUNK_MARKERS)]


def main() -> int:
    wheels = sorted(glob.glob("dist/*.whl"))
    sdists = sorted(glob.glob("dist/*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        print(f"expected exactly one wheel and one sdist, got wheel={wheels} sdist={sdists}")
        return 1

    wheel, sdist = Path(wheels[0]), Path(sdists[0])
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()

    problems: list[str] = []
    missing = _missing(wheel_names, WHEEL_REQUIRED)
    if missing:
        problems.append(f"{wheel.name} is missing: {missing}")
    missing = _missing(sdist_names, SDIST_REQUIRED_SUFFIXES)
    if missing:
        problems.append(f"{sdist.name} is missing: {missing}")
    junk = _junk(wheel_names) + _junk(sdist_names)
    if junk:
        problems.append(f"build artifacts contain local junk: {junk[:5]}")

    if problems:
        print("\n".join(problems))
        return 1

    print(f"OK: {wheel.name} ({len(wheel_names)} entries) / {sdist.name} ({len(sdist_names)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

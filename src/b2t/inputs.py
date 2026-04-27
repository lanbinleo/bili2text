from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from b2t.models import SourceRef


BV_PATTERN = re.compile(r"(BV[0-9A-Za-z]{10})")
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".flv", ".avi", ".webm"}


def parse_source(raw_input: str) -> SourceRef:
    value = raw_input.strip()
    if not value:
        raise ValueError("source cannot be empty")

    candidate_path = Path(value).expanduser()
    if candidate_path.exists():
        suffix = candidate_path.suffix.lower()
        if suffix in AUDIO_SUFFIXES:
            return SourceRef(
                raw_input=value,
                kind="audio",
                display_name=candidate_path.stem,
                path=candidate_path.resolve(),
            )
        if suffix in VIDEO_SUFFIXES:
            return SourceRef(
                raw_input=value,
                kind="video",
                display_name=candidate_path.stem,
                path=candidate_path.resolve(),
            )
        raise ValueError(f"unsupported local file type: {candidate_path.suffix}")

    match = BV_PATTERN.search(value)
    if match:
        bv = match.group(1)
        url = value if _looks_like_url(value) else f"https://www.bilibili.com/video/{bv}"
        page = _extract_page_from_url(url)
        return SourceRef(
            raw_input=value,
            kind="bilibili",
            display_name=bv,
            url=url,
            bv=bv,
            page=page,
        )

    raise ValueError("source must be a BV id, a Bilibili URL, or an existing local audio/video file")


def parse_source_list(raw_input: str) -> list[str]:
    sources = [
        line.strip()
        for line in raw_input.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not sources:
        raise ValueError("source list cannot be empty")
    return sources


def safe_stem(value: str) -> str:
    stem = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE).strip("-._")
    return stem or "b2t-output"


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _extract_page_from_url(url: str) -> int | None:
    """Extract a valid 1-based 'p' (page) parameter from URL query string."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    p_values = query_params.get("p", [])
    if p_values:
        try:
            page = int(p_values[0])
        except ValueError:
            return None
        return page if page >= 1 else None
    return None

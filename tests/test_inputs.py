from pathlib import Path

import pytest

from b2t.inputs import parse_source, parse_source_list, safe_stem


def test_parse_bv_identifier() -> None:
    source = parse_source("BV1xx411c7XD")
    assert source.kind == "bilibili"
    assert source.bv == "BV1xx411c7XD"
    assert source.url == "https://www.bilibili.com/video/BV1xx411c7XD"


def test_parse_bilibili_url_keeps_page_information() -> None:
    source = parse_source("https://www.bilibili.com/video/BV1xx411c7XD?p=2")
    assert source.kind == "bilibili"
    assert source.url == "https://www.bilibili.com/video/BV1xx411c7XD?p=2"


def test_parse_bilibili_url_extracts_page_number() -> None:
    source = parse_source("https://www.bilibili.com/video/BV1xx411c7XD?p=2")
    assert source.kind == "bilibili"
    assert source.page == 2


def test_parse_bilibili_url_without_page_sets_page_to_none() -> None:
    source = parse_source("https://www.bilibili.com/video/BV1xx411c7XD")
    assert source.kind == "bilibili"
    assert source.page is None


def test_parse_bv_identifier_without_page_sets_page_to_none() -> None:
    source = parse_source("BV1xx411c7XD")
    assert source.kind == "bilibili"
    assert source.page is None


@pytest.mark.parametrize("page", ["0", "-1", "not-a-number"])
def test_parse_bilibili_url_ignores_invalid_page_number(page: str) -> None:
    source = parse_source(f"https://www.bilibili.com/video/BV1xx411c7XD?p={page}")
    assert source.kind == "bilibili"
    assert source.page is None


def test_parse_local_audio_file(tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"wav")

    source = parse_source(str(audio_path))
    assert source.kind == "audio"
    assert source.path == audio_path.resolve()


def test_parse_source_list_ignores_blank_lines_and_comments() -> None:
    sources = parse_source_list(
        """
        BV1xx411c7XD

        # optional note
        https://www.bilibili.com/video/BV1yy411c7XD
        """
    )

    assert sources == [
        "BV1xx411c7XD",
        "https://www.bilibili.com/video/BV1yy411c7XD",
    ]


def test_safe_stem_removes_unsafe_characters() -> None:
    assert safe_stem("hello / world?") == "hello-world"

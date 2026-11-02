from pathlib import Path

import pytest

from b2t.transcribers.mimo import MimoTranscriber


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    """Counts calls so tests can prove the cache actually skipped the API."""

    def __init__(self, reply: str = "转写结果", fail_times: int = 0) -> None:
        self.reply = reply
        self.fail_times = fail_times
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("429 Too many requests")
        return _FakeResponse(self.reply)


class _FakeClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = type("_Chat", (), {"completions": completions})()


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry backoff is real seconds in production; tests should not pay for it."""
    monkeypatch.setattr("b2t.transcribers.mimo.time.sleep", lambda _seconds: None)


def _chunk(tmp_path: Path, name: str = "0000.wav", data: bytes = b"RIFFfake-audio") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_chunk_result_is_cached_and_reused(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    transcriber = MimoTranscriber(api_key="k", cache_dir=cache_root)
    completions = _FakeCompletions(reply="第一片")
    client = _FakeClient(completions)
    chunk = _chunk(tmp_path)

    first = transcriber._transcribe_chunk(client, chunk, "")
    second = transcriber._transcribe_chunk(client, chunk, "")

    assert first == second == "第一片"
    assert completions.calls == 1, "second call should have been served from cache"


def test_cache_is_keyed_by_model_and_language(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    chunk = _chunk(tmp_path)

    zh = MimoTranscriber(api_key="k", cache_dir=cache_root, language="zh")
    en = MimoTranscriber(api_key="k", cache_dir=cache_root, language="en")
    zh._transcribe_chunk(_FakeClient(_FakeCompletions(reply="中文")), chunk, "")

    completions = _FakeCompletions(reply="english")
    assert en._transcribe_chunk(_FakeClient(completions), chunk, "") == "english"
    assert completions.calls == 1, "a different language must not reuse the zh entry"


def test_no_cache_dir_means_no_caching(tmp_path: Path) -> None:
    transcriber = MimoTranscriber(api_key="k", cache_dir=None)
    completions = _FakeCompletions()
    client = _FakeClient(completions)
    chunk = _chunk(tmp_path)

    transcriber._transcribe_chunk(client, chunk, "")
    transcriber._transcribe_chunk(client, chunk, "")

    assert completions.calls == 2


def test_transient_failure_is_retried_then_cached(tmp_path: Path) -> None:
    transcriber = MimoTranscriber(api_key="k", cache_dir=tmp_path / "cache", max_retries=3)
    completions = _FakeCompletions(reply="补上了", fail_times=2)
    client = _FakeClient(completions)
    chunk = _chunk(tmp_path)

    assert transcriber._transcribe_chunk(client, chunk, "") == "补上了"
    assert completions.calls == 3

    # the successful result is cached, so a resume does not pay for the retries again
    assert transcriber._transcribe_chunk(client, chunk, "") == "补上了"
    assert completions.calls == 3


def test_exhausted_retries_raise(tmp_path: Path) -> None:
    transcriber = MimoTranscriber(api_key="k", cache_dir=tmp_path / "cache", max_retries=2)
    completions = _FakeCompletions(fail_times=99)
    client = _FakeClient(completions)
    chunk = _chunk(tmp_path)

    with pytest.raises(RuntimeError, match="MiMo transcription failed"):
        transcriber._transcribe_chunk(client, chunk, "")

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from b2t.transcribers.sensevoice_local import SenseVoiceSmallTranscriber

REQUIRED_SUPPORT_FILES = (
    "config.yaml",
    "am.mvn",
    "chn_jpn_yue_eng_ko_spectok.bpe.model",
)


def _write_support_files(model_dir: Path) -> None:
    for filename in REQUIRED_SUPPORT_FILES:
        (model_dir / filename).write_text("test", encoding="utf-8")


@pytest.mark.parametrize(
    ("model_filename", "expected_quantize"),
    (("model_quant.onnx", True), ("model.onnx", False)),
)
def test_sensevoice_selects_quantization_from_available_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_filename: str,
    expected_quantize: bool,
) -> None:
    _write_support_files(tmp_path)
    (tmp_path / model_filename).write_bytes(b"onnx")
    calls: list[tuple[str, bool]] = []

    def fake_model(model_dir: str, *, quantize: bool):
        calls.append((model_dir, quantize))
        return object()

    monkeypatch.setitem(
        sys.modules, "funasr_onnx", SimpleNamespace(SenseVoiceSmall=fake_model)
    )

    transcriber = SenseVoiceSmallTranscriber(model_dir=tmp_path)
    transcriber._ensure_model()

    assert calls == [(str(tmp_path), expected_quantize)]


def test_sensevoice_reports_missing_tokenizer_before_model_load(tmp_path: Path) -> None:
    (tmp_path / "model_quant.onnx").write_bytes(b"onnx")
    (tmp_path / "config.yaml").write_text("test", encoding="utf-8")
    (tmp_path / "am.mvn").write_text("test", encoding="utf-8")

    transcriber = SenseVoiceSmallTranscriber(model_dir=tmp_path)

    with pytest.raises(RuntimeError, match="chn_jpn_yue_eng_ko_spectok.bpe.model"):
        transcriber._ensure_model()

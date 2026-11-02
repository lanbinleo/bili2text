import sys
import types
from pathlib import Path

from b2t.progress import ProgressReporter
from b2t.transcribers.whisper_local import (
    LocalWhisperTranscriber,
    WhisperProgressTqdm,
    build_whisper_import_error_message,
)


def _install_fake_whisper(monkeypatch, *, cuda: bool = False, mps: bool = False, mps_load_fails: bool = False) -> dict:
    calls: dict = {"load_devices": []}

    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: cuda)
    fake_torch.backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: mps),
    )

    class FakeModel:
        def transcribe(self, audio_path, **options):
            calls["transcribe_options"] = options
            return {"text": "hello", "segments": [], "language": "en"}

    def load_model(name, device=None):
        calls["load_devices"].append(device)
        if device == "mps" and mps_load_fails:
            raise NotImplementedError("sparse tensors not supported on MPS")
        return FakeModel()

    fake_whisper = types.ModuleType("whisper")
    fake_whisper.load_model = load_model

    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)
    return calls


def test_device_auto_selects_mps_when_cuda_unavailable(monkeypatch) -> None:
    calls = _install_fake_whisper(monkeypatch, cuda=False, mps=True)
    transcriber = LocalWhisperTranscriber(model="small")

    transcriber._ensure_model()

    assert transcriber.device == "mps"
    assert calls["load_devices"] == ["mps"]


def test_mps_load_failure_falls_back_to_cpu(monkeypatch) -> None:
    calls = _install_fake_whisper(monkeypatch, cuda=False, mps=True, mps_load_fails=True)
    transcriber = LocalWhisperTranscriber(model="small")

    transcriber._ensure_model()

    assert transcriber.device == "cpu"
    assert calls["load_devices"] == ["mps", "cpu"]


def test_transcribe_disables_fp16_on_mps(monkeypatch) -> None:
    calls = _install_fake_whisper(monkeypatch, cuda=False, mps=True)
    transcriber = LocalWhisperTranscriber(model="small")

    result = transcriber.transcribe(Path("dummy.wav"))

    assert calls["transcribe_options"]["fp16"] is False
    assert result["device"] == "mps"


def test_build_whisper_import_error_message_reports_missing_install() -> None:
    message = build_whisper_import_error_message(
        whisper_available=False,
    )

    assert "Whisper support is not installed." in message
    assert "uv sync --extra whisper --extra web" in message


def test_build_whisper_import_error_message_reports_broken_environment() -> None:
    message = build_whisper_import_error_message(
        whisper_available=True,
    )

    assert "Whisper is installed, but the Python environment looks broken." in message
    assert ".venv" in message


def test_whisper_progress_tqdm_reports_fractional_progress() -> None:
    events = []
    reporter = ProgressReporter("task-1", callback=events.append)
    bar = WhisperProgressTqdm(reporter, total=100, disable=False)

    with bar:
        bar.update(25)
        bar.update(25)

    assert events[-1].stage == "transcribing"
    assert round(events[-1].percent, 3) == 0.725

from __future__ import annotations

import importlib
import importlib.util
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from b2t.i18n import dependency_sync_guidance
from b2t.progress import ProgressReporter
from b2t.transcribers.base import Transcriber


class LocalWhisperTranscriber(Transcriber):
    name = "whisper"

    def __init__(self, model: str = "small", device: str | None = None) -> None:
        self.model_name = model
        self.device = device
        self._model: Any | None = None

    def transcribe(
        self,
        audio_path: Path,
        *,
        prompt: str | None = None,
        progress: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        model = self._ensure_model()
        if progress is not None:
            progress.running("transcribing", message="transcribing", stage_progress=0.0)
        transcribe_options: dict[str, Any] = {
            "initial_prompt": prompt or None,
            # `verbose=False` keeps Whisper text output quiet while still driving the internal tqdm loop.
            "verbose": False,
        }
        if self.device in ("cpu", "mps"):
            # fp16 is NaN-prone on some MPS/torch builds and Whisper re-casts
            # weights per forward pass anyway; fp32 is the safe choice off CUDA.
            transcribe_options["fp16"] = False
        with whisper_progress(progress):
            result = model.transcribe(str(audio_path), **transcribe_options)
        text = (result.get("text") or "").strip()
        return {
            "text": text,
            "segments": result.get("segments", []),
            "language": result.get("language"),
            "device": self.device,
            "model": self.model_name,
        }

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            import torch
            import whisper
        except ImportError as exc:
            raise RuntimeError(build_whisper_import_error_message()) from exc

        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                # Apple Silicon GPU (Metal Performance Shaders).
                self.device = "mps"
            else:
                self.device = "cpu"

        if self.device == "mps":
            # Whisper registers alignment_heads as a sparse buffer, which some
            # torch builds cannot move to MPS (NotImplementedError at load).
            try:
                self._model = whisper.load_model(self.model_name, device="mps")
            except Exception:
                self.device = "cpu"
                self._model = whisper.load_model(self.model_name, device="cpu")
        else:
            self._model = whisper.load_model(self.model_name, device=self.device)
        return self._model


def build_whisper_import_error_message(*, whisper_available: bool | None = None) -> str:
    if whisper_available is None:
        whisper_available = importlib.util.find_spec("whisper") is not None

    if whisper_available:
        return (
            "Whisper is installed, but the Python environment looks broken. "
            "Recreate `.venv` and sync the required extras again. "
            f"{dependency_sync_guidance('en-US')} "
            "Whisper currently needs Python 3.12 or below."
        )

    return (
        "Whisper support is not installed. "
        f"{dependency_sync_guidance('en-US')} "
        "Whisper currently needs Python 3.12 or below."
    )


@contextmanager
def whisper_progress(progress: ProgressReporter | None):
    if progress is None:
        yield
        return

    module = importlib.import_module("whisper.transcribe")
    original = module.tqdm.tqdm
    module.tqdm.tqdm = lambda *args, **kwargs: WhisperProgressTqdm(progress, *args, **kwargs)
    try:
        yield
    finally:
        module.tqdm.tqdm = original


class WhisperProgressTqdm:
    def __init__(self, progress: ProgressReporter, *args, total: int | None = None, disable: bool = False, **kwargs) -> None:
        self.progress = progress
        self.total = total or 0
        self.disable = disable
        self.n = 0

    def __enter__(self) -> "WhisperProgressTqdm":
        if not self.disable:
            self.progress.running("transcribing", message="transcribing", stage_progress=0.0)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def update(self, amount: int = 1) -> None:
        self.n += amount
        if self.disable:
            return
        if self.total <= 0:
            self.progress.running("transcribing", message="transcribing", indeterminate=True)
            return
        self.progress.running(
            "transcribing",
            message="transcribing",
            stage_progress=min(1.0, self.n / self.total),
        )

    def refresh(self) -> None:
        return

    def close(self) -> None:
        return

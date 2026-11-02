from __future__ import annotations

from pathlib import Path
from typing import Any

from b2t.i18n import dependency_sync_guidance
from b2t.transcribers.base import Transcriber

SENSEVOICE_TOKENIZER = "chn_jpn_yue_eng_ko_spectok.bpe.model"
SENSEVOICE_SUPPORT_FILES = ("config.yaml", "am.mvn", SENSEVOICE_TOKENIZER)


class SenseVoiceSmallTranscriber(Transcriber):
    name = "sensevoice"

    def __init__(
        self, *, model_dir: Path, language: str = "auto", use_itn: bool = True
    ) -> None:
        self.model_dir = model_dir
        self.language = language
        self.use_itn = use_itn
        self._model: Any | None = None

    def transcribe(
        self,
        audio_path: Path,
        *,
        prompt: str | None = None,
        progress=None,
    ) -> dict[str, Any]:
        model = self._ensure_model()
        if progress is not None:
            progress.running("transcribing", message="transcribing", indeterminate=True)

        try:
            from funasr_onnx.utils.postprocess_utils import (
                rich_transcription_postprocess,
            )
        except ImportError as exc:
            raise RuntimeError(
                "SenseVoice support is not installed. "
                f"{dependency_sync_guidance('en-US')}"
            ) from exc

        results = model(
            [str(audio_path)],
            language=self.language,
            use_itn=self.use_itn,
        )
        text = "\n".join(
            rich_transcription_postprocess(_extract_text(item))
            for item in results
            if item is not None
        ).strip()

        return {
            "text": text,
            "segments": results,
            "language": self.language,
            "model": str(self.model_dir),
        }

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        if not self.model_dir.exists():
            raise RuntimeError(
                f"SenseVoice model directory does not exist: {self.model_dir}"
            )

        quantize = _validate_model_dir(self.model_dir)

        try:
            from funasr_onnx import SenseVoiceSmall
        except ImportError as exc:
            raise RuntimeError(
                "SenseVoice support is not installed. "
                f"{dependency_sync_guidance('en-US')}"
            ) from exc

        self._model = SenseVoiceSmall(str(self.model_dir), quantize=quantize)
        return self._model


def _extract_text(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


def _validate_model_dir(model_dir: Path) -> bool:
    missing = [
        filename
        for filename in SENSEVOICE_SUPPORT_FILES
        if not (model_dir / filename).is_file()
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(
            f"SenseVoice model directory is incomplete ({model_dir}). Missing: {missing_text}. "
            "The ONNX repository does not include the SentencePiece tokenizer; copy "
            f"{SENSEVOICE_TOKENIZER} from iic/SenseVoiceSmall into this directory."
        )

    if (model_dir / "model_quant.onnx").is_file():
        return True
    if (model_dir / "model.onnx").is_file():
        return False

    raise RuntimeError(
        f"SenseVoice model directory is incomplete ({model_dir}). "
        "Missing model_quant.onnx or model.onnx."
    )

from __future__ import annotations

import re
from pathlib import Path

from b2t.config import Settings
from b2t.downloaders import YtDlpDownloader
from b2t.pipeline import B2TPipeline
from b2t.transcribers import LocalWhisperTranscriber
from b2t.user_config import AppConfig

# `AppConfig.default_model` is whisper-scoped, but callers historically passed
# `model or config.default_model` down to every provider. Those whisper model
# names ("small" by default) must never end up as a Volcengine model name or a
# SenseVoice model directory (#112).
_WHISPER_MODEL_RE = re.compile(
    r"^(tiny|base|small|medium|large|turbo)([.-](en|v\d+))*$",
    re.IGNORECASE,
)


def _looks_like_whisper_model(value: str) -> bool:
    return bool(_WHISPER_MODEL_RE.match(value.strip()))


def _resolve_whisper_model(config: AppConfig, model: str | None) -> str:
    candidate = (model or config.default_model or "").strip()
    return candidate or "small"


def _resolve_sensevoice_model_dir(config: AppConfig, model: str | None) -> str:
    candidate = (model or "").strip()
    if candidate and not _looks_like_whisper_model(candidate):
        return candidate
    return config.sensevoice.model_dir.strip()


def _resolve_volcengine_model_name(config: AppConfig, model: str | None) -> str:
    candidate = (model or "").strip()
    if candidate and not _looks_like_whisper_model(candidate):
        return candidate
    return config.volcengine.model_name or "bigmodel"


def _resolve_mimo_model_name(config: AppConfig, model: str | None) -> str:
    candidate = (model or "").strip()
    if candidate.lower().startswith("mimo"):
        return candidate
    return config.mimo.model_name or "mimo-v2.5-asr"


def build_pipeline(
    *,
    settings: Settings,
    config: AppConfig,
    provider: str | None = None,
    model: str | None = None,
    cookies_from_browser: str | None = None,
) -> B2TPipeline:
    selected_provider = (provider or config.default_provider).strip().lower()

    if selected_provider == "whisper":
        transcriber = LocalWhisperTranscriber(model=_resolve_whisper_model(config, model))
    elif selected_provider == "sensevoice":
        from b2t.transcribers.sensevoice_local import SenseVoiceSmallTranscriber

        model_dir_text = _resolve_sensevoice_model_dir(config, model)
        if not model_dir_text:
            raise RuntimeError("SenseVoice provider requires a local model directory. Run `bili2text bootstrap` first.")
        transcriber = SenseVoiceSmallTranscriber(
            model_dir=Path(model_dir_text).expanduser(),
            language=config.sensevoice.language,
            use_itn=config.sensevoice.use_itn,
        )
    elif selected_provider == "volcengine":
        from b2t.transcribers.volcengine import VolcengineFlashTranscriber

        transcriber = VolcengineFlashTranscriber(
            api_key=config.volcengine.api_key,
            app_key=config.volcengine.app_key,
            access_key=config.volcengine.access_key,
            resource_id=config.volcengine.resource_id,
            model_name=_resolve_volcengine_model_name(config, model),
            use_itn=config.volcengine.use_itn,
        )
    elif selected_provider == "mimo":
        from b2t.transcribers.mimo import MimoTranscriber

        transcriber = MimoTranscriber(
            api_key=config.mimo.api_key,
            base_url=config.mimo.base_url,
            model_name=_resolve_mimo_model_name(config, model),
            language=config.mimo.language,
            workers=config.mimo.workers,
            cache_dir=settings.cache_dir,
        )
    else:
        raise RuntimeError(f"Unsupported provider: {selected_provider}")

    return B2TPipeline(
        settings=settings,
        downloader=YtDlpDownloader(cookies_from_browser=cookies_from_browser),
        transcriber=transcriber,
    )

from __future__ import annotations

from pathlib import Path

from b2t.config import Settings
from b2t.downloaders import YtDlpDownloader
from b2t.pipeline import B2TPipeline
from b2t.transcribers import LocalWhisperTranscriber
from b2t.user_config import AppConfig


def build_pipeline(
    *,
    settings: Settings,
    config: AppConfig,
    provider: str | None = None,
    model: str | None = None,
    cookies_from_browser: str | None = None,
) -> B2TPipeline:
    selected_provider = (provider or config.default_provider).strip().lower()
    selected_model = (model or config.default_model).strip()

    if selected_provider == "whisper":
        transcriber = LocalWhisperTranscriber(model=selected_model or "small")
    elif selected_provider == "sensevoice":
        from b2t.transcribers.sensevoice_local import SenseVoiceSmallTranscriber

        model_dir_text = selected_model or config.sensevoice.model_dir
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
            model_name=selected_model or config.volcengine.model_name,
            use_itn=config.volcengine.use_itn,
        )
    elif selected_provider == "mimo":
        from b2t.transcribers.mimo import MimoTranscriber

        # selected_model may carry whisper's default ("small"); only honor it when it
        # actually looks like a MiMo model id.
        chosen_model = selected_model if selected_model.startswith("mimo") else config.mimo.model_name
        transcriber = MimoTranscriber(
            api_key=config.mimo.api_key,
            base_url=config.mimo.base_url,
            model_name=chosen_model or "mimo-v2.5-asr",
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

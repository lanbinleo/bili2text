from pathlib import Path

from b2t.config import Settings
from b2t.factory import build_pipeline
from b2t.user_config import AppConfig


def _settings(tmp_path: Path) -> Settings:
    return Settings.from_workspace(tmp_path / ".b2t")


def test_whisper_uses_configured_default_model(tmp_path: Path) -> None:
    config = AppConfig(default_provider="whisper", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config)
    assert pipeline.transcriber.model_name == "small"


def test_whisper_honors_explicit_model(tmp_path: Path) -> None:
    config = AppConfig(default_provider="whisper", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config, model="large")
    assert pipeline.transcriber.model_name == "large"


def test_volcengine_ignores_whisper_default_model(tmp_path: Path) -> None:
    # Regression test for #112: the whisper-scoped default must not become a
    # Volcengine model name.
    config = AppConfig(default_provider="volcengine", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config)
    assert pipeline.transcriber.model_name == "bigmodel"


def test_volcengine_honors_explicit_model(tmp_path: Path) -> None:
    config = AppConfig(default_provider="volcengine", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config, model="custom-flash-model")
    assert pipeline.transcriber.model_name == "custom-flash-model"


def test_sensevoice_ignores_whisper_default_model(tmp_path: Path) -> None:
    # Regression test for #112: SenseVoice must use its configured model dir,
    # not treat whisper's "small" as a path.
    config = AppConfig(default_provider="sensevoice", default_model="small")
    config.sensevoice.model_dir = "/models/SenseVoiceSmall-onnx"
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config)
    assert pipeline.transcriber.model_dir == Path("/models/SenseVoiceSmall-onnx")


def test_sensevoice_honors_explicit_model_dir(tmp_path: Path) -> None:
    config = AppConfig(default_provider="sensevoice", default_model="small")
    config.sensevoice.model_dir = "/models/SenseVoiceSmall-onnx"
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config, model="/models/other-onnx")
    assert pipeline.transcriber.model_dir == Path("/models/other-onnx")


def test_mimo_ignores_whisper_default_model(tmp_path: Path) -> None:
    config = AppConfig(default_provider="mimo", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config)
    assert pipeline.transcriber.model_name == "mimo-v2.5-asr"


def test_mimo_honors_explicit_model(tmp_path: Path) -> None:
    config = AppConfig(default_provider="mimo", default_model="small")
    pipeline = build_pipeline(settings=_settings(tmp_path), config=config, model="mimo-v2.5-asr-pro")
    assert pipeline.transcriber.model_name == "mimo-v2.5-asr-pro"

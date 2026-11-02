from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from b2t.config import Settings
from b2t.i18n import DEFAULT_LANGUAGE, normalize_language

ALL_PROVIDERS = ("whisper", "sensevoice", "volcengine", "mimo")
ALL_FEATURES = ("web", "server", "window")


@dataclass(slots=True)
class SenseVoiceConfig:
    model_dir: str = ""
    language: str = "auto"
    use_itn: bool = True


@dataclass(slots=True)
class VolcengineConfig:
    api_key: str = ""
    app_key: str = ""
    access_key: str = ""
    resource_id: str = "volc.bigasr.auc_turbo"
    model_name: str = "bigmodel"
    use_itn: bool = True


@dataclass(slots=True)
class MimoConfig:
    api_key: str = ""
    base_url: str = "https://api.xiaomimimo.com/v1"
    model_name: str = "mimo-v2.5-asr"
    language: str = "zh"
    workers: int = 4


@dataclass(slots=True)
class AppConfig:
    language: str = DEFAULT_LANGUAGE
    enabled_providers: list[str] = field(default_factory=lambda: ["whisper"])
    enabled_features: list[str] = field(default_factory=lambda: ["window"])
    default_provider: str = "whisper"
    default_model: str = "small"
    sensevoice: SenseVoiceConfig = field(default_factory=SenseVoiceConfig)
    volcengine: VolcengineConfig = field(default_factory=VolcengineConfig)
    mimo: MimoConfig = field(default_factory=MimoConfig)

    @classmethod
    def load(cls, settings: Settings) -> "AppConfig":
        if not settings.config_path.exists():
            return cls()

        data = json.loads(settings.config_path.read_text(encoding="utf-8"))
        enabled = data.get("enabled_providers")
        if enabled is None:
            # backwards compat: old configs only had default_provider
            enabled = [data.get("default_provider", "whisper")]
        features = data.get("enabled_features", ["window"])
        return cls(
            language=normalize_language(data.get("language")),
            enabled_providers=enabled,
            enabled_features=features,
            default_provider=data.get("default_provider", "whisper"),
            default_model=data.get("default_model", "small"),
            sensevoice=SenseVoiceConfig(**data.get("sensevoice", {})),
            volcengine=VolcengineConfig(**data.get("volcengine", {})),
            mimo=MimoConfig(**data.get("mimo", {})),
        )

    def save(self, settings: Settings) -> None:
        settings.ensure_directories()
        settings.config_path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

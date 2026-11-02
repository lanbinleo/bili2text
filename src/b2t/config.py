from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WORKSPACE_NAME = ".b2t"


@dataclass(slots=True)
class Settings:
    workspace_root: Path
    downloads_dir: Path
    audio_dir: Path
    transcripts_dir: Path
    transcripts_original_dir: Path
    transcripts_edited_dir: Path
    metadata_dir: Path
    tasks_dir: Path
    cache_dir: Path
    config_path: Path
    app_db_path: Path

    @classmethod
    def from_workspace(cls, workspace: Path | None = None) -> "Settings":
        root = workspace or Path(os.getenv("B2T_HOME", DEFAULT_WORKSPACE_NAME)).expanduser()
        return cls(
            workspace_root=root,
            downloads_dir=root / "downloads",
            audio_dir=root / "audio",
            transcripts_dir=root / "transcripts",
            transcripts_original_dir=root / "transcripts" / "original",
            transcripts_edited_dir=root / "transcripts" / "edited",
            metadata_dir=root / "metadata",
            tasks_dir=root / "tasks",
            cache_dir=root / "cache",
            config_path=root / "config.json",
            app_db_path=root / "app.db",
        )

    def ensure_directories(self) -> None:
        for directory in (
            self.workspace_root,
            self.downloads_dir,
            self.audio_dir,
            self.transcripts_dir,
            self.transcripts_original_dir,
            self.transcripts_edited_dir,
            self.metadata_dir,
            self.tasks_dir,
            self.cache_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

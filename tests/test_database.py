import json
from pathlib import Path

from b2t.config import Settings
from b2t.database import AppDatabase
from b2t.library import WorkspaceLibrary
from b2t.models import ProgressSnapshot, SourceRef, TranscriptResult


def test_settings_create_database_and_workspace_directories(tmp_path: Path) -> None:
    settings = Settings.from_workspace(tmp_path / ".b2t")
    settings.ensure_directories()

    assert settings.transcripts_original_dir.exists()
    assert settings.transcripts_edited_dir.exists()
    assert settings.tasks_dir.exists()


def test_database_persists_task_progress(tmp_path: Path) -> None:
    settings = Settings.from_workspace(tmp_path / ".b2t")
    database = AppDatabase(settings)

    task = database.create_task(
        kind="transcription",
        source_input="BV1xx411c7XD",
        provider="whisper",
        model="small",
    )
    database.record_progress(
        ProgressSnapshot(
            task_id=task.id,
            status="running",
            stage="downloading",
            message="downloading",
            percent=0.25,
        )
    )

    loaded = database.get_task(task.id)
    assert loaded is not None
    assert loaded.current_stage == "downloading"
    assert loaded.progress_percent == 0.25


def test_workspace_library_indexes_existing_files(tmp_path: Path) -> None:
    settings = Settings.from_workspace(tmp_path / ".b2t")
    settings.ensure_directories()
    transcript_path = settings.transcripts_original_dir / "demo-1.txt"
    metadata_path = settings.metadata_dir / "demo-1.json"
    transcript_path.write_text("hello world\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "source": {
                    "raw_input": "BV1xx411c7XD",
                    "kind": "bilibili",
                    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
                    "bv": "BV1xx411c7XD",
                },
                "engine": "whisper",
                "model": "small",
                "audio_path": str(settings.audio_dir / "demo.wav"),
                "video_path": str(settings.downloads_dir / "demo.mp4"),
                "download": {"title": "Demo Title"},
                "language": "zh",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    database = AppDatabase(settings)
    library = WorkspaceLibrary(settings, database)
    library.index_existing_workspace()

    videos = database.list_videos()
    assert len(videos) == 1
    assert videos[0]["title"] == "Demo Title"
    active = database.get_active_transcript_version(int(videos[0]["id"]))
    assert active is not None
    assert active.file_path == str(transcript_path)


def test_register_transcript_result_indexes_local_file_without_download_metadata(tmp_path: Path) -> None:
    settings = Settings.from_workspace(tmp_path / ".b2t")
    settings.ensure_directories()
    transcript_path = settings.transcripts_original_dir / "local-video.txt"
    transcript_path.write_text("hello from local file\n", encoding="utf-8")
    metadata_path = settings.metadata_dir / "local-video.json"
    metadata_path.write_text("{}", encoding="utf-8")

    database = AppDatabase(settings)
    library = WorkspaceLibrary(settings, database)
    video_id = library.register_transcript_result(
        TranscriptResult(
            source=SourceRef(
                raw_input=str(tmp_path / "local-video.mp4"),
                kind="video",
                display_name="local-video",
                path=tmp_path / "local-video.mp4",
            ),
            engine="whisper",
            model="small",
            text="hello from local file",
            audio_path=settings.audio_dir / "local-video.wav",
            transcript_path=transcript_path,
            metadata_path=metadata_path,
            video_path=tmp_path / "local-video.mp4",
            metadata={"language": "zh", "download": None},
        )
    )

    video = database.get_video(video_id)
    assert video is not None
    assert video["title"] == "local-video"
    assert video["source_kind"] == "video"

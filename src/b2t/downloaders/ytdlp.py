from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from b2t.config import Settings
from b2t.downloaders.base import Downloader
from b2t.models import DownloadResult, SourceRef


class YtDlpDownloader(Downloader):
    name = "yt-dlp"

    def download(
        self,
        source: SourceRef,
        settings: Settings,
        *,
        progress=None,
    ) -> DownloadResult:
        if source.kind != "bilibili":
            raise ValueError("yt-dlp downloader only supports bilibili sources")

        settings.ensure_directories()

        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise RuntimeError(
                "yt-dlp is not installed. Run `uv sync` to install the core dependencies."
            ) from exc

        ydl_opts = self._build_ydl_opts(source, settings)
        if progress is not None:
            def progress_hook(data: dict[str, Any]) -> None:
                status = data.get("status")
                if status == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                    downloaded = data.get("downloaded_bytes") or 0
                    stage_progress = (downloaded / total) if total else None
                    progress.running(
                        "downloading",
                        message="downloading",
                        stage_progress=stage_progress,
                        indeterminate=stage_progress is None,
                    )
                elif status == "finished":
                    progress.running("downloading", message="download_finished", stage_progress=1.0)
            ydl_opts["progress_hooks"] = [progress_hook]
            ydl_opts["noprogress"] = False

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source.url or f"https://www.bilibili.com/video/{source.bv}", download=True)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]
            info = ydl.sanitize_info(info)

            video_path = self._resolve_video_path(ydl, info)
            if not video_path.exists():
                raise RuntimeError(f"yt-dlp reported success but no file was found at {video_path}")

        return DownloadResult(
            source=source,
            video_path=video_path,
            title=info.get("title"),
            webpage_url=info.get("webpage_url") or source.url,
            metadata={
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "id": info.get("id"),
                "webpage_url": info.get("webpage_url") or source.url,
            },
        )

    def _build_ydl_opts(self, source: SourceRef, settings: Settings) -> dict[str, Any]:
        ydl_opts: dict[str, Any] = {
            "format": "bv*+ba/b",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "outtmpl": str(settings.downloads_dir / "%(id)s.%(ext)s"),
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
        }

        # Support cookies for authenticated access to Bilibili.
        # Priority: B2T_COOKIE_FILE env var > cookies.txt in workspace.
        cookie_file = os.getenv("B2T_COOKIE_FILE")
        if cookie_file:
            cookie_path = Path(cookie_file).expanduser()
        else:
            cookie_path = settings.workspace_root / "cookies.txt"
        if cookie_path.exists():
            ydl_opts["cookiefile"] = str(cookie_path)

        # Bilibili's CDN frequently blocks proxy/VPN nodes, causing 412
        # or SSL errors. Direct connections usually work better.
        # Set B2T_USE_PROXY=1 to re-enable the system proxy if needed.
        if not os.getenv("B2T_USE_PROXY"):
            ydl_opts["noproxy"] = True

        if source.page is not None:
            ydl_opts["playlist_items"] = str(source.page)
            ydl_opts["noplaylist"] = False
            ydl_opts["outtmpl"] = str(settings.downloads_dir / "%(id)s.%(playlist_index)02d.%(ext)s")
        return ydl_opts

    def _resolve_video_path(self, ydl: Any, info: dict[str, Any]) -> Path:
        requested_downloads = info.get("requested_downloads") or []
        for requested in requested_downloads:
            filepath = requested.get("filepath")
            if filepath:
                return Path(filepath)

        prepared = Path(ydl.prepare_filename(info))
        if prepared.exists():
            return prepared

        merged_mp4 = prepared.with_suffix(".mp4")
        if merged_mp4.exists():
            return merged_mp4

        return prepared

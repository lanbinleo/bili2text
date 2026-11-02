from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from b2t.i18n import dependency_sync_guidance
from b2t.transcribers.base import Transcriber

_DEFAULT_INSTRUCTION = (
    "请把音频里的语音内容逐字转写为文本，只输出转写文本本身，"
    "不要加任何说明、标题、注释或解释。如果音频里没有清晰人声，输出空字符串。"
)


class MimoTranscriber(Transcriber):
    name = "mimo"

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "https://api.xiaomimimo.com/v1",
        model_name: str = "mimo-v2.5-asr",
        language: str = "",
        chunk_seconds: int = 60,
        workers: int = 4,
        max_retries: int = 6,
        cache_dir: Path | None = None,
        max_tokens: int = 4096,
        timeout: float = 300.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model_name = model_name.strip()
        self.language = language.strip()
        self.chunk_seconds = max(0, int(chunk_seconds))
        self.workers = max(1, int(workers))
        self.max_retries = max(1, int(max_retries))
        self.cache_dir = Path(cache_dir) / "mimo" if cache_dir else None
        self.max_tokens = max_tokens
        self.timeout = timeout

    def transcribe(
        self,
        audio_path: Path,
        *,
        prompt: str | None = None,
        progress=None,
    ) -> dict[str, Any]:
        if progress is not None:
            progress.running("transcribing", message="transcribing", indeterminate=True)

        if not self.api_key:
            raise RuntimeError("MiMo provider requires an API key. Run `bili2text bootstrap` first.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "MiMo support is not installed. "
                f"{dependency_sync_guidance('en-US')}"
            ) from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        instruction = self._build_instruction(prompt)
        chunks = self._prepare_chunks(audio_path)

        total = len(chunks)
        done = 0

        def work(item: tuple[int, tuple[int, Path]]) -> tuple[int, int, str]:
            nonlocal done
            idx, (start_sec, chunk_path) = item
            text = self._transcribe_chunk(client, chunk_path, instruction)
            done += 1
            if progress is not None:
                progress.running(
                    "transcribing",
                    message=f"transcribing {done}/{total}",
                    indeterminate=True,
                )
            return idx, start_sec, text

        try:
            with ThreadPoolExecutor(max_workers=min(self.workers, total or 1)) as pool:
                results = sorted(pool.map(work, enumerate(chunks)))
        finally:
            self._cleanup_chunks(chunks, original=audio_path)

        all_text: list[str] = []
        segments: list[dict[str, Any]] = []
        for idx, start_sec, text in results:
            if text:
                all_text.append(text)
            segments.append(
                {
                    "id": idx,
                    "start": float(start_sec),
                    "end": float(start_sec) + float(self.chunk_seconds or 0),
                    "text": text,
                }
            )

        return {
            "text": "\n".join(all_text).strip(),
            "segments": segments,
            "language": self.language or None,
            "model": self.model_name,
            "raw_response": None,
        }

    def _build_instruction(self, user_prompt: str | None) -> str:
        parts = [_DEFAULT_INSTRUCTION]
        if self.language:
            parts.append(f"音频语言提示: {self.language}.")
        if user_prompt:
            parts.append(user_prompt.strip())
        return "\n".join(parts)

    def _prepare_chunks(self, audio_path: Path) -> list[tuple[int, Path]]:
        if self.chunk_seconds <= 0 or not shutil.which("ffmpeg"):
            return [(0, audio_path)]

        duration = self._probe_duration(audio_path)
        if duration is None or duration <= self.chunk_seconds:
            return [(0, audio_path)]

        chunks_dir = audio_path.parent / f".{audio_path.stem}.mimo_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        chunks: list[tuple[int, Path]] = []
        start = 0
        idx = 0
        while start < duration:
            chunk_path = chunks_dir / f"{idx:04d}.wav"
            command = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-ss",
                str(start),
                "-t",
                str(self.chunk_seconds),
                "-i",
                str(audio_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(chunk_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 or not chunk_path.exists() or chunk_path.stat().st_size == 0:
                self._cleanup_chunks(chunks, original=audio_path)
                if chunk_path.exists():
                    chunk_path.unlink(missing_ok=True)
                try:
                    chunks_dir.rmdir()
                except OSError:
                    pass
                raise RuntimeError(
                    f"ffmpeg failed to split audio for MiMo: {result.stderr.strip() or 'unknown error'}"
                )
            chunks.append((start, chunk_path))
            start += self.chunk_seconds
            idx += 1
        return chunks

    def _probe_duration(self, audio_path: Path) -> float | None:
        if not shutil.which("ffprobe"):
            return None
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        try:
            return float(result.stdout.strip())
        except ValueError:
            return None

    def _cleanup_chunks(self, chunks: list[tuple[int, Path]], *, original: Path) -> None:
        chunks_dir: Path | None = None
        for _, chunk_path in chunks:
            if chunk_path == original:
                continue
            try:
                chunk_path.unlink(missing_ok=True)
            except OSError:
                pass
            chunks_dir = chunk_path.parent
        if chunks_dir is not None:
            try:
                chunks_dir.rmdir()
            except OSError:
                pass

    def _cache_path(self, audio_bytes: bytes) -> Path | None:
        """Cache key = chunk audio content + model + language.

        Content-addressed on purpose: a re-run re-splits the audio into byte-identical
        chunks, so a resumed task hits the cache regardless of file names or which chunk
        index it landed on. Changing model or language misses, as it should.
        """
        if self.cache_dir is None:
            return None
        digest = hashlib.sha256(audio_bytes)
        digest.update(f"|{self.model_name}|{self.language}".encode("utf-8"))
        return self.cache_dir / f"{digest.hexdigest()}.txt"

    def _transcribe_chunk(self, client, chunk_path: Path, instruction: str) -> str:
        audio_bytes = chunk_path.read_bytes()

        cache_path = self._cache_path(audio_bytes)
        if cache_path is not None and cache_path.exists():
            try:
                return cache_path.read_text(encoding="utf-8")
            except OSError:
                pass  # unreadable cache entry is not fatal, just re-transcribe

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        fmt = chunk_path.suffix.lstrip(".").lower() or "wav"
        mime = "audio/wav" if fmt == "wav" else "audio/mpeg" if fmt in ("mp3", "mpeg") else f"audio/{fmt}"
        data_uri = f"data:{mime};base64,{audio_b64}"
        # mimo-v2.5-asr: 音频走 input_audio.data 的 data-URI 格式，语言经 asr_options 指定，
        # ASR 模型不需要 text instruction（参数保留以兼容调用方签名）。
        # 并发跑满时服务端会回 429，逐次退避重试，别让整条任务因为一片挂掉。
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_audio", "input_audio": {"data": data_uri}},
                            ],
                        }
                    ],
                    extra_body={"asr_options": {"language": self.language or "auto"}},
                )
            except Exception as exc:  # noqa: BLE001 - retry on any transport/rate-limit error
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                continue

            if not getattr(response, "choices", None):
                return ""
            message = response.choices[0].message
            if message is None:
                return ""
            text = (getattr(message, "content", None) or "").strip()
            self._store_cache(cache_path, text)
            return text

        raise RuntimeError(f"MiMo transcription failed for {chunk_path.name}: {last_error}")

    def _store_cache(self, cache_path: Path | None, text: str) -> None:
        """Persist a finished chunk so a later re-run skips the API call.

        Write to a temp file then rename, so an interrupted run can never leave a
        half-written entry that a resume would happily trust.
        """
        if cache_path is None:
            return
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = cache_path.with_suffix(".partial")
            tmp_path.write_text(text, encoding="utf-8")
            tmp_path.replace(cache_path)
        except OSError:
            pass  # caching is an optimization; never fail the transcription over it

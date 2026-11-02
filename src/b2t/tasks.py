from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import TYPE_CHECKING, Callable

from b2t.database import AppDatabase
from b2t.library import WorkspaceLibrary
from b2t.models import TaskRecord
from b2t.pipeline import B2TPipeline
from b2t.progress import ProgressCallback, ProgressReporter

if TYPE_CHECKING:
    from b2t.sse import SSEManager


PipelineFactory = Callable[[str, str], B2TPipeline]


class TaskService:
    def __init__(
        self,
        *,
        database: AppDatabase,
        library: WorkspaceLibrary,
        pipeline_factory: PipelineFactory,
        sse_manager: "SSEManager | None" = None,
    ) -> None:
        self.database = database
        self.library = library
        self.pipeline_factory = pipeline_factory
        self.sse_manager = sse_manager
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="b2t-task")
        self._listeners: dict[str, list[ProgressCallback]] = {}
        self._futures: dict[str, Future[object]] = {}
        self._lock = Lock()

    def ensure_indexed(self) -> None:
        self.library.index_existing_workspace()

    def submit_transcription(
        self,
        *,
        source: str,
        provider: str,
        model: str,
        prompt: str = "",
        listener: ProgressCallback | None = None,
    ) -> TaskRecord:
        task = self.database.create_task(
            kind="transcription",
            source_input=source,
            provider=provider,
            model=model,
        )
        if listener is not None:
            self.add_listener(task.id, listener)
        reporter = ProgressReporter(task.id, callback=self._handle_progress)
        reporter.queued("queued")
        future = self.executor.submit(self._run_transcription, task.id, source, provider, model, prompt)
        with self._lock:
            self._futures[task.id] = future
        return task

    def wait_for_task(self, task_id: str) -> TaskRecord:
        with self._lock:
            future = self._futures.get(task_id)
        if future is not None:
            future.result()
        task = self.database.get_task(task_id)
        if task is None:
            raise RuntimeError(f"task not found: {task_id}")
        return task

    def add_listener(self, task_id: str, callback: ProgressCallback) -> None:
        with self._lock:
            self._listeners.setdefault(task_id, []).append(callback)

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self.database.get_task(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return self.database.list_tasks()

    def _run_transcription(self, task_id: str, source: str, provider: str, model: str, prompt: str) -> None:
        reporter = ProgressReporter(task_id, callback=self._handle_progress)
        try:
            reporter.running("preparing", message="preparing")
            pipeline = self.pipeline_factory(provider, model)
            result = pipeline.transcribe(source, prompt=prompt or None, progress=reporter)
            reporter.running("indexing", message="indexing", stage_progress=0.5)
            video_id = self.library.register_transcript_result(result)
            reporter.completed("completed")
            self.database.complete_task(task_id, video_id=video_id, message="completed")
        except Exception as exc:
            reporter.failed(str(exc))
            self.database.fail_task(task_id, error_message=str(exc))
            raise

    def _handle_progress(self, snapshot) -> None:  # type: ignore[no-untyped-def]
        self.database.record_progress(snapshot)
        if self.sse_manager is not None:
            self.sse_manager.publish(snapshot)
            if snapshot.status in {"completed", "failed", "cancelled"}:
                self.sse_manager.notify_terminal(snapshot.task_id)
        with self._lock:
            callbacks = list(self._listeners.get(snapshot.task_id, []))
        for callback in callbacks:
            callback(snapshot)

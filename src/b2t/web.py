from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from b2t.database import AppDatabase
from b2t.i18n import tr
from b2t.inputs import parse_source_list
from b2t.library import WorkspaceLibrary
from b2t.models import TaskRecord
from b2t.tasks import TaskService


class TranscribeTaskRequest(BaseModel):
    source: str
    provider: str = "whisper"
    model: str = "small"
    prompt: str = ""


class BatchTranscribeTaskRequest(BaseModel):
    sources: list[str] | None = None
    source_text: str | None = None
    provider: str = "whisper"
    model: str = "small"
    prompt: str = ""


class TranscriptUpdateRequest(BaseModel):
    text: str


class CategoryRequest(BaseModel):
    name: str | None = None
    category_id: int | None = None


class TagRequest(BaseModel):
    name: str | None = None
    tag_id: int | None = None


def create_app(
    *,
    task_service: TaskService,
    library: WorkspaceLibrary,
    database: AppDatabase,
    default_provider: str = "whisper",
    default_model: str = "small",
    language: str = "zh-CN",
) -> FastAPI:
    templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
    app = FastAPI(title="bili2text")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "error": None,
                "values": {
                    "source": "",
                    "provider": default_provider,
                    "model": default_model,
                    "prompt": "",
                },
                "videos": database.list_videos(),
                "lang": language,
                "t": lambda key, **kwargs: tr(language, key, **kwargs),
            },
        )

    @app.post("/transcribe", response_class=HTMLResponse)
    async def transcribe_from_form(
        request: Request,
        source: str = Form(...),
        provider: str = Form("whisper"),
        model: str = Form("small"),
        prompt: str = Form(""),
    ) -> HTMLResponse:
        try:
            sources = parse_source_list(source)
        except ValueError as exc:
            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "error": str(exc),
                    "values": {
                        "source": source,
                        "provider": provider,
                        "model": model,
                        "prompt": prompt,
                    },
                    "videos": database.list_videos(),
                    "lang": language,
                    "t": lambda key, **kwargs: tr(language, key, **kwargs),
                },
                status_code=400,
            )

        tasks = _submit_transcription_tasks(
            task_service,
            sources=sources,
            provider=provider,
            model=model,
            prompt=prompt,
        )
        if len(tasks) > 1:
            return templates.TemplateResponse(
                request,
                "batch.html",
                {
                    "tasks": [asdict(task) for task in tasks],
                    "lang": language,
                    "t": lambda key, **kwargs: tr(language, key, **kwargs),
                },
            )

        task = tasks[0]
        return templates.TemplateResponse(
            request,
            "task.html",
            {
                "task_id": task.id,
                "lang": language,
                "t": lambda key, **kwargs: tr(language, key, **kwargs),
            },
        )

    @app.get("/tasks/batch", response_class=HTMLResponse)
    async def batch_task_page(request: Request, ids: str = Query("")) -> HTMLResponse:
        task_ids = [task_id.strip() for task_id in ids.split(",") if task_id.strip()]
        tasks = []
        for task_id in task_ids:
            task = database.get_task(task_id)
            if task is not None:
                tasks.append(asdict(task))
        return templates.TemplateResponse(
            request,
            "batch.html",
            {
                "tasks": tasks,
                "lang": language,
                "t": lambda key, **kwargs: tr(language, key, **kwargs),
            },
        )

    @app.get("/tasks/{task_id}", response_class=HTMLResponse)
    async def task_page(request: Request, task_id: str) -> HTMLResponse:
        task = database.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        return templates.TemplateResponse(
            request,
            "task.html",
            {
                "task_id": task_id,
                "task": asdict(task),
                "lang": language,
                "t": lambda key, **kwargs: tr(language, key, **kwargs),
            },
        )

    @app.get("/videos/{video_id}", response_class=HTMLResponse)
    async def video_page(request: Request, video_id: int) -> HTMLResponse:
        video = database.get_video(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="video not found")
        transcript = library.load_active_transcript(video_id)
        versions = [asdict(version) for version in database.list_transcript_versions(video_id)]
        return templates.TemplateResponse(
            request,
            "video.html",
            {
                "video": video,
                "transcript": transcript,
                "versions": versions,
                "categories": database.list_categories(),
                "tags": database.list_tags(),
                "lang": language,
                "t": lambda key, **kwargs: tr(language, key, **kwargs),
            },
        )

    @app.post("/videos/{video_id}/edit")
    async def edit_video_transcript(video_id: int, text: str = Form(...)) -> RedirectResponse:
        library.save_edited_transcript(video_id, text)
        return RedirectResponse(url=f"/videos/{video_id}", status_code=303)

    @app.post("/videos/{video_id}/category")
    async def assign_video_category(video_id: int, category_name: str = Form("")) -> RedirectResponse:
        category_name = category_name.strip()
        category_id = None
        if category_name:
            category = database.create_category(category_name)
            category_id = int(category["id"])
        database.assign_category(video_id, category_id)
        return RedirectResponse(url=f"/videos/{video_id}", status_code=303)

    @app.post("/videos/{video_id}/tags")
    async def add_video_tag(video_id: int, tag_name: str = Form("")) -> RedirectResponse:
        tag_name = tag_name.strip()
        if tag_name:
            tag = database.create_tag(tag_name)
            database.add_video_tag(video_id, int(tag["id"]))
        return RedirectResponse(url=f"/videos/{video_id}", status_code=303)

    @app.post("/api/tasks/transcribe")
    async def create_transcription_task(payload: TranscribeTaskRequest) -> JSONResponse:
        task = task_service.submit_transcription(
            source=payload.source,
            provider=payload.provider,
            model=payload.model,
            prompt=payload.prompt,
        )
        return JSONResponse({"task_id": task.id, "status": task.status})

    @app.post("/api/tasks/batch")
    async def create_batch_transcription_tasks(payload: BatchTranscribeTaskRequest) -> JSONResponse:
        source_chunks = list(payload.sources or [])
        if payload.source_text:
            source_chunks.append(payload.source_text)
        try:
            sources = parse_source_list("\n".join(source_chunks))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        tasks = _submit_transcription_tasks(
            task_service,
            sources=sources,
            provider=payload.provider,
            model=payload.model,
            prompt=payload.prompt,
        )
        return JSONResponse(
            {
                "items": [asdict(task) for task in tasks],
                "count": len(tasks),
            }
        )

    @app.get("/api/tasks")
    async def list_tasks(
        status: str | None = Query(None),
        provider: str | None = Query(None),
    ) -> JSONResponse:
        return JSONResponse(
            {
                "items": [asdict(task) for task in task_service.list_tasks() if (status is None or task.status == status) and (provider is None or task.provider == provider)],
                "filters": {"status": status, "provider": provider},
            }
        )

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str) -> JSONResponse:
        task = task_service.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        return JSONResponse(asdict(task))

    @app.get("/api/tasks/{task_id}/progress")
    async def get_task_progress(task_id: str) -> JSONResponse:
        task = task_service.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        return JSONResponse(asdict(task))

    @app.get("/api/tasks/{task_id}/events")
    async def get_task_events(task_id: str) -> JSONResponse:
        task = task_service.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        return JSONResponse({"items": database.list_task_events(task_id)})

    @app.get("/api/videos")
    async def list_videos_api(
        query: str | None = Query(None),
        category_id: int | None = Query(None),
        tag_id: int | None = Query(None),
    ) -> JSONResponse:
        return JSONResponse(
            {
                "items": database.list_videos(query=query, category_id=category_id, tag_id=tag_id),
                "filters": {
                    "query": query,
                    "category_id": category_id,
                    "tag_id": tag_id,
                },
            }
        )

    @app.get("/api/videos/{video_id}")
    async def get_video_api(video_id: int) -> JSONResponse:
        video = database.get_video(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="video not found")
        return JSONResponse(video)

    @app.get("/api/videos/{video_id}/transcript")
    async def get_video_transcript(video_id: int, version_id: int | None = Query(None)) -> JSONResponse:
        if version_id is None:
            return JSONResponse(library.load_active_transcript(video_id))
        return JSONResponse(library.load_transcript_version(video_id, version_id))

    @app.get("/api/videos/{video_id}/metadata")
    async def get_video_metadata(video_id: int) -> JSONResponse:
        return JSONResponse(library.load_video_metadata(video_id))

    @app.put("/api/videos/{video_id}/transcript")
    async def update_video_transcript(video_id: int, payload: TranscriptUpdateRequest) -> JSONResponse:
        version_id = library.save_edited_transcript(video_id, payload.text)
        return JSONResponse({"video_id": video_id, "version_id": version_id})

    @app.get("/api/videos/{video_id}/versions")
    async def list_video_versions(video_id: int) -> JSONResponse:
        versions = [asdict(version) for version in database.list_transcript_versions(video_id)]
        return JSONResponse({"items": versions})

    @app.get("/api/videos/{video_id}/versions/{version_id}")
    async def get_video_version(video_id: int, version_id: int) -> JSONResponse:
        return JSONResponse(library.load_transcript_version(video_id, version_id))

    @app.post("/api/videos/{video_id}/versions/{version_id}/activate")
    async def activate_video_version(video_id: int, version_id: int) -> JSONResponse:
        database.activate_transcript_version(video_id, version_id)
        return JSONResponse({"video_id": video_id, "version_id": version_id})

    @app.get("/api/categories")
    async def list_categories_api() -> JSONResponse:
        return JSONResponse({"items": database.list_categories()})

    @app.post("/api/categories")
    async def create_category_api(payload: CategoryRequest) -> JSONResponse:
        if not payload.name:
            raise HTTPException(status_code=400, detail="name is required")
        category = database.create_category(payload.name)
        return JSONResponse(category)

    @app.put("/api/categories/{category_id}")
    async def update_category_api(category_id: int, payload: CategoryRequest) -> JSONResponse:
        if not payload.name:
            raise HTTPException(status_code=400, detail="name is required")
        category = database.update_category(category_id, payload.name)
        if category is None:
            raise HTTPException(status_code=404, detail="category not found")
        return JSONResponse(category)

    @app.delete("/api/categories/{category_id}")
    async def delete_category_api(category_id: int) -> JSONResponse:
        database.delete_category(category_id)
        return JSONResponse({"category_id": category_id})

    @app.post("/api/videos/{video_id}/category")
    async def assign_category_api(video_id: int, payload: CategoryRequest) -> JSONResponse:
        category_id = payload.category_id
        if category_id is None and payload.name:
            category = database.create_category(payload.name)
            category_id = int(category["id"])
        database.assign_category(video_id, category_id)
        return JSONResponse({"video_id": video_id, "category_id": category_id})

    @app.get("/api/tags")
    async def list_tags_api() -> JSONResponse:
        return JSONResponse({"items": database.list_tags()})

    @app.post("/api/tags")
    async def create_tag_api(payload: TagRequest) -> JSONResponse:
        if not payload.name:
            raise HTTPException(status_code=400, detail="name is required")
        tag = database.create_tag(payload.name)
        return JSONResponse(tag)

    @app.put("/api/tags/{tag_id}")
    async def update_tag_api(tag_id: int, payload: TagRequest) -> JSONResponse:
        if not payload.name:
            raise HTTPException(status_code=400, detail="name is required")
        tag = database.update_tag(tag_id, payload.name)
        if tag is None:
            raise HTTPException(status_code=404, detail="tag not found")
        return JSONResponse(tag)

    @app.delete("/api/tags/{tag_id}")
    async def delete_tag_api(tag_id: int) -> JSONResponse:
        database.delete_tag(tag_id)
        return JSONResponse({"tag_id": tag_id})

    @app.post("/api/videos/{video_id}/tags")
    async def add_video_tag_api(video_id: int, payload: TagRequest) -> JSONResponse:
        tag_id = payload.tag_id
        if tag_id is None and payload.name:
            tag = database.create_tag(payload.name)
            tag_id = int(tag["id"])
        if tag_id is None:
            raise HTTPException(status_code=400, detail="tag is required")
        database.add_video_tag(video_id, tag_id)
        return JSONResponse({"video_id": video_id, "tag_id": tag_id})

    @app.delete("/api/videos/{video_id}/tags/{tag_id}")
    async def remove_video_tag_api(video_id: int, tag_id: int) -> JSONResponse:
        database.remove_video_tag(video_id, tag_id)
        return JSONResponse({"video_id": video_id, "tag_id": tag_id})

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


def _submit_transcription_tasks(
    task_service: TaskService,
    *,
    sources: list[str],
    provider: str,
    model: str,
    prompt: str = "",
) -> list[TaskRecord]:
    return [
        task_service.submit_transcription(
            source=source,
            provider=provider,
            model=model,
            prompt=prompt,
        )
        for source in sources
    ]

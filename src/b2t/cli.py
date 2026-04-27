from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import typer

from b2t import __version__
from b2t.bootstrap import ensure_bootstrap, run_bootstrap
from b2t.cli_progress import TqdmTaskRenderer
from b2t.config import Settings
from b2t.database import AppDatabase
from b2t.factory import build_pipeline
from b2t.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, dependency_sync_guidance, resolve_language, tr
from b2t.inputs import parse_source_list
from b2t.library import WorkspaceLibrary
from b2t.tasks import TaskService
from b2t.user_config import AppConfig


def create_app(language: str = DEFAULT_LANGUAGE) -> typer.Typer:
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help=tr(language, "app_help"),
    )

    @app.callback(invoke_without_command=True)
    def version_callback(
        version: bool = typer.Option(
            False,
            "--version",
            help=tr(language, "show_version"),
            is_eager=True,
        ),
    ) -> None:
        if version:
            typer.echo(__version__)
            raise typer.Exit()

    @app.command("transcribe", help=tr(language, "cmd_transcribe_help"))
    @app.command("tx", hidden=True)
    def transcribe(
        source: str = typer.Argument(..., help=tr(language, "arg_source_help")),
        provider: str | None = typer.Option(None, "--provider", help=tr(language, "opt_provider_help")),
        model: str | None = typer.Option(None, "--model", help=tr(language, "opt_model_help")),
        prompt: str = typer.Option("", "--prompt", help=tr(language, "opt_prompt_help")),
        output: Path | None = typer.Option(None, "--output", help=tr(language, "opt_output_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Download or open media, then transcribe it with the selected provider."""
        try:
            settings, config = _load_runtime(workspace=workspace, provider=provider, model=model)
            renderer = TqdmTaskRenderer(config.language)
            service = _build_task_service(
                settings=settings,
                config=config,
                provider=provider,
                model=model,
            )
            task = service.submit_transcription(
                source=source,
                provider=provider or config.default_provider,
                model=model or config.default_model,
                prompt=prompt,
                listener=renderer,
            )
            typer.echo(tr(config.language, "task_submitted", task_id=task.id))
            task = service.wait_for_task(task.id)
            if task.video_id is None:
                raise RuntimeError("transcription completed but no video record was created")
            video = service.database.get_video(task.video_id)
            if video is None:
                raise RuntimeError(f"video record not found: {task.video_id}")
            transcript = service.library.load_active_transcript(task.video_id)
        except Exception as exc:
            message = tr(_detect_preferred_language(workspace), "error_prefix", message=exc)
            typer.secho(message, err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        typer.echo(tr(config.language, "transcript_saved", path=transcript["file_path"]))
        typer.echo(tr(config.language, "metadata_saved", path=video["metadata_path"]))

    @app.command("batch", help=tr(language, "cmd_batch_help"))
    def batch_transcribe(
        sources: list[str] | None = typer.Argument(None, help=tr(language, "arg_sources_help")),
        source_file: Path | None = typer.Option(None, "--file", "-f", help=tr(language, "opt_source_file_help")),
        provider: str | None = typer.Option(None, "--provider", help=tr(language, "opt_provider_help")),
        model: str | None = typer.Option(None, "--model", help=tr(language, "opt_model_help")),
        prompt: str = typer.Option("", "--prompt", help=tr(language, "opt_prompt_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Submit multiple transcription tasks from arguments or a newline-separated file."""
        selected_language = _detect_preferred_language(workspace)
        try:
            settings, config = _load_runtime(workspace=workspace, provider=provider, model=model)
            service = _build_task_service(
                settings=settings,
                config=config,
                provider=provider,
                model=model,
            )
            source_values = _collect_batch_sources(sources or [], source_file)
            tasks = [
                service.submit_transcription(
                    source=source,
                    provider=provider or config.default_provider,
                    model=model or config.default_model,
                    prompt=prompt,
                )
                for source in source_values
            ]
            typer.echo(tr(config.language, "batch_submitted", count=len(tasks)))
            for task in tasks:
                typer.echo(f"{task.id}\t{task.source_input}")

            failed = 0
            for task in tasks:
                try:
                    completed = service.wait_for_task(task.id)
                except Exception as exc:
                    failed += 1
                    typer.secho(
                        tr(config.language, "batch_task_failed", task_id=task.id, message=exc),
                        err=True,
                        fg=typer.colors.RED,
                    )
                    continue
                if completed.status == "completed":
                    typer.echo(tr(config.language, "batch_task_completed", task_id=completed.id))
                else:
                    failed += 1
                    typer.secho(
                        tr(config.language, "batch_task_failed", task_id=completed.id, message=completed.error_message),
                        err=True,
                        fg=typer.colors.RED,
                    )
        except Exception as exc:
            message = tr(selected_language, "error_prefix", message=exc)
            typer.secho(message, err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        if failed:
            raise typer.Exit(code=1)

    @app.command("doctor", help=tr(language, "cmd_doctor_help"))
    @app.command("diag", hidden=True)
    def doctor(
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Print the current runtime requirements and what is missing."""
        selected_language = _detect_preferred_language(workspace)
        ffmpeg = shutil.which("ffmpeg")
        rows: list[tuple[str, str]] = [(tr(selected_language, "doctor_ffmpeg"), ffmpeg or tr(selected_language, "status_missing"))]

        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            rows.insert(0, (tr(selected_language, "doctor_yt_dlp"), tr(selected_language, "status_missing")))
        else:
            rows.insert(0, (tr(selected_language, "doctor_yt_dlp"), tr(selected_language, "status_ok")))

        try:
            import whisper  # noqa: F401
        except ImportError:
            rows.append((tr(selected_language, "doctor_whisper"), tr(selected_language, "status_missing")))
        else:
            rows.append((tr(selected_language, "doctor_whisper"), tr(selected_language, "status_ok")))

        try:
            import funasr_onnx  # noqa: F401
        except ImportError:
            rows.append((tr(selected_language, "doctor_sensevoice"), tr(selected_language, "status_missing")))
        else:
            rows.append((tr(selected_language, "doctor_sensevoice"), tr(selected_language, "status_ok")))

        try:
            import requests  # noqa: F401
        except ImportError:
            rows.append((tr(selected_language, "doctor_requests"), tr(selected_language, "status_missing")))
        else:
            rows.append((tr(selected_language, "doctor_requests"), tr(selected_language, "status_ok")))

        for label, status in rows:
            typer.echo(f"{label}: {status}")

    @app.command("bootstrap", help=tr(language, "cmd_bootstrap_help"))
    @app.command("init", hidden=True)
    def bootstrap(
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
        sync_only: bool = typer.Option(False, "--sync-only", help=tr(language, "bootstrap_sync_only")),
    ) -> None:
        """Create or update the local bili2text config."""
        settings = Settings.from_workspace(workspace)
        if sync_only and not settings.config_path.exists():
            typer.secho(tr(_detect_preferred_language(workspace), "bootstrap_sync_only_missing_config"), err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1)
        run_bootstrap(settings=settings, interactive=not sync_only)

    @app.command("web", help=tr(language, "cmd_web_help"))
    @app.command("ui", hidden=True)
    def web_ui(
        host: str = typer.Option("127.0.0.1", "--host", help=tr(language, "opt_host_help")),
        port: int = typer.Option(8000, "--port", help=tr(language, "opt_port_help")),
        provider: str | None = typer.Option(None, "--provider", help=tr(language, "opt_provider_help")),
        model: str | None = typer.Option(None, "--model", help=tr(language, "opt_model_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Launch the plain HTML web interface."""
        _run_server(host=host, port=port, provider=provider, model=model, workspace=workspace)

    @app.command("server", help=tr(language, "cmd_server_help"))
    @app.command("srv", hidden=True)
    def server_mode(
        host: str = typer.Option("0.0.0.0", "--host", help=tr(language, "opt_host_help")),
        port: int = typer.Option(8000, "--port", help=tr(language, "opt_port_help")),
        provider: str | None = typer.Option(None, "--provider", help=tr(language, "opt_provider_help")),
        model: str | None = typer.Option(None, "--model", help=tr(language, "opt_model_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Launch the server feature for Docker or LAN deployment."""
        _run_server(host=host, port=port, provider=provider, model=model, workspace=workspace)

    @app.command("window", help=tr(language, "cmd_window_help"))
    @app.command("win", hidden=True)
    def window_mode(
        provider: str | None = typer.Option(None, "--provider", help=tr(language, "opt_provider_help")),
        model: str | None = typer.Option(None, "--model", help=tr(language, "opt_model_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Launch the Tk window feature."""
        from b2t.window_app import run_window

        settings, config = _load_runtime(workspace=workspace, provider=provider, model=model)

        run_window(
            pipeline_factory=lambda selected_provider, selected_model, selected_workspace: build_pipeline(
                settings=Settings.from_workspace(selected_workspace or settings.workspace_root),
                config=config,
                provider=selected_provider or provider or config.default_provider,
                model=selected_model or model or config.default_model,
            ),
            default_provider=provider or config.default_provider,
            default_model=model or config.default_model,
            default_workspace=settings.workspace_root,
            language=config.language,
        )

    @app.command("language", help=tr(language, "cmd_language_help"))
    @app.command("lang", hidden=True)
    def language_command(
        value: str = typer.Argument(..., help=tr(language, "opt_language_help")),
        workspace: Path | None = typer.Option(None, "--workspace", help=tr(language, "opt_workspace_help")),
    ) -> None:
        """Switch the preferred interface language."""
        resolved = resolve_language(value)
        if not resolved:
            typer.secho(tr(language, "unsupported_language", language=value), err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1)

        settings = Settings.from_workspace(workspace)
        config = AppConfig.load(settings)
        config.language = resolved
        config.save(settings)
        typer.echo(tr(resolved, "language_updated", language=SUPPORTED_LANGUAGES[resolved]))

    return app


def main() -> None:
    create_app(_detect_preferred_language())(prog_name="bili2text")


def _load_runtime(
    *,
    workspace: Path | None,
    provider: str | None = None,
    model: str | None = None,
    allow_bootstrap: bool = True,
) -> tuple[Settings, AppConfig]:
    settings = Settings.from_workspace(workspace)
    config = ensure_bootstrap(
        settings=settings,
        allow_prompt=allow_bootstrap and sys.stdin.isatty(),
    )
    if provider:
        config.default_provider = provider
    if model:
        config.default_model = model
    return settings, config


def _run_server(*, host: str, port: int, provider: str | None, model: str | None, workspace: Path | None) -> None:
    selected_language = _detect_preferred_language(workspace)
    try:
        import uvicorn
    except ImportError as exc:
        typer.secho(
            tr(
                selected_language,
                "missing_dependency",
                name="web/server",
                guidance=dependency_sync_guidance(selected_language),
            ),
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1) from exc

    from b2t.web import create_app

    settings, config = _load_runtime(workspace=workspace, provider=provider, model=model)
    service = _build_task_service(settings=settings, config=config, provider=provider, model=model)
    app_instance = create_app(
        task_service=service,
        library=service.library,
        database=service.database,
        default_provider=provider or config.default_provider,
        default_model=model or config.default_model,
        language=config.language,
    )
    uvicorn.run(app_instance, host=host, port=port)


def _detect_preferred_language(workspace: Path | None = None) -> str:
    env_language = resolve_language(os.getenv("B2T_LANG"))
    if env_language:
        return env_language

    settings = Settings.from_workspace(workspace)
    if settings.config_path.exists():
        return AppConfig.load(settings).language
    return DEFAULT_LANGUAGE


def _build_task_service(
    *,
    settings: Settings,
    config: AppConfig,
    provider: str | None = None,
    model: str | None = None,
) -> TaskService:
    database = AppDatabase(settings)
    library = WorkspaceLibrary(settings, database)
    service = TaskService(
        database=database,
        library=library,
        pipeline_factory=lambda selected_provider, selected_model: build_pipeline(
            settings=settings,
            config=config,
            provider=selected_provider or provider or config.default_provider,
            model=selected_model or model or config.default_model,
        ),
    )
    service.ensure_indexed()
    return service


def _collect_batch_sources(sources: list[str], source_file: Path | None) -> list[str]:
    chunks: list[str] = []
    if source_file is not None:
        chunks.append(source_file.expanduser().read_text(encoding="utf-8"))
    chunks.extend(sources)
    return parse_source_list("\n".join(chunks))


app = create_app(DEFAULT_LANGUAGE)

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel

from b2t.config import Settings
from b2t.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, tr
from b2t.user_config import ALL_FEATURES, ALL_PROVIDERS, AppConfig


def uv_available(which=shutil.which) -> bool:
    return which("uv") is not None


def collect_required_extras(*, providers: list[str], features: list[str]) -> list[str]:
    extras: list[str] = []
    for name in [*providers, *features]:
        mapped = name if name != "window" else ""
        if mapped and mapped not in extras:
            extras.append(mapped)
    return extras


def build_uv_sync_command(*, workspace, extras: list[str]) -> list[str]:
    command = ["uv", "sync"]
    for extra in extras:
        command.extend(["--extra", extra])
    return command


@dataclass(slots=True)
class BootstrapEnvironmentResult:
    ok: bool
    reason: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""


def sync_selected_environment(
    *,
    workspace: Path,
    extras: list[str],
    which=shutil.which,
    runner=subprocess.run,
) -> BootstrapEnvironmentResult:
    command = build_uv_sync_command(workspace=workspace, extras=extras)
    if not uv_available(which):
        return BootstrapEnvironmentResult(ok=False, reason="missing_uv", command=command)
    assert runner is not None
    completed = runner(command, cwd=workspace, capture_output=True, encoding="utf-8", check=False)
    return BootstrapEnvironmentResult(
        ok=completed.returncode == 0,
        reason="ok" if completed.returncode == 0 else "sync_failed",
        command=command,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def sync_environment_for_config(
    *,
    project_root: Path,
    config: AppConfig,
    which=shutil.which,
    runner=subprocess.run,
) -> BootstrapEnvironmentResult:
    extras = collect_required_extras(
        providers=config.enabled_providers,
        features=config.enabled_features,
    )
    return sync_selected_environment(
        workspace=project_root,
        extras=extras,
        which=which,
        runner=runner,
    )


def run_bootstrap(*, settings: Settings, interactive: bool = True) -> AppConfig:
    config = AppConfig.load(settings)
    project_root = _find_project_root()
    if not interactive:
        _auto_sync(
            console=Console(),
            project_root=project_root,
            config=config,
            language=config.language,
        )
        return config

    console = Console()
    lang = config.language or DEFAULT_LANGUAGE

    # ── Check for existing configuration ────────────────────
    has_existing = settings.config_path.exists()

    if has_existing:
        console.print()
        console.print(
            Panel.fit(
                tr(lang, "bootstrap_current_summary",
                   providers=", ".join(config.enabled_providers) or "—",
                   features=", ".join(config.enabled_features) or "—",
                   default=config.default_provider or "—"),
                title=tr(lang, "bootstrap_current_title"),
                border_style="cyan",
            )
        )
        reconfigure = inquirer.confirm(
            message=tr(lang, "bootstrap_reconfigure_prompt"),
            default=False,
        ).execute()
        if not reconfigure:
            console.print(f"[dim]{tr(lang, 'bootstrap_reconfigure_skipped')}[/dim]")
            return config
        console.print()
    else:
        console.print()
        console.print(
            Panel.fit(
                tr(lang, "bootstrap_intro"),
                title=tr(lang, "bootstrap_title"),
                border_style="cyan",
            )
        )

    # ── 1. Language ──────────────────────────────────────────
    console.print()
    console.rule(f"[bold]{tr(lang, 'bootstrap_step_language')}[/bold]")
    language_choices = [
        {"name": f"{label}  ({code})", "value": code}
        for code, label in SUPPORTED_LANGUAGES.items()
    ]
    config.language = inquirer.select(
        message=tr(lang, "bootstrap_language_prompt"),
        choices=language_choices,
        default=config.language,
    ).execute()
    lang = config.language

    # ── 2. Providers (checkbox) ──────────────────────────────
    console.print()
    console.rule(f"[bold]{tr(lang, 'bootstrap_step_providers')}[/bold]")
    provider_choices = [
        {
            "name": f"whisper    — {tr(lang, 'provider_whisper_short')}",
            "value": "whisper",
            "enabled": "whisper" in config.enabled_providers,
        },
        {
            "name": f"sensevoice — {tr(lang, 'provider_sensevoice_short')}",
            "value": "sensevoice",
            "enabled": "sensevoice" in config.enabled_providers,
        },
        {
            "name": f"volcengine — {tr(lang, 'provider_volcengine_short')}",
            "value": "volcengine",
            "enabled": "volcengine" in config.enabled_providers,
        },
        {
            "name": f"mimo       — {tr(lang, 'provider_mimo_short')}",
            "value": "mimo",
            "enabled": "mimo" in config.enabled_providers,
        },
    ]
    selected_providers: list[str] = inquirer.checkbox(
        message=tr(lang, "bootstrap_providers_prompt"),
        choices=provider_choices,
        validate=lambda result: len(result) >= 1,
        invalid_message=tr(lang, "bootstrap_providers_validate"),
    ).execute()
    config.enabled_providers = selected_providers

    # ── 3. Features (checkbox) ───────────────────────────────
    console.print()
    console.rule(f"[bold]{tr(lang, 'bootstrap_step_features')}[/bold]")
    feature_choices = [
        {
            "name": f"web       — {tr(lang, 'feature_web_short')}",
            "value": "web",
            "enabled": "web" in config.enabled_features,
        },
        {
            "name": f"server    — {tr(lang, 'feature_server_short')}",
            "value": "server",
            "enabled": "server" in config.enabled_features,
        },
        {
            "name": f"window    — {tr(lang, 'feature_window_short')}",
            "value": "window",
            "enabled": "window" in config.enabled_features,
        },
    ]
    config.enabled_features = inquirer.checkbox(
        message=tr(lang, "bootstrap_features_prompt"),
        choices=feature_choices,
    ).execute()

    # ── 4. Configure each selected provider ──────────────────
    selected_whisper_model: str | None = None
    for provider in selected_providers:
        console.print()
        console.rule(f"[bold cyan]{tr(lang, f'provider_{provider}_name')}[/bold cyan]")
        console.print(f"[dim]{tr(lang, f'provider_{provider}_desc')}[/dim]")
        console.print()

        if provider == "whisper":
            selected_whisper_model = _configure_whisper(config, lang)
        elif provider == "sensevoice":
            _configure_sensevoice(config, lang)
        elif provider == "volcengine":
            _configure_volcengine(config, lang)
        elif provider == "mimo":
            _configure_mimo(config, lang)

    # ── 5. Pick default provider ─────────────────────────────
    console.print()
    console.rule(f"[bold]{tr(lang, 'bootstrap_step_default')}[/bold]")
    if len(selected_providers) == 1:
        config.default_provider = selected_providers[0]
    else:
        default_choices = [
            {"name": f"{p} — {tr(lang, f'provider_{p}_short')}", "value": p}
            for p in selected_providers
        ]
        config.default_provider = inquirer.select(
            message=tr(lang, "bootstrap_default_provider_prompt"),
            choices=default_choices,
            default=config.default_provider if config.default_provider in selected_providers else selected_providers[0],
        ).execute()
    if config.default_provider == "whisper" and selected_whisper_model:
        config.default_model = selected_whisper_model

    # ── Save and show next steps ─────────────────────────────
    config.save(settings)
    _show_next_steps(
        console=console,
        project_root=project_root,
        config=config,
        language=lang,
        save_path=settings.config_path,
    )
    return config


def ensure_bootstrap(*, settings: Settings, allow_prompt: bool = True) -> AppConfig:
    if settings.config_path.exists():
        return AppConfig.load(settings)

    if allow_prompt:
        Console().print(f"[yellow]{tr(DEFAULT_LANGUAGE, 'bootstrap_auto_start')}[/yellow]")
        return run_bootstrap(settings=settings, interactive=True)

    config = AppConfig()
    config.save(settings)
    return config


# ── Provider configuration flows ─────────────────────────────


def _configure_whisper(config: AppConfig, lang: str) -> str:
    whisper_model = inquirer.select(
        message=tr(lang, "bootstrap_whisper_model_prompt"),
        choices=[
            {"name": "tiny    — " + tr(lang, "whisper_model_tiny"), "value": "tiny"},
            {"name": "base    — " + tr(lang, "whisper_model_base"), "value": "base"},
            {"name": "small   — " + tr(lang, "whisper_model_small"), "value": "small"},
            {"name": "medium  — " + tr(lang, "whisper_model_medium"), "value": "medium"},
            {"name": "large   — " + tr(lang, "whisper_model_large"), "value": "large"},
        ],
        default=config.default_model if config.default_model in ("tiny", "base", "small", "medium", "large") else "small",
    ).execute()
    return whisper_model


def _configure_sensevoice(config: AppConfig, lang: str) -> None:
    config.sensevoice.model_dir = inquirer.text(
        message=tr(lang, "bootstrap_sensevoice_dir_prompt"),
        default=config.sensevoice.model_dir,
    ).execute().strip()
    config.sensevoice.language = inquirer.select(
        message=tr(lang, "bootstrap_sensevoice_lang_prompt"),
        choices=[
            {"name": "auto (" + tr(lang, "sensevoice_lang_auto") + ")", "value": "auto"},
            {"name": "zh", "value": "zh"},
            {"name": "en", "value": "en"},
            {"name": "ja", "value": "ja"},
            {"name": "ko", "value": "ko"},
            {"name": "yue (Cantonese)", "value": "yue"},
        ],
        default=config.sensevoice.language,
    ).execute()
    config.sensevoice.use_itn = inquirer.confirm(
        message=tr(lang, "bootstrap_sensevoice_itn_prompt"),
        default=config.sensevoice.use_itn,
    ).execute()


def _configure_volcengine(config: AppConfig, lang: str) -> None:
    config.volcengine.api_key = inquirer.secret(
        message=tr(lang, "bootstrap_volc_api_key_prompt"),
        default=config.volcengine.api_key,
    ).execute().strip()
    config.volcengine.app_key = inquirer.secret(
        message=tr(lang, "bootstrap_volc_app_key_prompt"),
        default=config.volcengine.app_key,
    ).execute().strip()
    config.volcengine.access_key = inquirer.secret(
        message=tr(lang, "bootstrap_volc_access_key_prompt"),
        default=config.volcengine.access_key,
    ).execute().strip()
    config.volcengine.resource_id = inquirer.text(
        message=tr(lang, "bootstrap_volc_resource_prompt"),
        default=config.volcengine.resource_id,
    ).execute().strip()
    config.volcengine.model_name = inquirer.text(
        message=tr(lang, "bootstrap_volc_model_prompt"),
        default=config.volcengine.model_name,
    ).execute().strip()
    config.volcengine.use_itn = inquirer.confirm(
        message=tr(lang, "bootstrap_volc_itn_prompt"),
        default=config.volcengine.use_itn,
    ).execute()


def _configure_mimo(config: AppConfig, lang: str) -> None:
    config.mimo.api_key = inquirer.secret(
        message=tr(lang, "bootstrap_mimo_api_key_prompt"),
        default=config.mimo.api_key,
    ).execute().strip()
    config.mimo.base_url = inquirer.text(
        message=tr(lang, "bootstrap_mimo_base_url_prompt"),
        default=config.mimo.base_url,
    ).execute().strip()
    config.mimo.model_name = inquirer.text(
        message=tr(lang, "bootstrap_mimo_model_prompt"),
        default=config.mimo.model_name,
    ).execute().strip()
    config.mimo.language = inquirer.text(
        message=tr(lang, "bootstrap_mimo_language_prompt"),
        default=config.mimo.language,
    ).execute().strip()


def _show_next_steps(
    *,
    console: Console,
    project_root: Path,
    config: AppConfig,
    language: str,
    save_path: Path,
) -> None:
    extras = collect_required_extras(
        providers=config.enabled_providers,
        features=config.enabled_features,
    )
    command = build_uv_sync_command(workspace=project_root, extras=extras)

    console.print()
    console.rule(f"[bold]{tr(language, 'bootstrap_step_done')}[/bold]")
    console.print(f"[green]{tr(language, 'bootstrap_saved', path=save_path)}[/green]")
    if extras:
        console.print()
        console.print(tr(language, "bootstrap_manual_sync_hint"))
        console.print()
        console.print(f"  [bold]{' '.join(command)}[/bold]")
    console.print()
    console.print(tr(language, "bootstrap_finish"))


def _auto_sync(
    *,
    console: Console,
    project_root: Path,
    config: AppConfig,
    language: str,
) -> None:
    extras = collect_required_extras(
        providers=config.enabled_providers,
        features=config.enabled_features,
    )
    result = sync_selected_environment(workspace=project_root, extras=extras)

    if result.reason == "missing_uv":
        console.print(f"[yellow]{tr(language, 'bootstrap_uv_missing')}[/yellow]")
        console.print(tr(language, "bootstrap_uv_install_hint"))
        console.print(" ".join(result.command))
        return

    if result.ok:
        console.print(f"[green]{tr(language, 'bootstrap_sync_success')}[/green]")
        return

    console.print(f"[red]{tr(language, 'bootstrap_sync_failed')}[/red]")
    if result.stdout.strip():
        console.print(result.stdout.strip())
    if result.stderr.strip():
        console.print(result.stderr.strip())
    console.print(" ".join(result.command))


def _find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current

# Development Guide

## Goal

This repository is moving from a legacy script-style layout to a more maintainable application structure:

- `CLI` as the main entrypoint
- `Window / Web / Server` as features
- transcription providers decoupled from the core pipeline
- `uv` as the standard development workflow

## Layout

```text
src/b2t/
  cli.py            CLI entrypoint
  cli_progress.py   CLI progress output
  bootstrap.py      first-run wizard
  user_config.py    local config loading/saving
  config.py         workspace paths and runtime settings
  inputs.py         input parsing (BV / URL / local file / part)
  models.py         core data models
  database.py       SQLite index
  tasks.py          background task service
  progress.py       task progress and event snapshots
  library.py        video library and transcript versions
  pipeline.py       shared transcription pipeline
  factory.py        downloader/provider assembly
  downloaders/      download implementations
  transcribers/     speech-to-text providers
  templates/        web templates
  web.py            web / API entrypoint
  window_app.py     Tk feature
tests/              automated tests
assets/             logos, screenshots, favicon, materials
archive/            preserved legacy files
```

## Local Setup

```bash
uv sync --extra whisper --extra web
```

Add more providers when needed:

```bash
uv sync --extra sensevoice --extra volcengine --extra mimo
```

Note: always put every extra in the same `uv sync` command — separate calls override each other.

It is usually safer to let Bootstrap manage combined environments:

```bash
uv run bili2text bootstrap
uv run bili2text bootstrap --sync-only
```

## Common Commands

```bash
uv run bili2text --help
uv run bili2text --version
uv run bili2text doctor
uv run bili2text bootstrap
uv run bili2text tx "<bilibili-url>"
uv run bili2text batch "BV1xx411c7XD" "BV1yy411c7XD"
uv run bili2text ui
uv run bili2text win
uv run pytest -q
```

Install the relevant extras before running tests (e.g. `uv sync --extra web --extra volcengine --extra mimo`).

## Config

The default local config file lives at:

```text
./.b2t/config.json
```

Important fields:

- `language`
- `enabled_providers`
- `enabled_features`
- `default_provider`
- `default_model`
- `sensevoice.*`
- `volcengine.*`
- `mimo.*` (`api_key` / `base_url` / `model_name` / `language` / `workers`)

These are environment variables rather than config keys: `B2T_HOME`, `B2T_KEEP_VIDEO`,
`B2T_COOKIE_FILE`, `B2T_COOKIES_FROM_BROWSER`, `B2T_USE_PROXY`.

## Provider Rules

When adding a provider:

- keep download logic out of the provider
- keep the provider focused on speech-to-text
- store config in `AppConfig`
- assemble dependencies in `factory.py`
- run real workflows through `pipeline.py`

## Feature Rules

`Window / Web / Server` should stay as thin shells:

- gather input
- call the shared pipeline
- present results
- avoid duplicating business logic

## Commit Style

This refactor branch prefers small, frequent commits:

- one feature slice per commit
- one fix per commit
- split structural changes from behavior changes whenever possible
- run relevant tests before committing

## Cleanup Rules

- keep the repo root focused
- move historical scripts into `archive/`
- move visual/material assets into `assets/`
- keep `main.py` and `window.py` as compatibility entrypoints for now

## Next Steps

Post-release priorities:

1. add CI (GitHub Actions covering at least ubuntu + windows) instead of relying on manual local testing
2. merge "patch B" from issue #98: send a `Referer` + browser UA with Bilibili requests
3. take over or close PR #94 (SSE + cookie UI); the branch has been idle since 2026-06-22
4. keep cleaning up MiMo / `--keep-video` implementation details (see `ROADMAP.md`)
5. document a more robust Server Mode deployment story

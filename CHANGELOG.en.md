# Changelog

## Unreleased

### Batch Transcription

- added `bili2text batch` for submitting multiple inputs from arguments or a text file
- added multiline batch submission to the web UI and API
- added multiline batch processing to the desktop window

## 2026-04-10 (v0.3.0)

### Version Cleanup

- normalized the current refactor baseline to `0.3.0`

### CLI UX

- command aliases (tx / init / ui / srv / win / diag / lang) are now hidden from help output
- primary commands show their alias in parentheses, e.g. "Transcribe a video or audio file (alias: tx)"
- added InquirerPy dependency, replacing rich.prompt text input

### Bootstrap wizard rewrite

- language and engine selection now use arrow-key navigation instead of typed input
- multi-provider support via checkbox: enable multiple engines, configure each in sequence
- multi-feature support via checkbox: enable `web / server / window` as needed
- only selected providers enter the configuration flow — no more asking for unrelated API keys
- config file gains `enabled_providers` field, backwards-compatible with old configs
- config file gains `enabled_features` field
- whisper model selection shows descriptions (tiny/base/small/medium/large)
- sensevoice language selection uses a descriptive list
- Bootstrap can now generate and run `uv sync --extra ...`
- added `bootstrap --sync-only` for environment resync

### I18n copy refresh

- rewrote all Chinese and English copy to feel more natural and conversational
- doctor status now shows ✓ / ✗ symbols
- added whisper model descriptions, sensevoice language descriptions, and other helper text

### Web UI redesign

- rebuilt index.html and result.html with Tailwind CSS
- clean, modern, responsive layout
- unified form controls, card-style result display

## 2026-04-10

### Refactor Foundation

- established `src/b2t` as the new core directory
- introduced a CLI-first architecture with `transcribe / web / server / window`
- reduced downloads to a single `yt-dlp` path
- added bootstrap onboarding and local config support

### Providers

- added local `whisper`
- added local `sensevoice`
- added Volcengine provider scaffolding and config support

### UX and I18n

- made CLI help Chinese-first
- added short aliases: `tx / init / ui / srv / win / diag / lang`
- added the `language` / `lang` command
- upgraded bootstrap into an interactive wizard with provider explanations
- wired i18n into the web UI and Tk window feature

### Docs and Cleanup

- rewrote the README as a bilingual project front door
- added development docs
- moved legacy scripts and old dependency files into `archive/`
- moved logos and favicon into `assets/`

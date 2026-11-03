# Changelog

## Unreleased

### Engineering & releases

- added GitHub Actions CI: runs the full test suite on ubuntu, windows and macos × Python 3.10 / 3.12, and builds + verifies the wheel / sdist
- added a release packaging workflow: publishing a GitHub Release automatically builds the wheel / sdist and attaches them to that release; it can also be triggered manually for an existing tag
- added `scripts/check_dist.py` to verify that artifacts contain the web templates and no local caches; the sdist now excludes `.uv-cache` / `.venv*` directories
- added a CI status badge to both READMEs

## 2026-11-03 (v0.4.0)

### Behavior changes

- downloads keep audio only by default; pass `--keep-video` or set `B2T_KEEP_VIDEO=1` to keep the video file

### New features

- added `bili2text batch` for submitting multiple inputs from arguments or a text file; the web UI and API accept multiline batches, and the desktop window processes pasted multiline sources one by one
- multi-part Bilibili videos are supported: a URL with `?p=N` downloads and transcribes only that part
- added `--cookies-from-browser` (and `B2T_COOKIES_FROM_BROWSER`) to extract login cookies straight from a browser profile, mitigating Bilibili 412 anti-bot errors
- added support for a login cookie file: `workspace/cookies.txt`, or a path given by `B2T_COOKIE_FILE`
- system proxies are bypassed by default when talking to Bilibili CDNs (proxy nodes often trigger 412 / SSL errors); set `B2T_USE_PROXY=1` to keep using one
- local Whisper engine supports Apple Silicon MPS (GPU) with automatic CPU fallback and a notice
- built-in shell completion (Bash / Zsh / Fish / PowerShell): `bili2text --install-completion`
- completed the web/API surface: persisted tasks with progress/event queries, video library search, categories and tags, transcript version management and activation (see `docs/API.md`)

### MiMo transcription engine

- added Xiaomi MiMo (`mimo-v2.5-asr`) as a cloud engine over an OpenAI-compatible chat completions + `input_audio` protocol
- long audio is split into 60s chunks and transcribed concurrently; added `--workers` and the `mimo.workers` config key (default 4)
- chunks retry with backoff so a single rate-limit response cannot discard a long job
- successful chunks are cached under `.b2t/cache/mimo/` keyed by audio content, so a re-run after an interruption only transcribes what is missing
- documented that `--prompt` has no effect on MiMo

### Fixes

- SenseVoice now auto-detects the official quantized model (`model_quant.onnx`) and reports missing files before loading
- fixed the SenseVoice ITN switch being silently ignored under funasr-onnx 0.4.1 (the kwarg was renamed to `textnorm`; issue #105)
- fixed a crash when indexing local-file transcriptions whose `download` metadata is `None` (issue #100)
- fixed Volcengine transcription calling the wrong API: switched to the flash API with the correct headers and credentials
- fixed GBK-decoded subprocess output breaking ffmpeg / uv on Windows; all calls now use UTF-8
- MiMo: fatal 4xx errors (invalid key, etc.) now fail immediately instead of burning backoff retries
- missing dependencies now show the matching `uv sync --extra ...` hint, and a broken Whisper environment is detected with a rebuild notice

### Docs & maintenance

- updated both READMEs with multi-part, cookie file, proxy switch, MiMo, and shell completion usage
- added `ROADMAP.md` maintainer roadmap
- bumped `yt-dlp` to 2026.7.4

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

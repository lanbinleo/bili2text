<p align="center">
  <img src="assets/light_logo2.png" alt="bili2text logo" width="360" />
</p>

<p align="center">
  <a href="README.md">简体中文</a>
  ·
  <a href="CHANGELOG.en.md">Changelog</a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/lanbinleo/bili2text" alt="GitHub stars" />
  <img src="https://img.shields.io/github/license/lanbinleo/bili2text" alt="License" />
  <img src="https://img.shields.io/github/v/release/lanbinleo/bili2text" alt="Release" />
</p>

# bili2text

**bili2text** is a command-line tool that turns Bilibili videos into text.

Give it a URL or BV id, and it'll download the video, extract the audio, run speech recognition, and hand you a transcript. It supports multiple transcription engines — run everything locally and offline, or connect to a cloud service.

There's also a simple web UI and a desktop window for anyone who'd rather not use the terminal.

![Screenshot](assets/new_v_sc.png)

## Transcription Engines

| Engine | Type | Notes |
| --- | --- | --- |
| **Whisper** | Local model | OpenAI's open-source speech recognition model. Runs offline, general-purpose |
| **SenseVoice** | Local model | ONNX-based local model with strong Chinese recognition |
| **Volcengine** | Cloud API | ByteDance's commercial ASR service, good for batch or service-oriented workloads |
| **MiMo** | Cloud API | Xiaomi MiMo ASR (`mimo-v2.5-asr`) over an OpenAI-compatible API; long audio is chunked and transcribed in parallel |

## Quick Start

### Install

Requires Python 3.10–3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/lanbinleo/bili2text.git
cd bili2text
uv sync
```

This only installs core dependencies. Transcription engines and extra features are installed via extras — for example, to use Whisper and the web UI:

```bash
uv sync --extra whisper --extra web
```

Available extras: `whisper`, `sensevoice`, `volcengine`, `mimo`, `web`, `server`.

> Note: put every extra in the same command (e.g. `uv sync --extra whisper --extra web`). Running separate `uv sync` calls overrides each other — the later one removes packages installed by the earlier one.

#### Prepare the SenseVoice ONNX model

When using SenseVoice, download [`iic/SenseVoiceSmall-onnx`](https://modelscope.cn/models/iic/SenseVoiceSmall-onnx) to a local directory. That ONNX repository does not include the required `chn_jpn_yue_eng_ko_spectok.bpe.model`; download the file with that name from [`iic/SenseVoiceSmall`](https://modelscope.cn/models/iic/SenseVoiceSmall) and place it in the same directory. The final directory must contain at least:

```text
config.yaml
am.mvn
chn_jpn_yue_eng_ko_spectok.bpe.model
model_quant.onnx  # official quantized model; model.onnx is also supported
```

Point the SenseVoice model-directory prompt at this directory. bili2text automatically selects quantized or non-quantized loading from `model_quant.onnx` or `model.onnx`, and reports incomplete directories before loading the runtime.

### Set Up

A setup wizard runs automatically the first time, or you can launch it manually:

```bash
uv run bili2text init
```

The wizard walks you through language, engine, and feature selection, then tells you what install command to run.

### Transcribe

```bash
uv run bili2text tx "https://www.bilibili.com/video/BV1kfDTBXEfu"
```

Local files work too:

```bash
uv run bili2text tx ./my-video.mp4
```

Specify an engine and model:

```bash
uv run bili2text tx "BV1kfDTBXEfu" --provider whisper --model medium
```

Downloads keep audio only by default (transcription never needs the video track, and audio is roughly 25x smaller). Pass `--keep-video` — or set `B2T_KEEP_VIDEO=1` — when you want the video file too:

```bash
uv run bili2text tx "BV1kfDTBXEfu" --keep-video
```

For videos that require login, extract cookies straight from a browser profile (`chrome`/`firefox`/`edge`/`brave`, optionally with a profile name like `firefox:default`):

```bash
uv run bili2text tx "BV1kfDTBXEfu" --cookies-from-browser chrome
```

You can also place a `cookies.txt` in the workspace (or point `B2T_COOKIE_FILE` at one). On top of that, bili2text bypasses system proxies by default when talking to Bilibili CDNs (proxy nodes often trigger 412 / SSL errors); set `B2T_USE_PROXY=1` if you need one.

Submit multiple inputs in one batch:

```bash
uv run bili2text batch "BV1kfDTBXEfu" "https://www.bilibili.com/video/BV1xx411c7XD"
```

Or put one BV, URL, or local file path per line:

```bash
uv run bili2text batch --file sources.txt
```

For multi-part videos, include `?p=N` in the URL to process only that part:

```bash
uv run bili2text tx "https://www.bilibili.com/video/BV1xx411c7XD?p=2"
```

### MiMo cloud transcription

MiMo uses an OpenAI-compatible API, so install the extra and configure a key first:

```bash
uv sync --extra mimo
uv run bili2text bootstrap   # pick mimo, paste the API key
```

Long audio is split into 60-second chunks and transcribed concurrently. `--workers` sets the concurrency (default 4):

```bash
uv run bili2text tx "BV1kfDTBXEfu" --provider mimo --workers 6
```

Pushing concurrency too high gets you rate-limited (HTTP 429). Individual chunks retry with backoff, and successful chunks are cached under `.b2t/cache/mimo/` keyed by audio content — so re-running an interrupted job **only pays for what is missing**.

Note: `--prompt` has no effect on the MiMo engine (the ASR model takes no text instructions; language comes from the `mimo.language` config), and fatal 4xx errors such as an invalid API key fail immediately instead of burning through retries.

## Commands

| Command | Alias | What it does |
| --- | --- | --- |
| `bili2text transcribe` | `tx` | Transcribe a video or audio file |
| `bili2text batch` | - | Batch transcribe multiple inputs |
| `bili2text bootstrap` | `init` | Run the setup wizard |
| `bili2text web` | `ui` | Start the web UI |
| `bili2text server` | `srv` | Start server mode |
| `bili2text window` | `win` | Start the desktop window |
| `bili2text doctor` | `diag` | Check runtime dependencies |
| `bili2text language` | `lang` | Switch the interface language |

```bash
uv run bili2text --help
```

## Shell Completion

bili2text ships with built-in shell completion for Bash, Zsh, Fish, and PowerShell. Install it once, then press Tab to complete subcommands and options:

```bash
bili2text --install-completion
```

Restart your terminal (or reload your shell config as prompted) to activate it.

If the script lands in a non-default location, or you run the CLI through `uv run`, you can also generate and source it manually:

```bash
# Bash
bili2text --show-completion bash > ~/.bili2text-complete.bash
echo 'source ~/.bili2text-complete.bash' >> ~/.bashrc

# Zsh
bili2text --show-completion zsh > ~/.bili2text-complete.zsh
echo 'source ~/.bili2text-complete.zsh' >> ~/.zshrc
```

## Web UI & Server Mode

Start the web interface (opens in your browser):

```bash
uv run bili2text ui
```

Run in server mode (good for Docker or LAN deployment):

```bash
uv run bili2text srv --host 0.0.0.0 --port 8000
```

Besides submitting transcriptions, the web UI offers task progress, a searchable video library, categories and tags, transcript editing, and switching between historical versions.

*Note: the project is not yet optimized for long-running Docker/server deployments — use it locally for now.*

## Development

- [Development Guide](docs/DEVELOPMENT.en.md)
- [Changelog](CHANGELOG.en.md)

## License

MIT License

## Notice

Please respect the copyright laws and platform rules in your region before downloading or processing any content.

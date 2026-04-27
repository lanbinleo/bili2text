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

Available extras: `whisper`, `sensevoice`, `volcengine`, `web`, `server`.

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

Submit multiple inputs in one batch:

```bash
uv run bili2text batch "BV1kfDTBXEfu" "https://www.bilibili.com/video/BV1xx411c7XD"
```

Or put one BV, URL, or local file path per line:

```bash
uv run bili2text batch --file sources.txt
```

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

## Web UI & Server Mode

Start the web interface (opens in your browser):

```bash
uv run bili2text ui
```

Run in server mode (good for Docker or LAN deployment):

```bash
uv run bili2text srv --host 0.0.0.0 --port 8000
```

## Development

- [Development Guide](docs/DEVELOPMENT.en.md)
- [Changelog](CHANGELOG.en.md)

## License

MIT License

## Notice

Please respect the copyright laws and platform rules in your region before downloading or processing any content.

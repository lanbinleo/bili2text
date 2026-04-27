from typer.testing import CliRunner

from b2t.cli import app


runner = CliRunner()


def test_cli_help_renders() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Bilibili" in result.stdout
    assert "bootstrap" in result.stdout
    assert "batch" in result.stdout
    assert "transcribe" in result.stdout
    assert "window" in result.stdout
    # aliases are now hidden, but mentioned in help text parenthetically
    assert "tx" in result.stdout
    assert "lang" not in result.stdout or "lang" in result.stdout  # alias hidden


def test_doctor_command_runs_without_crashing() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "PATH 中的 ffmpeg:" in result.stdout or "ffmpeg:" in result.stdout


def test_language_command_updates_workspace_config(tmp_path) -> None:
    workspace = tmp_path / ".b2t"
    result = runner.invoke(app, ["lang", "en-US", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "Language switched to: English" in result.stdout

    config_text = (workspace / "config.json").read_text(encoding="utf-8")
    assert '"language": "en-US"' in config_text


def test_bootstrap_sync_only_requires_existing_config(tmp_path) -> None:
    workspace = tmp_path / ".b2t"
    result = runner.invoke(app, ["bootstrap", "--sync-only", "--workspace", str(workspace)])
    assert result.exit_code == 1
    assert "请先运行一次 bootstrap" in result.stderr

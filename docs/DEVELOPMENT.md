# 开发文档

## 当前目标

这个仓库正在从旧版脚本式实现迁移到一个更稳定的应用结构：

- `CLI` 作为核心入口
- `Window / Web / Server` 作为 Feature
- `Provider` 与核心逻辑解耦
- 依赖管理与开发流程统一到 `uv`

## 目录结构

```text
src/b2t/
  cli.py            CLI 入口
  cli_progress.py   命令行进度输出
  bootstrap.py      首次启动向导
  user_config.py    本地配置读写
  config.py         工作区目录与运行时设置
  inputs.py         输入解析（BV / 链接 / 本地文件 / 分P）
  models.py         核心数据模型
  database.py       SQLite 索引
  tasks.py          后台任务服务
  progress.py       任务进度与事件快照
  library.py        视频库与文本版本管理
  pipeline.py       核心转写流程
  factory.py        Provider / Downloader 组装
  downloaders/      下载实现
  transcribers/     转写 Provider
  templates/        Web 模板
  web.py            Web / API 入口
  window_app.py     Tk Feature
tests/              自动化测试
assets/             logo、截图、favicon 等素材
archive/            旧版脚本与历史文件
```

## 本地开发

### 环境准备

```bash
uv sync --extra whisper --extra web
```

如需 SenseVoice / 火山引擎 / MiMo：

```bash
uv sync --extra sensevoice --extra volcengine --extra mimo
```

注意：多个 extra 一定要写在同一条 `uv sync` 命令里，分成多条执行会互相覆盖。

更推荐直接用 Bootstrap 管理组合环境：

```bash
uv run bili2text bootstrap
uv run bili2text bootstrap --sync-only
```

### 常用命令

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

跑测试前需要先装齐相关 extras（如 `uv sync --extra web --extra volcengine --extra mimo`）。

## 配置机制

本地配置默认保存在：

```text
./.b2t/config.json
```

当前配置主要包含：

- `language`
- `enabled_providers`
- `enabled_features`
- `default_provider`
- `default_model`
- `sensevoice.*`
- `volcengine.*`
- `mimo.*`（`api_key` / `base_url` / `model_name` / `language` / `workers`）

另外这些是环境变量而不是配置文件项：`B2T_HOME`、`B2T_KEEP_VIDEO`、`B2T_COOKIE_FILE`、
`B2T_COOKIES_FROM_BROWSER`、`B2T_USE_PROXY`。

## Provider 约定

新增 Provider 时，尽量遵守下面的边界：

- 下载逻辑不要塞进 Provider
- Provider 只负责“把音频转成文本”
- 配置项写入 `AppConfig`
- 创建逻辑统一走 `factory.py`
- 真实工作流统一走 `pipeline.py`

## Feature 约定

`Window / Web / Server` 都应该尽量只做壳层：

- 接受输入
- 调用统一 Pipeline
- 输出结果
- 不复制核心业务逻辑

## 提交建议

当前分支偏向小步提交：

- 一个功能点一个 commit
- 一个修复点一个 commit
- 改结构和改行为尽量拆开
- 提交前先跑相关测试

## 清理策略

- 根目录尽量只保留真正的项目入口和元信息
- 历史脚本放进 `archive/`
- 项目素材放进 `assets/`
- 兼容入口暂时保留 `main.py` 和 `window.py`

## CI 与发布

- `.github/workflows/ci.yml`：push 到 main / 打 tag / 提 PR 时，在 ubuntu + windows + macos × Python 3.10 / 3.12 上跑
  `uv run --frozen python -m pytest -q`，并在 ubuntu 上额外构建、校验 wheel / sdist
- `.github/workflows/release.yml`：GitHub Release 发布后自动 `uv build` 并把 wheel / sdist 附加到 Release；
  也可手动补传：`gh workflow run release.yml -f tag=v0.4.0`
- 本地打包校验：`uv build && python scripts/check_dist.py`

## 后续建议

发版后的优先顺序建议为：

1. 合入 issue #98 评论区的「补丁 B」：给 B 站请求加 `Referer` + 浏览器 UA
2. 接手或关闭 PR #94（SSE + Cookie UI），该分支自 2026-06-22 起已停滞
3. 继续清理 MiMo / `--keep-video` 的实现细节（见 `ROADMAP.md`）
4. 为 Server Mode 增加更稳定的部署说明

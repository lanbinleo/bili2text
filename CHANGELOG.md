# 更新日志

## 未发布

### 工程与发布

- 新增 GitHub Actions CI：push / PR 时在 ubuntu、windows、macos × Python 3.10 / 3.12 上跑完整测试，并构建、校验 wheel / sdist
- 新增发版打包 workflow：GitHub Release 发布后自动构建 wheel / sdist 并附加到对应 Release；也可手动指定 tag 触发
- 新增 `scripts/check_dist.py` 校验打包产物包含 Web 模板且不含本地缓存；sdist 排除 `.uv-cache` / `.venv*` 等目录
- 修复 shell 补全测试在 CI 环境下的两处不稳定：GitHub Actions 的 ANSI 样式会拆分别名、macOS runner 上 shell 探测可能失败
- README 增加 CI 状态徽章

## 2026-11-03 (v0.4.0)

### 行为变更

- 下载默认只保留音频文件；需要保留视频时加 `--keep-video` 或设置 `B2T_KEEP_VIDEO=1`

### 新增功能

- 新增 `bili2text batch` 命令，可从命令参数或文本文件批量提交多个输入；Web/API 支持多行输入与批量任务；桌面窗口支持粘贴多行来源并逐条处理
- 支持 B 站多分P视频：链接里带 `?p=N` 时只下载并转写指定分P
- 新增 `--cookies-from-browser`（及 `B2T_COOKIES_FROM_BROWSER` 环境变量），直接从浏览器提取登录态 Cookie，缓解 B 站 412 反爬
- 支持登录态 Cookie 文件：`workspace/cookies.txt`，或用 `B2T_COOKIE_FILE` 指定路径
- 默认绕过系统代理直连 B 站 CDN（代理节点常触发 412 / SSL 错误）；需要代理时设置 `B2T_USE_PROXY=1`
- 本地 Whisper 引擎支持 Apple Silicon MPS（GPU），加载失败自动降级 CPU 并提示
- 内置 shell 补全（Bash / Zsh / Fish / PowerShell）：`bili2text --install-completion`
- Web/API 能力补全：任务持久化与进度/事件查询、视频库检索、分类与标签、文本版本管理与激活（详见 `docs/API.md`）

### MiMo 转写引擎

- 新增小米 MiMo（`mimo-v2.5-asr`）云端引擎，走 OpenAI 兼容的 chat completions + `input_audio` 协议
- 长音频按 60 秒切片并发转写，新增 `--workers` 与配置项 `mimo.workers`（默认 4）
- 切片失败自动退避重试，避免单次限流让整个长任务作废
- 转写成功的切片按音频内容哈希缓存到 `.b2t/cache/mimo/`，中断后重跑只补缺失部分
- `--prompt` 对 MiMo 无效已写入文档

### 修复

- SenseVoice 自动识别官方量化模型（`model_quant.onnx`），模型目录缺文件时在加载前报出缺失清单
- 修复 SenseVoice 的 ITN 开关在 funasr-onnx 0.4.1 下静默失效（参数改名为 `textnorm` 且旧参数被忽略，issue #105）
- 修复本地文件转写时 `download` 元数据为 `None` 导致的入库崩溃（issue #100）
- 修复火山引擎转写调用错误 API 导致的失败：改用 flash API 并修正请求头与鉴权
- 修复 Windows 下子进程输出用 GBK 解码导致的 ffmpeg / uv 报错，统一改为 UTF-8
- MiMo 引擎：无效 Key 等 4xx 致命错误立即失败，不再空耗退避重试
- 依赖缺失时给出对应的 `uv sync --extra ...` 提示；Whisper 环境损坏时可被识别并提示重建

### 文档与维护

- 双语 README 补充分P、Cookie 文件、代理开关、MiMo、Shell 补全等用法
- 新增 `ROADMAP.md` 维护者路线图
- `yt-dlp` 升级至 2026.7.4

## 2026-04-10 (v0.3.0)

### 版本整理

- 将当前重构基线统一规范为 `0.3.0`

### CLI 体验优化

- 命令别名（tx / init / ui / srv / win / diag / lang）改为隐藏，不再重复显示在帮助列表中
- 主命令的帮助文案中以括号标注缩写，如"转写视频或音频（缩写: tx）"
- 添加 InquirerPy 依赖，替换 rich.prompt 的文本输入

### Bootstrap 初始化向导重写

- 语言和引擎选择改为箭头键 + 回车交互，取代手动输入
- 支持 checkbox 多选 provider：可同时启用多个转写引擎，按顺序逐个配置
- 支持 checkbox 多选 feature：可按需启用 `web / server / window`
- 只有选中的 provider 才会进入配置流程，不再无差别询问所有参数
- 配置文件新增 `enabled_providers` 字段，向后兼容旧配置
- 配置文件新增 `enabled_features` 字段
- Whisper 模型选择改为带说明的列表（tiny/base/small/medium/large）
- SenseVoice 语言选择改为带说明的下拉列表
- Bootstrap 可直接生成并执行 `uv sync --extra ...`
- 新增 `bootstrap --sync-only` 用于环境重同步

### i18n 文案优化

- 全面重写中英文文案，更自然、更口语化
- doctor 状态加上 ✓ / ✗ 符号
- 新增 whisper 模型描述、sensevoice 语言描述等辅助文案

### Web UI 重设计

- 使用 Tailwind CSS 重新设计 index.html 和 result.html
- 简约大方的现代风格，响应式布局
- 表单控件样式统一，结果页改为卡片式展示

## 2026-04-10

### 重构基础

- 建立 `src/b2t` 为核心目录，逐步替代旧脚本式结构
- 引入 CLI-first 架构，统一 `transcribe / web / server / window` 入口
- 下载流程统一收敛到 `yt-dlp`
- 新增 Bootstrap 初始化流程与本地配置文件机制

### Provider

- 接入本地 `whisper`
- 接入本地 `sensevoice`
- 增加火山引擎 Provider 骨架与配置项

### 交互与体验

- CLI 帮助信息改为中文优先
- 增加短命令别名：`tx / init / ui / srv / win / diag / lang`
- 增加 `language` / `lang` 命令
- Bootstrap 升级为交互式向导，并补充三类 Provider 说明
- Web UI 与 Tk Window 接入 i18n 文案

### 文档与仓库整理

- README 重新整理为中英双语门面
- 增加开发文档
- 将旧脚本与历史依赖迁移到 `archive/`
- 将 logo / favicon 等素材归档到 `assets/`

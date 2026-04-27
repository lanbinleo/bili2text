# 更新日志

## 未发布

### 批量转写

- 新增 `bili2text batch` 命令，可从命令参数或文本文件批量提交多个输入
- Web/API 支持多行输入与批量任务提交
- 桌面窗口支持在输入框中粘贴多行来源并逐条处理

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

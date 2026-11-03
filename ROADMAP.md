# Roadmap（维护者路线图）

> 状态：随仓库维护。由 2026-11-02 的 PR/issue 大筛查沉淀，2026-11-03 随 v0.4.0 发版更新。
> 文中的引用（issue/PR 编号、提交号）基于发版时的 main（`4b0925b`），动手前先核对。

## 📦 发版

v0.4.0（2026-11-03）已发布，打包与发布链路也已补上：

- 版本号同步到 `pyproject.toml`、`src/b2t/__init__.py`、`uv.lock`
- 双语 CHANGELOG 落日期，并补齐 0.3.0 之后的全部变更
- README / DEVELOPMENT / API 文档同步
- 修掉了一个只在 Windows + PowerShell 下失败的工具测试
- 补上 CI 与发版打包 workflow（见下），v0.4.0 的 wheel / sdist 已补传到 Release

后续发版清单：改三处版本号 → 双语 CHANGELOG 落日期 → `uv lock` → 跑测试 → 打 tag →
`gh release create`。发布后 `release.yml` 会自动构建 wheel / sdist 并附加到 Release，
不用再本地打包上传。

**v0.4.1（2026-11-03）**：修复 #112（非 whisper provider 默认 model 串台），并带上 v0.4.0
之后补的 CI/CD 收尾。

历史注意：GitHub 上仍有一个 2023 年的 `sv-1.0.0` release（旧脚本实现），与当前 0.x
版本线没有继承关系，看版本时以 0.4.0 之后的 tag 为准。

## 🔴 等待外部输入

- [ ] **PR #94（SSE + Cookie UI）**：已 request-changes（缺测试、`event_stream` 多队列
      future 不复用不取消会丢事件、`on_event` 已废弃、需 rebase）。作者自 2026-06-22 起未再
      推送提交，已远超约定的 2~3 周；建议 fork 其分支接手或关闭——方向是对的，修起来量不大
- [ ] **上游 yt-dlp**：B 站 412 challenge 的解答在等上游合入。上游最新 stable 为
      2026.10.26，对应 PR [#16889](https://github.com/yt-dlp/yt-dlp/pull/16889) 仍 open；
      合入后随依赖升级自然解决

## 🟡 已识别、值得排期的小改进

### 已建 issue（2026-11-03 复查遗留问题）

- [ ] **#113 Web / 桌面窗口缺 MiMo 选项**：provider 列表与 CLI 不同步，model 也不随 provider 联动
- [ ] **#114 下载复用**：已下载过的视频默认跳过，新增强制重下开关（#39 关闭时的承诺）
- [ ] **#115 SenseVoice 模型自动下载**：支持填 ModelScope 模型名（#101 建议 2）
- [ ] **#116 文档补齐**：ffmpeg 必需依赖 + Intel Mac 平台限制

### 常规项

- [ ] **吸收 #98 评论区的「补丁 B」**：给 B 站请求加 `Referer: https://www.bilibili.com/` +
      浏览器 UA，几行代码，低成本高收益（v0.4.0 未包含）
- [x] **CI**：已补 `.github/workflows/ci.yml`（ubuntu / windows / macos × Python 3.10 / 3.12
      跑测试，并构建校验 wheel / sdist）与 `.github/workflows/release.yml`（Release 发布后
      自动把打包产物附加到 Release）
- [ ] **#93 的 uv 陷阱**：README 与 DEVELOPMENT 已强调「extras 要写在同一条命令里」（0.4.0），
      还可以考虑在 pyproject 加 `[tool.uv] default-extras = ["web"]`
- [ ] mimo 清理项：`_build_instruction`/`max_tokens` 是死代码（prompt 不进 API），要么实现要么删；
      `work()` 里 `done += 1` 非原子（只影响进度显示）；最后一片 `end` 超时长；
      `factory.py` 用 `startswith("mimo")` 判归属很脆弱；`MimoConfig.language` 默认 `"zh"`
      对英文用户不友好；`doctor` 缺 openai/mimo 检查项；`batch` 没有 `--workers`
- [ ] #97 清理项：`--keep-video` 走 `os.environ` 传参，应迁到 `Settings` 字段；
      默认模式下 metadata 的 `video_path` 实际指向音频文件（语义不符）；
      web/server/window 三个入口没有 keep-video 的 UI 开关
- [ ] **SenseVoice 模型下载体验**：已转为 issue #115 跟踪；#102 已解决官方 ONNX 模型的加载问题，
      剩下「从哪拿模型」仍靠手抄文档

## 🟢 已关闭 / 已修复

- **随 0.4.1 修复**：#112（非 whisper provider 默认 model 串台，volcengine/sensevoice 均受影响）
- **随 0.4.0 修复**：#100（本地文件入库崩溃）、#101（SenseVoice 官方 ONNX 模型）、
  #105（funasr-onnx 0.4.1 ITN 失效）
- **2026-11-03 复查结论**（扫描已关闭 issue 的后续线索）：
  - **#87**（`NoneType` 崩溃）：与 #100 同根因，已在 0.4.0 修复；评论里的 provider/model 问题
    转成 #112 / #113，并已在原 issue 下评论说明
  - **#95**（Intel Mac）：临时抽查 PyTorch 2.15.0，仍无 macOS x86_64 wheel，限制依旧；
    文档/提示缺失转成 #116
  - **#103**（抖音转写）：yt-dlp 抖音提取器仍有多个 open 问题
    （[#17826](https://github.com/yt-dlp/yt-dlp/issues/17826)、
    [#9667](https://github.com/yt-dlp/yt-dlp/issues/9667)、
    [#17831](https://github.com/yt-dlp/yt-dlp/issues/17831)），继续等上游，不重开
  - **#63**：指向旧 you-get / `window.py` 代码路径，当前代码已不存在，无后续
  - **#93**：0.4.0 已在 README / DEVELOPMENT 强调「extras 写同一条命令」，保持关闭
  - **#72 / #73**（Python 3.13/3.14）：属于 whisper / numba 依赖限制，README 已标注
    3.10–3.12，保持关闭

## 🧹 仓库卫生

- [x] ~~`.video_agent/` 未跟踪目录~~（2026-11-02 已确认是 video-agent-kit 插件的探测残留，
      已清理）
- [x] ~~`ROADMAP.md` 只是本地笔记~~（v0.4.0 起纳入仓库维护）
- [x] ~~sdist 会被本地 `.uv-cache` / `.venv*` 污染~~（已加 hatch 排除规则，并用
      `scripts/check_dist.py` 在 CI 里校验产物）
- [ ] 两个大 PR 合并后 uv.lock 已重锁为新格式，后续维护者升级依赖时直接 `uv lock` 即可，
      别再手改

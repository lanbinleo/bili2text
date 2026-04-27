# bili2text API 文档

这份文档面向前端或外部客户端，描述当前可用的后端接口。

## 基本说明

- 默认服务入口: `http://127.0.0.1:8000`
- 推荐启动方式:

```bash
uv run bili2text web
```

- FastAPI 原生文档:
  - Swagger UI: `/docs`
  - OpenAPI JSON: `/openapi.json`

## 设计约束

### 本地文件是真实数据源

转写文本、编辑后的版本、元数据 JSON、下载视频和音频都保存在 `.b2t` 本地目录中。

SQLite 只负责索引和管理状态，不是唯一数据源。

因此：

- 编辑文本会先写新的本地文本文件
- 然后才更新数据库里的当前版本指针
- 读取视频文本时，最终读取的是本地文件内容

## 通用响应习惯

- 列表接口通常返回:

```json
{
  "items": []
}
```

- 单条接口通常直接返回对象
- 失败时返回 FastAPI 默认错误结构:

```json
{
  "detail": "..."
}
```

## 任务 API

### 1. 创建转写任务

`POST /api/tasks/transcribe`

请求体:

```json
{
  "source": "https://www.bilibili.com/video/BV1xx411c7XD",
  "provider": "whisper",
  "model": "small",
  "prompt": ""
}
```

响应:

```json
{
  "task_id": "8f7d...",
  "status": "queued"
}
```

### 2. 批量创建转写任务

`POST /api/tasks/batch`

请求体可以传 `sources` 数组，也可以传 `source_text` 多行文本：

```json
{
  "source_text": "BV1xx411c7XD\nhttps://www.bilibili.com/video/BV1yy411c7XD",
  "provider": "whisper",
  "model": "small",
  "prompt": ""
}
```

响应：

```json
{
  "items": [
    {
      "id": "8f7d...",
      "status": "queued",
      "source_input": "BV1xx411c7XD"
    }
  ],
  "count": 2
}
```

返回的每个任务都可以继续用单任务进度接口轮询。

### 3. 查询任务列表

`GET /api/tasks`

支持查询参数:

- `status`
- `provider`

示例:

`GET /api/tasks?status=completed&provider=whisper`

响应:

```json
{
  "items": [
    {
      "id": "8f7d...",
      "kind": "transcription",
      "status": "completed",
      "source_input": "https://www.bilibili.com/video/BV1xx411c7XD",
      "provider": "whisper",
      "model": "small",
      "workspace_root": ".b2t",
      "progress_percent": 1.0,
      "current_stage": "completed",
      "current_message": "completed",
      "error_message": "",
      "video_id": 1,
      "created_at": "...",
      "started_at": "...",
      "finished_at": "..."
    }
  ],
  "filters": {
    "status": "completed",
    "provider": "whisper"
  }
}
```

### 4. 查询单个任务

`GET /api/tasks/{task_id}`

返回单个任务对象。

### 5. 查询任务当前进度

`GET /api/tasks/{task_id}/progress`

当前返回与任务对象相同的核心状态字段，适合前端轮询。

建议轮询频率:

- 任务运行中: `1000ms`
- 任务完成或失败: 停止轮询

### 6. 查询任务事件流

`GET /api/tasks/{task_id}/events`

响应:

```json
{
  "items": [
    {
      "id": 1,
      "task_id": "8f7d...",
      "status": "running",
      "stage": "downloading",
      "message": "downloading",
      "percent": 0.18,
      "indeterminate": false,
      "detail": {},
      "created_at": "..."
    }
  ]
}
```

这个接口适合前端做任务时间线、调试面板或更细粒度的进度展示。

## 视频库 API

### 1. 查询视频列表

`GET /api/videos`

支持查询参数:

- `query`
- `category_id`
- `tag_id`

示例:

`GET /api/videos?query=demo&category_id=1&tag_id=2`

响应:

```json
{
  "items": [
    {
      "id": 1,
      "source_kind": "bilibili",
      "source_input": "https://www.bilibili.com/video/BV1xx411c7XD",
      "source_url": "https://www.bilibili.com/video/BV1xx411c7XD",
      "source_bv": "BV1xx411c7XD",
      "title": "Demo Title",
      "display_name": "demo",
      "language": "zh",
      "engine": "whisper",
      "model": "small",
      "video_path": ".b2t/downloads/demo.mp4",
      "audio_path": ".b2t/audio/demo.wav",
      "metadata_path": ".b2t/metadata/demo.json",
      "current_transcript_version_id": 3,
      "category_id": 1,
      "category_name": "Research",
      "created_at": "...",
      "updated_at": "...",
      "tags": [
        {
          "id": 2,
          "name": "important",
          "slug": "important"
        }
      ]
    }
  ],
  "filters": {
    "query": "demo",
    "category_id": 1,
    "tag_id": 2
  }
}
```

### 2. 查询单个视频详情

`GET /api/videos/{video_id}`

返回单个视频对象，结构与列表项一致。

### 3. 查询当前文本

`GET /api/videos/{video_id}/transcript`

响应:

```json
{
  "version_id": 3,
  "kind": "edited",
  "file_path": ".b2t/transcripts/edited/demo-1-20260411-120000.txt",
  "is_active": true,
  "text": "..."
}
```

也支持指定版本:

`GET /api/videos/{video_id}/transcript?version_id=2`

### 4. 查询视频元数据

`GET /api/videos/{video_id}/metadata`

返回对应的本地 metadata JSON 内容。

这个接口适合前端详情页显示来源、音频路径、视频路径、模型、语言等附加信息。

## 文本版本 API

### 1. 更新文本并生成新版本

`PUT /api/videos/{video_id}/transcript`

请求体:

```json
{
  "text": "edited text"
}
```

响应:

```json
{
  "video_id": 1,
  "version_id": 4
}
```

说明:

- 这不会覆盖原始文本
- 会写入一个新的 edited 文件
- 然后把新版本设为 active

### 2. 查询版本列表

`GET /api/videos/{video_id}/versions`

响应:

```json
{
  "items": [
    {
      "id": 4,
      "video_id": 1,
      "kind": "edited",
      "file_path": ".b2t/transcripts/edited/...",
      "text_sha256": "...",
      "char_count": 1234,
      "is_active": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### 3. 查询单个版本详情

`GET /api/videos/{video_id}/versions/{version_id}`

返回该版本的文件路径、类型、激活状态和文本内容。

### 4. 激活某个历史版本

`POST /api/videos/{video_id}/versions/{version_id}/activate`

响应:

```json
{
  "video_id": 1,
  "version_id": 2
}
```

## 分类 API

### 1. 查询分类列表

`GET /api/categories`

### 2. 创建分类

`POST /api/categories`

请求体:

```json
{
  "name": "Research"
}
```

### 3. 更新分类

`PUT /api/categories/{category_id}`

请求体:

```json
{
  "name": "Archive"
}
```

### 4. 删除分类

`DELETE /api/categories/{category_id}`

说明:

- 删除分类时，会把关联视频的 `category_id` 清空

### 5. 给视频设置分类

`POST /api/videos/{video_id}/category`

支持两种方式:

1. 直接指定已有分类 id

```json
{
  "category_id": 1
}
```

2. 直接传分类名，后端自动创建

```json
{
  "name": "Research"
}
```

如果要清空分类，可以传:

```json
{
  "category_id": null
}
```

## 标签 API

### 1. 查询标签列表

`GET /api/tags`

### 2. 创建标签

`POST /api/tags`

```json
{
  "name": "important"
}
```

### 3. 更新标签

`PUT /api/tags/{tag_id}`

```json
{
  "name": "featured"
}
```

### 4. 删除标签

`DELETE /api/tags/{tag_id}`

说明:

- 删除标签时，会一并删除 `video_tags` 关联

### 5. 给视频添加标签

`POST /api/videos/{video_id}/tags`

支持两种方式:

```json
{
  "tag_id": 2
}
```

或

```json
{
  "name": "important"
}
```

### 6. 从视频移除标签

`DELETE /api/videos/{video_id}/tags/{tag_id}`

## 前端推荐工作流

### 新建转写任务

1. 调 `POST /api/tasks/transcribe`
2. 保存 `task_id`
3. 轮询 `GET /api/tasks/{task_id}/progress`
4. 当返回 `status=completed` 且 `video_id` 不为空时，跳转到 `/api/videos/{video_id}` 或前端详情页

### 编辑文本

1. 调 `GET /api/videos/{video_id}/transcript`
2. 用户编辑
3. 调 `PUT /api/videos/{video_id}/transcript`
4. 刷新 `GET /api/videos/{video_id}/versions`

### 列表筛选

- 按搜索词: `query`
- 按分类: `category_id`
- 按标签: `tag_id`

## 当前已验证范围

接口已通过项目自动化测试覆盖以下流程：

- 创建后台转写任务
- 查询任务和任务事件
- 视频列表和筛选
- 文本编辑与版本切换
- 分类 CRUD 与绑定
- 标签 CRUD 与绑定
- 视频元数据读取

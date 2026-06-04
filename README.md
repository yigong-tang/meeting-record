# meeting-cli

会议录制处理命令行工具：下载 → 转写 → 对比 → 总结。

## 安装

```bash
# Python 3.12 推荐（3.14 部分依赖不兼容）
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

外部依赖：
```bash
pip install yt-dlp           # 视频下载
winget install ffmpeg         # 音视频处理（重启 shell 生效）
```

可选依赖：
```bash
pip install funasr modelscope torch torchaudio  # SenseVoice 本地转写
```

## 快速开始

完整 pipeline 示例：

```powershell
# 1. 下载 B站 视频（音频 + 视频）
meeting-cli download "https://www.bilibili.com/video/BV1xx" `
    -o my-meeting --keep-video --cookies .meeting-cli/cookies/bilibili.txt

# 2. 转写（whisper small，默认）
meeting-cli transcribe my-meeting/audio.mp3 -b whisper -o my-meeting

# 3. 用另一个模型再转一份（用于对比）
meeting-cli transcribe my-meeting/audio.mp3 -b whisper -m medium -o my-meeting

# 4. 自动对比 → 产出 final-transcript.txt + diff-report.html
meeting-cli compare my-meeting/trans-whisper-small.txt my-meeting/trans-whisper-medium.txt -o my-meeting

# 5. 生成会议纪要（需 DeepSeek API key）
$env:DEEPSEEK_API_KEY = "sk-xxx"
meeting-cli summarize my-meeting/final-transcript.txt -b deepseek -o my-meeting

# 6. 生成字幕（硬字幕烧录）
meeting-cli subtitle my-meeting/final-transcript.txt my-meeting/video.mp4 -o my-meeting
```

---

## 命令参考

### download — 下载视频

```bash
meeting-cli download <url> [OPTIONS]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `-o, --output-dir` | `./meeting-output` | 输出目录 |
| `--audio-only` | 开启 | 只下载音频 |
| `--no-audio-only` | — | 只下载视频（含音轨） |
| `--keep-video` | 关闭 | 同时保留视频文件（产出 .mp3 + .mp4） |
| `--cookies` | — | Netscape 格式 cookies 文件（B站登录态） |
| `--dry-run` | — | 只打印 yt-dlp 命令 |

产出：

| 参数组合 | 产出 |
|----------|------|
| 默认 | `audio.mp3` |
| `--keep-video` | `audio.mp3` + `video.mp4` |
| `--no-audio-only` | `video.mp4` |

### transcribe — 音频转写

```bash
meeting-cli transcribe <file> [OPTIONS]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `-b, --backend` | 必须指定 | 转写后端（可多次指定） |
| `-o, --output-dir` | `./meeting-output` | 输出目录 |
| `-l, --language` | `zh` | 音频语言 |
| `-m, --model-size` | `small` | whisper 模型：tiny/small/medium/large-v3 |

产出：`trans-{backend}-{model_size}.txt`（带时间戳文本）

可用后端：

| 后端 | 类型 | 状态 |
|------|------|------|
| `whisper` | 本地 faster-whisper | ✅ |
| `sensevoice` | 本地 FunASR | ⚠️ Windows 适配中 |
| `aliyun` | 阿里云 ASR API | ⏳ stub |
| `iflytek` | 科大讯飞 ASR API | ⏳ stub |

### compare — 对比两份转写

```bash
meeting-cli compare <file_a> <file_b> [OPTIONS]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `-o, --output-dir` | `./meeting-output` | 输出目录 |
| `-i, --interactive` | 关闭 | 手动逐段审核（默认：算法自动决策） |
| `--use-llm` | 关闭 | LLM 辅助判断差异（待实现） |
| `--llm-backend` | `openai` | LLM 后端 |
| `-a, --audio` | — | 音频文件（`--interactive` 时可用 P 回听） |

产出：`final-transcript.txt` + `diff-report.html`

三种模式：

| 命令 | 行为 |
|------|------|
| `compare a.txt b.txt` | 自动算法决策，直接出报告 |
| `compare a.txt b.txt --interactive` | 逐段手动审核 |
| `compare a.txt b.txt --use-llm` | LLM 辅助精判（接口预留） |

### summarize — 生成会议纪要

```bash
meeting-cli summarize <file> [OPTIONS]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `-b, --backend` | `openai` | LLM 后端 |
| `-o, --output-dir` | `./meeting-output` | 输出目录 |

产出：`merged-transcript.txt`（去时间戳） + `summary.md`（LLM 可用时）

LLM 失效时自动回退，仅输出合并文本。后端自动识别提供商 URL：

| 后端 | 环境变量 | 模型 |
|------|----------|------|
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-v4-flash |
| `openai` | `OPENAI_API_KEY` | deepseek-v4-flash |
| `dashscope` | `DASHSCOPE_API_KEY` | deepseek-v4-flash |

通过 `{PREFIX}_MODEL` 和 `{PREFIX}_BASE_URL` 覆盖默认值。

### subtitle — 生成字幕

```bash
meeting-cli subtitle <transcript> <video> [OPTIONS]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `-o, --output-dir` | `./meeting-output` | 输出目录 |
| `--soft` | 关闭 | 软字幕（秒出，播放器可开关） |
| `--translate` | 关闭 | 翻译字幕（未实现） |

默认硬字幕（烧录到画面），`--soft` 为独立字幕轨。

---

## 性能参考

**测试条件：** 21 分钟 B站 中文对话音频，Intel i7-10710U (6C12T)，16GB RAM，Windows 10

| 模型 | 大小 | 速度 | 段数 | 备注 |
|------|------|------|------|------|
| whisper-tiny | 237MB | ~1x 实时 | ~130 | 可用但准确度较低 |
| whisper-small | 952MB | ~0.4x 实时 | ~158 | 日常使用推荐 |
| whisper-medium | 1.5GB | ~0.15x 实时 | ~171 | 最高准确度 |

> 速度 = 音频时长 / 转写耗时。0.4x 实时 = 21 分钟音频约 8 分钟转完。

---

## 目录结构

```
meeting-record/
├── meeting_cli/           # 源代码
│   ├── commands/           # CLI 命令 (download/transcribe/compare/summarize/subtitle)
│   ├── backends/           # 后端插件 (whisper/sensevoice/summarizers)
│   ├── diff/               # 差异对比引擎 (文本对齐 + 报告生成)
│   └── utils/              # 工具 (配置/模型管理)
├── tests/                  # 测试 (86 个)
├── .meeting-cli/           # 本地数据 (模型/cookies，gitignore)
│   ├── cookies/             # B站 cookies
│   └── models/              # 本地模型 (faster-whisper / SenseVoiceSmall)
├── docs/superpowers/       # 设计文档 & 计划
└── pyproject.toml
```

## 待办

- [ ] SenseVoice Windows 适配 (#2026-06-04-sensevoice-windows)
- [ ] ffmpeg PATH 自动检测 (#2026-06-04-ffmpeg-path)
- [ ] 后端架构拆分（每个 API 独立文件）(#2026-06-04-backend-refactor)
- [ ] LLM compare 辅助判断实现
- [ ] subtitle --translate 翻译功能
- [ ] 阿里云 / 科大讯飞 ASR 后端实现

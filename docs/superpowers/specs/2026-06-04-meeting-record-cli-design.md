# 会议记录 CLI 设计文档

## 概述

一个命令行工具，用于处理会议视频：下载 → 转写 → 对比 → 总结，附带字幕生成探索功能。

## 设计决策

| 维度 | 决策 |
|------|------|
| 语言 | 中文为主 |
| 使用模式 | 离线批处理 |
| CLI 风格 | 子命令式（`meeting-cli <verb> [args]`） |
| 管道模式 | 线性手动管道（方案 A），每步独立运行 |
| 后端机制 | 可插拔，统一注册表，新增后端无需改 CLI 层 |
| 配置管理 | 环境变量 |
| 视频来源 | B站为主，通过 yt-dlp |
| 转写时间戳 | 强制要求，作为 diff 对齐和字幕生成的基础 |

## 命令接口

```
meeting-cli download <url>          下载音频/视频
    --output-dir <dir>              工作目录（默认 ./meeting-output）
    --audio-only                    只下载音频（默认）
    --keep-video                    保留视频文件

meeting-cli transcribe <file>       转写音频
    --backend <name>                选择后端（可多次指定）
    --output-dir <dir>              工作目录
    --language zh                   语言提示

meeting-cli compare <a> <b>         对比两份转写
    --output-dir <dir>
    --use-llm                       启用LLM辅助精判差异
    --llm-backend <name>            LLM后端选择

meeting-cli summarize <file>        生成会议纪要
    --backend <name>                选择LLM后端
    --output-dir <dir>

meeting-cli subtitle <trans> <video> 生成字幕（探索性功能）
    --translate                     同时生成翻译字幕
    --target-lang en                翻译目标语言
```

### 规范约定

- 每个子命令独立运行，输出文件自动写入工作目录
- 工作目录下文件有固定命名规则：`trans-{backend}.txt`、`diff-report.html`、`final-transcript.txt`、`summary.md`
- 后续命令不指定输入文件时，自动从工作目录发现

## 项目结构

```
meeting-record/
├── meeting_cli/
│   ├── __init__.py
│   ├── main.py                 # CLI 入口
│   ├── commands/
│   │   ├── download.py         # yt-dlp 封装
│   │   ├── transcribe.py       # 转写调度
│   │   ├── compare.py          # 差异对比 + 交互确认
│   │   ├── summarize.py        # LLM 总结
│   │   └── subtitle.py         # 字幕生成（探索）
│   ├── backends/
│   │   ├── __init__.py         # 后端注册表（自动扫描）
│   │   ├── transcriber.py      # BaseTranscriber 抽象
│   │   ├── whisper_local.py    # faster-whisper 本地
│   │   ├── sensevoice_local.py # SenseVoice 本地
│   │   ├── aliyun_asr.py       # 阿里云语音识别 API
│   │   ├── iflytek_asr.py      # 科大讯飞语音识别 API
│   │   ├── summarizer.py       # BaseSummarizer 抽象
│   │   └── openai_compat.py    # OpenAI 兼容接口
│   ├── diff/
│   │   ├── engine.py           # 时间戳对齐 + 差异检测
│   │   └── reporter.py         # HTML/Markdown 报告生成
│   └── utils/
│       ├── config.py           # 环境变量读取
│       └── audio.py            # 音频格式处理
├── tests/
├── pyproject.toml
└── README.md
```

## 核心模块设计

### 1. download — yt-dlp 封装

- 通过 subprocess 调用 yt-dlp 命令行工具（需用户自行安装 yt-dlp）
- 默认 `--audio-only`，提取音频为 mp3
- `--keep-video` 时保留原始视频文件
- 默认携带浏览器 User-Agent 和 Referer header（B站等平台需要）
- `--cookies` 指定 Netscape 格式的 cookie 文件路径（B站登录态）
- 下载前检查 ffmpeg 是否可用，不可用时给出警告提示（音视频流可能无法自动合并）
- 产出：`<output-dir>/<title>.mp3`，可选 `<output-dir>/<title>.mp4`

### 2. transcribe — 转写调度

- 后端通过名称注册，`--backend whisper --backend aliyun` 并行或串行调用
- 后端接口约定：

```python
class BaseTranscriber:
    name: str  # 注册名，对应 --backend 参数值
    def transcribe(self, audio_path: str) -> list[Segment]:
        ...
        # 每个 Segment: {start: float, end: float, text: str}
```

- 产出：`<output-dir>/trans-{backend}.txt`，格式：

```
[00:00:00.000 -> 00:00:03.500] 大家好，欢迎参加今天的会议
[00:00:03.500 -> 00:00:08.200] 今天我们讨论Q2的预算分配
```

### 3. compare — 差异对比与人工确认

#### 3.1 文本对齐

- **主轴：时间戳对齐**。相同时间段直接配对
- **辅轴：语义相似度**。处理时间戳轻微偏移的情况（偏移 < 2s 且文本相似度 > 阈值则视为同一段）
- 时间戳无对应且语义不匹配 → 标记为孤立段落

#### 3.2 差异分级

| 级别 | 条件 | 处理 |
|------|------|------|
| 🟢 一致 | 编辑距离 < 10% 或 LLM判定同义 | 自动通过，不展示 |
| 🟡 小差异 | 编辑距离 10-30% | 终端展示，需确认 |
| 🔴 大差异 | 编辑距离 > 30% | 终端高亮展示，需确认 |

#### 3.3 LLM 辅助精判（`--use-llm`，可选）

- 对 🔴 差异段落，调用 LLM 判断是否实质同义
- LLM 后端同样走 `backends/` 注册机制
- 不启用时纯算法判断

#### 3.4 终端交互

```
【段落 3】[00:03:15 -> 00:03:22]  🔴大差异
A (whisper):   "我们决定将Q2预算上调15%"
B (aliyun):    "我们决定将Q2预算上调50%"
差异: 15% vs 50%

选择: [A] [B] [手动编辑] [回听音频] [跳过]
```

- "回听音频"：自动调用 ffplay 播放对应时间段的音频（`ffplay -ss -t -nodisp -autoexit`）；若 ffplay 不可用则回退为打印时间戳提示
- "手动编辑"：用户输入修正文本

#### 3.5 产出

- `final-transcript.txt`：人工确认后的完整转写，保留时间戳
- `diff-report.html`：完整对比报告，包含所有差异段落的原始内容、用户选择、审计痕迹

### 4. summarize — 会议总结

- 后端接口：

```python
class BaseSummarizer:
    name: str
    def summarize(self, transcript: str) -> str:
        ...
        # 返回 Markdown 格式的会议纪要
```

- 后端实现：
  - `openai_compat`：OpenAI 兼容接口，覆盖通义千问、DeepSeek 等
  - `ollama_local`：本地 Ollama 运行的开源模型
- 产出 `summary.md`，包含：
  - 基本信息（日期、时长、参会人）
  - 主要议题
  - 关键决策
  - 待办事项
  - 简短摘要

### 5. subtitle — 字幕生成（探索性）

- 依赖转写后端返回的时间戳
- 从带时间戳的转写直接生成 SRT 文件
- 翻译通过 LLM 后端实现，时间轴不变
- 使用 ffmpeg 将字幕嵌入视频
- 探索优先级：先验证各后端时间戳能力，再实现完整流程

## 环境变量

| 变量 | 用途 |
|------|------|
| `ALIYUN_ASR_KEY` | 阿里云语音识别 |
| `IFLYTEK_ASR_KEY` | 科大讯飞语音识别 |
| `OPENAI_API_KEY` | OpenAI API（Whisper + LLM） |
| `DEEPSEEK_API_KEY` | DeepSeek LLM |
| `DASHSCOPE_API_KEY` | 通义千问 LLM |
| `OLLAMA_HOST` | 本地 Ollama 地址 |

## 数据流总览

```
① download  → audio.mp3 (+ 可选 video.mp4)
② transcribe → trans-whisper.txt, trans-aliyun.txt, ...
③ compare   → 终端逐段确认 → final-transcript.txt + diff-report.html
④ summarize → summary.md
⑤ subtitle  → subtitle.srt (+ subtitle-en.srt) → ffmpeg嵌入 → 带字幕视频
```

## 测试策略

- 单元测试：各后端接口 mock、diff 对齐算法、报告生成
- 集成测试：录制短会议音频，走完整管道
- 不依赖真实 API 的测试可离线运行

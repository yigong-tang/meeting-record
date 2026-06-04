# 后端架构重构

**状态：** 待处理

**问题：**
当前后端耦合过紧：

- `openai_compat.py` 承担了 openai / deepseek / dashscope 三个提供商，通过 `backend_name` 参数区分
- 三个便捷子类（`DeepSeekSummarizer`, `DashScopeSummarizer`）也挤在同一个文件
- 三个 stub 后端（`sensevoice_local.py`, `aliyun_asr.py`, `iflytek_asr.py`）是空壳
- `config.py` 的 `get_backend_config` 用前缀拼接方式读环境变量，逻辑太通用，不够清晰

**目标架构：**

```
backends/
├── __init__.py          # 注册表（不改）
├── transcriber.py       # BaseTranscriber + Segment（不改）
├── summarizer.py        # BaseSummarizer（不改）
│
├── transcribe/          # 转写后端，每个 API 一个文件
│   ├── whisper.py       # faster-whisper 本地
│   ├── sensevoice.py    # SenseVoice 本地
│   ├── aliyun.py        # 阿里云 ASR
│   └── iflytek.py       # 科大讯飞 ASR
│
└── summarize/           # 总结后端，每个 API 一个文件
    ├── openai.py        # OpenAI
    ├── deepseek.py      # DeepSeek
    ├── dashscope.py     # 阿里云通义千问
    └── ollama.py        # 本地 Ollama
```

每个后端文件自包含：接口实现 + 环境变量读取 + 提示词模板。不再共用一个 `get_backend_config` 做"万能"配置解析。

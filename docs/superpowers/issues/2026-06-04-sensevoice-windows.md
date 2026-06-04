# SenseVoice Windows 兼容性问题

**状态：** 待解决

**问题：**
FunASR 在 Windows 上使用 `remote_code` 加载 `model.py` 时，无法处理 Windows 绝对路径（反斜杠转义问题）。模型文件（893MB）已成功下载到 `.meeting-cli/models/SenseVoiceSmall/`，模型骨架 `model.py` 也已从 GitHub 拉取，但加载时反复报错。

**已尝试：**
1. 绝对路径 `remote_code="C:\...\model.py"` → "No module named 'C:\\...'"
2. 将 models 目录加入 sys.path，用 `remote_code="model"` → model.py 内部依赖 `utils` 模块缺失
3. 下载 utils/frontend.py → 尚未完成完整测试（每次加载 893MB 耗尽资源）

**需要的文件（已就位）：**
- `model.pt` (893MB) ✅ — 模型权重
- `model.py` (33KB) ✅ — 模型结构
- `utils/frontend.py` ✅ — 模型依赖

**可能解决方向：**
- 用 ONNX 运行时替代 FunASR（更轻量）
- 设置 `MODELSCOPE_CACHE` 环境变量让 FunASR 直接用 modelscope 的缓存路径
- 在 Linux/WSL 下运行

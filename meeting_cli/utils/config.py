"""Environment variable configuration reader."""

import os
from pathlib import Path
from typing import Optional


def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """Read an environment variable by name.

    Args:
        key_name: The env var name (e.g. 'ALIYUN_ASR_KEY').
        default: Fallback value if the env var is not set.

    Returns:
        The env var value, or default/None.
    """
    return os.environ.get(key_name, default)


def get_backend_config(backend_name: str) -> dict:
    """Read all environment variables for a named backend.

    Backend names normalize to uppercase with underscores:
        'openai'    → OPENAI_API_KEY, OPENAI_BASE_URL
        'aliyun'    → ALIYUN_ASR_KEY
        'iflytek'   → IFLYTEK_ASR_KEY
        'deepseek'  → DEEPSEEK_API_KEY
        'dashscope' → DASHSCOPE_API_KEY
        'ollama'    → OLLAMA_HOST

    Args:
        backend_name: Lowercase backend identifier.

    Returns:
        Dict with keys 'api_key' and 'base_url'.
    """
    prefix = backend_name.upper()
    result = {"api_key": None, "base_url": None}

    # API key: try {PREFIX}_API_KEY, then {PREFIX}_ASR_KEY
    for key_suffix in ["API_KEY", "ASR_KEY"]:
        val = os.environ.get(f"{prefix}_{key_suffix}")
        if val:
            result["api_key"] = val
            break

    # Base URL
    result["base_url"] = os.environ.get(f"{prefix}_BASE_URL")

    return result


def get_model_dir() -> Path:
    """Return the local model storage directory.

    Controlled by MEETING_CLI_MODEL_DIR env var.
    Default: ~/.config/meeting-cli/models

    Returns:
        Path to the model directory (created if it doesn't exist).
    """
    default = Path.home() / ".config" / "meeting-cli" / "models"
    path = Path(os.environ.get("MEETING_CLI_MODEL_DIR", str(default)))
    path.mkdir(parents=True, exist_ok=True)
    return path

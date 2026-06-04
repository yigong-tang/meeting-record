"""Tests for config module."""

from pathlib import Path
from meeting_cli.utils.config import get_api_key, get_backend_config, get_model_dir


class TestGetApiKey:
    def test_returns_env_var_if_set(self, monkeypatch):
        monkeypatch.setenv("ALIYUN_ASR_KEY", "sk-test-123")
        assert get_api_key("ALIYUN_ASR_KEY") == "sk-test-123"

    def test_returns_none_if_not_set(self, monkeypatch):
        monkeypatch.delenv("ALIYUN_ASR_KEY", raising=False)
        assert get_api_key("ALIYUN_ASR_KEY") is None

    def test_returns_default_if_not_set(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert get_api_key("OPENAI_API_KEY", default="fallback") == "fallback"


class TestGetBackendConfig:
    def test_extracts_backend_specific_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example.com/v1")
        config = get_backend_config("openai")
        assert config == {
            "api_key": "sk-openai",
            "base_url": "https://proxy.example.com/v1",
        }

    def test_handles_missing_vars(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        config = get_backend_config("openai")
        assert config["api_key"] is None
        assert config["base_url"] is None


class TestGetModelDir:
    def test_returns_default_path(self, monkeypatch):
        monkeypatch.delenv("MEETING_CLI_MODEL_DIR", raising=False)
        path = get_model_dir()
        assert path.name == "models"
        assert ".config" in str(path)

    def test_uses_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MEETING_CLI_MODEL_DIR", str(tmp_path / "my-models"))
        path = get_model_dir()
        assert path.name == "my-models"

    def test_creates_dir_if_missing(self, monkeypatch, tmp_path):
        new_dir = tmp_path / "new-models"
        monkeypatch.setenv("MEETING_CLI_MODEL_DIR", str(new_dir))
        path = get_model_dir()
        assert path.exists()
        assert path.is_dir()

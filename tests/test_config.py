"""Tests for config module."""

import os
from meeting_cli.utils.config import get_api_key, get_backend_config


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

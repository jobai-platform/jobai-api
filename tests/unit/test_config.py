import importlib

import pytest


def test_settings_reads_ollama_base_url_from_env(monkeypatch):
    """GIVEN OLLAMA_BASE_URL is set in the environment
    WHEN Settings is instantiated
    THEN the value is read from the environment, not hardcoded
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-ollama:9999")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_BASE_URL == "http://custom-ollama:9999"


def test_settings_reads_ollama_llm_model_from_env(monkeypatch):
    """GIVEN OLLAMA_LLM_MODEL is set in the environment
    WHEN Settings is instantiated
    THEN the correct model name is used
    """
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "mistral-nemo:12b")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_LLM_MODEL == "mistral-nemo:12b"


def test_settings_ollama_timeout_defaults_to_120(monkeypatch):
    """GIVEN OLLAMA_TIMEOUT is NOT set in the environment
    WHEN Settings is instantiated
    THEN the default of 120.0 seconds is used
    """
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_TIMEOUT == 120.0


def test_settings_embedding_provider_defaults_to_ollama(monkeypatch):
    """GIVEN EMBEDDING_PROVIDER is NOT set in the environment
    WHEN Settings is instantiated
    THEN the default 'ollama' is used
    """
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.EMBEDDING_PROVIDER == "ollama"

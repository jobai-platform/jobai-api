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


def test_settings_cors_allow_origins_defaults_to_frontend_origin(monkeypatch):
    """GIVEN CORS_ALLOW_ORIGINS is NOT set
    WHEN Settings is instantiated
    THEN the frontend origin is used as the strict CORS allowlist
    """
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.jobai.test")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.CORS_ALLOW_ORIGINS == ["https://app.jobai.test"]


def test_settings_cors_allow_origins_reads_comma_separated_env(monkeypatch):
    """GIVEN CORS_ALLOW_ORIGINS contains multiple origins
    WHEN Settings is instantiated
    THEN whitespace is stripped and empty values are ignored
    """
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://app.jobai.test, http://localhost:3000, ",
    )

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.CORS_ALLOW_ORIGINS == [
        "https://app.jobai.test",
        "http://localhost:3000",
    ]


def test_settings_cors_allow_origins_rejects_wildcard_with_credentials(monkeypatch):
    """GIVEN CORS_ALLOW_ORIGINS contains a wildcard
    WHEN Settings is loaded
    THEN configuration fails because credentials require strict origins
    """
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")

    with pytest.raises(ValueError, match="CORS_ALLOW_ORIGINS cannot contain"):
        import app.core.config as config_module
        importlib.reload(config_module)

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


def test_settings_reads_app_env_from_env(monkeypatch):
    """GIVEN APP_ENV is set in the environment
    WHEN Settings is instantiated
    THEN the configured runtime environment is used
    """
    monkeypatch.setenv("APP_ENV", "preview")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.APP_ENV == "preview"


def test_settings_rejects_invalid_app_env(monkeypatch):
    """GIVEN APP_ENV is invalid
    WHEN Settings is loaded
    THEN configuration fails fast
    """
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValueError, match="APP_ENV must be one of"):
        import app.core.config as config_module
        importlib.reload(config_module)


def test_settings_reads_ollama_llm_model_from_env(monkeypatch):
    """GIVEN OLLAMA_LLM_MODEL is set in the environment
    WHEN Settings is instantiated
    THEN the correct model name is used
    """
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "mistral-nemo:12b")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_LLM_MODEL == "mistral-nemo:12b"


def test_settings_reads_public_api_base_url_from_env(monkeypatch):
    """GIVEN PUBLIC_API_BASE_URL is set in the environment
    WHEN Settings is instantiated
    THEN the public backend URL is read from the environment
    """
    monkeypatch.setenv("PUBLIC_API_BASE_URL", "https://api.preview.test")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.PUBLIC_API_BASE_URL == "https://api.preview.test"


def test_settings_reads_linkedin_redirect_uri_from_env(monkeypatch):
    """GIVEN LINKEDIN_REDIRECT_URI is set in the environment
    WHEN Settings is instantiated
    THEN the explicit LinkedIn callback URL is used
    """
    monkeypatch.setenv(
        "LINKEDIN_REDIRECT_URI",
        "https://api.preview.test/api/v1/auth/linkedin/callback",
    )

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.LINKEDIN_REDIRECT_URI == (
        "https://api.preview.test/api/v1/auth/linkedin/callback"
    )


def test_settings_ollama_timeout_defaults_to_120(monkeypatch):
    """GIVEN OLLAMA_TIMEOUT is NOT set in the environment
    WHEN Settings is instantiated
    THEN the default of 120.0 seconds is used
    """
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_TIMEOUT == 120.0


def test_settings_database_url_sync_defaults_to_database_url(monkeypatch):
    """GIVEN DATABASE_URL_SYNC is NOT set
    WHEN Settings is instantiated
    THEN the sync URL defaults to DATABASE_URL
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    monkeypatch.delenv("DATABASE_URL_SYNC", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.DATABASE_URL_SYNC == "postgresql+asyncpg://user:pass@host/db"


def test_settings_database_url_sync_reads_env(monkeypatch):
    """GIVEN DATABASE_URL_SYNC is set
    WHEN Settings is instantiated
    THEN the explicit sync URL is used
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://user:pass@host-sync/db")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.DATABASE_URL_SYNC == "postgresql://user:pass@host-sync/db"


@pytest.mark.parametrize(
    ("ssl_value", "expected_ssl_value"),
    [
        ("true", "require"),
        ("false", "disable"),
    ],
)
def test_settings_normalizes_boolean_asyncpg_ssl_values(
    monkeypatch,
    ssl_value,
    expected_ssl_value,
):
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://user:pass@host/db?ssl={ssl_value}",
    )

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.DATABASE_URL == (
        f"postgresql+asyncpg://user:pass@host/db?ssl={expected_ssl_value}"
    )


def test_settings_preserves_valid_asyncpg_ssl_value(monkeypatch):
    database_url = "postgresql+asyncpg://user:pass@host/db?ssl=require&application_name=jobai"
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.DATABASE_URL == database_url


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


def test_settings_cors_allow_origins_adds_localhost_alias_for_local_dev(monkeypatch):
    """GIVEN the default frontend origin is localhost
    WHEN Settings is instantiated
    THEN the CORS allowlist also accepts the 127.0.0.1 alias used by some browsers
    """
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.CORS_ALLOW_ORIGINS == [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


def test_settings_cors_allow_origin_regex_defaults_to_none(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.CORS_ALLOW_ORIGIN_REGEX is None


def test_settings_cors_allow_origin_regex_reads_env(monkeypatch):
    origin_regex = (
        r"^https://jobai-frontend-[a-z0-9]+-"
        r"rpsantosvix-gmailcoms-projects\.vercel\.app$"
    )
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", origin_regex)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.CORS_ALLOW_ORIGIN_REGEX == origin_regex


def test_settings_cors_allow_origin_regex_rejects_invalid_regex(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "[invalid")

    with pytest.raises(ValueError, match="CORS_ALLOW_ORIGIN_REGEX must be a valid regex"):
        import app.core.config as config_module
        importlib.reload(config_module)


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

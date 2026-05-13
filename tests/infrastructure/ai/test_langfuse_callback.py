from app.infrastructure.ai.langfuse_callback import get_langfuse_callback


def test_get_langfuse_callback_returns_none_when_not_configured(monkeypatch):
    """GIVEN LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not set
    WHEN get_langfuse_callback is called
    THEN None is returned (no crash)
    """
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    result = get_langfuse_callback()

    assert result is None

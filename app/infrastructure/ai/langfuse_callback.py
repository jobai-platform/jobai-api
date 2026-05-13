import logging
import os

logger = logging.getLogger(__name__)


def get_langfuse_callback():
    """Returns a Langfuse callback handler if configured, else None.

    Requires LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST to be set.
    Returns None silently if not configured so the pipeline works without Langfuse.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not public_key or not secret_key:
        logger.debug("Langfuse not configured — tracing disabled")
        return None

    try:
        from langfuse.callback import CallbackHandler  # type: ignore[import-untyped]

        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("Langfuse tracing enabled at %s", host)
        return handler
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse callback: %s", exc)
        return None

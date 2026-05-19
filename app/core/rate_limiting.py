from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _candidate_rate_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    return f"analysis:{user_id}" if user_id else get_remote_address(request)


limiter = Limiter(key_func=_candidate_rate_key)

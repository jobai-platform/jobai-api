from app.application.auth.ports import OAuthGateway
from app.domain.users.value_objects import LinkedInProfile


class FakeOAuthGateway(OAuthGateway):
    """
    In-memory fake for OAuthGateway.
    Pass a LinkedInProfile to simulate success, or an Exception to simulate failure.
    """

    def __init__(
        self,
        profile: LinkedInProfile | None = None,
        raise_on_exchange: Exception | None = None,
    ) -> None:
        self._profile = profile
        self._raise = raise_on_exchange
        self.exchange_calls: list[tuple[str, str]] = []

    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInProfile:
        self.exchange_calls.append((code, redirect_uri))
        if self._raise is not None:
            raise self._raise
        if self._profile is None:
            raise RuntimeError("FakeOAuthGateway: no profile configured")
        return self._profile

    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"https://www.linkedin.com/oauth/v2/authorization?redirect_uri={redirect_uri}&state={state}"

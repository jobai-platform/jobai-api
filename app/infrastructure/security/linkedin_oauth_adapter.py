import logging

import httpx

from app.application.auth.ports import OAuthGateway
from app.domain.users.value_objects import LinkedInProfile

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
_AUTH_BASE_URL = "https://www.linkedin.com/oauth/v2/authorization"
_SCOPES = "openid profile email"


class LinkedInOAuthAdapter(OAuthGateway):
    """
    Concrete implementation of OAuthGateway for LinkedIn.

    Flow (LinkedIn OpenID Connect):
      1. POST /oauth/v2/accessToken  → access_token
      2. GET  /v2/userinfo           → sub (linkedin_id), email, given_name, family_name, picture

    Never stores tokens — only uses them transiently to build a LinkedInProfile.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInProfile:
        """
        Exchange an authorization code for a LinkedIn user profile.
        Raises RuntimeError on any HTTP or parsing failure (caught + re-raised as
        UnauthorizedError by LinkedInOAuthUseCase).
        """
        logger.info("LinkedInOAuthAdapter.exchange_code: starting token exchange redirect_uri=%r", redirect_uri)
        access_token = await self._fetch_access_token(code, redirect_uri)
        profile = await self._fetch_user_profile(access_token)
        logger.info(
            "LinkedInOAuthAdapter.exchange_code: profile fetched linkedin_id=%r email=%r name=%r %r",
            profile.linkedin_id,
            profile.email,
            profile.first_name,
            profile.last_name,
        )
        return profile

    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        url = (
            f"{_AUTH_BASE_URL}"
            f"?response_type=code"
            f"&client_id={self._client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&scope={_SCOPES.replace(' ', '%20')}"
        )
        logger.debug("LinkedInOAuthAdapter.build_authorization_url: url=%r", url)
        return url

    async def _fetch_access_token(self, code: str, redirect_uri: str) -> str:
        logger.debug("LinkedInOAuthAdapter._fetch_access_token: POST %s", _TOKEN_URL)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        logger.debug("LinkedInOAuthAdapter._fetch_access_token: response status=%d", response.status_code)

        if response.status_code != 200:
            logger.warning(
                "LinkedInOAuthAdapter._fetch_access_token: failed status=%d body=%r",
                response.status_code,
                response.text[:300],
            )
            raise RuntimeError(
                f"LinkedIn token exchange failed (HTTP {response.status_code})",
            )

        data = response.json()
        access_token: str | None = data.get("access_token")
        if not access_token:
            logger.error("LinkedInOAuthAdapter._fetch_access_token: response OK but access_token missing body=%r", data)
            raise RuntimeError("LinkedIn token response missing access_token")

        logger.info("LinkedInOAuthAdapter._fetch_access_token: access_token obtained (expires_in=%s)", data.get("expires_in"))
        return access_token

    async def _fetch_user_profile(self, access_token: str) -> LinkedInProfile:
        logger.debug("LinkedInOAuthAdapter._fetch_user_profile: GET %s", _USERINFO_URL)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        logger.debug("LinkedInOAuthAdapter._fetch_user_profile: response status=%d", response.status_code)

        if response.status_code != 200:
            logger.warning(
                "LinkedInOAuthAdapter._fetch_user_profile: failed status=%d body=%r",
                response.status_code,
                response.text[:300],
            )
            raise RuntimeError(
                f"LinkedIn userinfo request failed (HTTP {response.status_code})",
            )

        data = response.json()
        linkedin_id: str | None = data.get("sub")
        email: str | None = data.get("email")

        if not linkedin_id or not email:
            logger.error(
                "LinkedInOAuthAdapter._fetch_user_profile: missing required fields sub=%r email=%r raw=%r",
                linkedin_id,
                email,
                data,
            )
            raise RuntimeError(
                f"LinkedIn userinfo missing required fields: sub={linkedin_id!r} email={email!r}",
            )

        logger.debug(
            "LinkedInOAuthAdapter._fetch_user_profile: sub=%r email=%r given_name=%r family_name=%r has_picture=%s",
            linkedin_id,
            email,
            data.get("given_name"),
            data.get("family_name"),
            bool(data.get("picture")),
        )

        return LinkedInProfile(
            linkedin_id=linkedin_id,
            email=email,
            first_name=data.get("given_name", ""),
            last_name=data.get("family_name", ""),
            avatar_url=data.get("picture"),
        )

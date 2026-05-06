import logging

from app.application.auth.ports import OAuthGateway, TokenService
from app.application.auth.use_cases import TokenPair
from app.application.billing.use_cases import AssignFreemiumOnSignupUseCase
from app.application.users.ports import UserRepository
from app.domain.common.exceptions import UnauthorizedError
from app.domain.users.entities import User
from app.domain.users.value_objects import Email, LinkedInProfile

logger = logging.getLogger(__name__)


class LinkedInOAuthUseCase:
    """
    Orchestrates the LinkedIn OAuth2 login flow.

    Three branches:
      1. Existing user found by linkedin_id → issue JWT (returning user).
      2. Existing user found by email → attach linkedin_id + avatar, issue JWT (merge).
      3. No user found → create new User, assign freemium, issue JWT (signup).
    """

    def __init__(
        self,
        oauth_gateway: OAuthGateway,
        user_repo: UserRepository,
        token_service: TokenService,
        freemium_use_case: AssignFreemiumOnSignupUseCase,
    ) -> None:
        self._gateway = oauth_gateway
        self._user_repo = user_repo
        self._token_service = token_service
        self._freemium = freemium_use_case

    async def execute(self, *, code: str, redirect_uri: str) -> TokenPair:
        """
        Exchange the LinkedIn authorization code for a JWT TokenPair.
        Raises UnauthorizedError on any LinkedIn API failure.
        """
        logger.info("LinkedInOAuth.execute: starting code exchange redirect_uri=%r", redirect_uri)
        try:
            profile: LinkedInProfile = await self._gateway.exchange_code(code, redirect_uri)
        except Exception as exc:
            logger.warning("LinkedInOAuth.execute: code exchange failed — %s", exc)
            raise UnauthorizedError(
                code="linkedin_auth_failed",
                details="LinkedIn authentication failed. Please try again.",
            ) from exc

        logger.info(
            "LinkedInOAuth.execute: code exchanged successfully linkedin_id=%r email=%r",
            profile.linkedin_id,
            profile.email,
        )
        user = await self._resolve_user(profile)
        tokens = self._issue_tokens(user)
        logger.info("LinkedInOAuth.execute: JWT issued for user_id=%s", user.id)
        return tokens

    async def _resolve_user(self, profile: LinkedInProfile) -> User:
        logger.debug("LinkedInOAuth._resolve_user: looking up linkedin_id=%r", profile.linkedin_id)

        # Branch 1 — returning user (already connected LinkedIn)
        existing = await self._user_repo.find_by_linkedin_id(profile.linkedin_id)
        if existing:
            logger.info(
                "LinkedInOAuth._resolve_user: [branch=returning] user_id=%s email=%r",
                existing.id,
                str(existing.email),
            )
            return existing

        # Branch 2 — email collision: user registered with password
        email_vo = Email.from_raw(profile.email)
        logger.debug("LinkedInOAuth._resolve_user: no match by linkedin_id, checking email=%r", profile.email)
        by_email = await self._user_repo.get_by_email(email_vo)
        if by_email:
            logger.info(
                "LinkedInOAuth._resolve_user: [branch=merge] attaching linkedin_id=%r to existing user_id=%s",
                profile.linkedin_id,
                by_email.id,
            )
            by_email.attach_linkedin(profile)
            await self._user_repo.update(by_email.id, by_email)
            logger.info("LinkedInOAuth._resolve_user: [branch=merge] update persisted for user_id=%s", by_email.id)
            return by_email

        # Branch 3 — brand-new user
        logger.info(
            "LinkedInOAuth._resolve_user: [branch=signup] no existing user found, creating new user email=%r",
            profile.email,
        )
        new_user = User(
            id=None,
            email=email_vo,
            first_name=profile.first_name,
            last_name=profile.last_name,
            linkedin_id=profile.linkedin_id,
            avatar_url=profile.avatar_url,
            hashed_password=None,
        )
        created = await self._user_repo.create(new_user)
        logger.info("LinkedInOAuth._resolve_user: [branch=signup] user created user_id=%s", created.id)

        logger.info("LinkedInOAuth._resolve_user: [branch=signup] assigning freemium to user_id=%s", created.id)
        await self._freemium.execute(user_id=created.id)
        logger.info("LinkedInOAuth._resolve_user: [branch=signup] freemium assigned to user_id=%s", created.id)

        return created

    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        logger.debug("LinkedInOAuth.build_authorization_url: redirect_uri=%r state=%r", redirect_uri, state)
        return self._gateway.build_authorization_url(redirect_uri=redirect_uri, state=state)

    def _issue_tokens(self, user: User) -> TokenPair:
        logger.debug("LinkedInOAuth._issue_tokens: generating JWT for user_id=%s role=%r", user.id, user.role)
        subject = str(user.id)
        extra = {"role": user.role, "email": str(user.email)}
        return TokenPair(
            access_token=self._token_service.create_access_token(subject, extra),
            refresh_token=self._token_service.create_refresh_token(subject, extra),
        )

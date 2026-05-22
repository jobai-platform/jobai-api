import logging
from uuid import UUID

from app.application.auth.ports import LinkedInOAuthGateway
from app.application.users.ports import UserRepository
from app.domain.common.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.domain.users.value_objects import LinkedInProfile

logger = logging.getLogger(__name__)


class LinkedInOAuthUseCase:
    """
    LinkedIn OAuth2 helpers for account management:
    - Build the authorization URL (CSRF state support)
    - Link a LinkedIn identity to an already-authenticated Candidate

    For the OAuth callback (code → JWT), see LinkedInCallbackUseCase.
    """

    def __init__(
        self,
        oauth_gateway: LinkedInOAuthGateway,
        user_repo: UserRepository,
    ) -> None:
        self._gateway = oauth_gateway
        self._user_repo = user_repo

    def build_authorization_url(self, redirect_uri: str, state: str) -> str:
        logger.debug(
            "LinkedInOAuth.build_authorization_url: redirect_uri=%r state=%r",
            redirect_uri,
            state,
        )
        return self._gateway.build_authorization_url(redirect_uri=redirect_uri, state=state)

    async def link_to_existing_user(
        self, *, current_user_id: UUID, code: str, redirect_uri: str
    ) -> None:
        """
        Attach a LinkedIn identity to an already-authenticated Candidate.
        Does NOT create a new user — attaches linkedin_id + avatar_url to the existing account.

        Raises:
          UnauthorizedError  — if the LinkedIn code exchange fails
          NotFoundError      — if current_user_id doesn't exist
          ConflictError      — if the linkedin_id is already attached to a different account
        """
        logger.info(
            "LinkedInOAuth.link_to_existing_user: user_id=%s starting code exchange",
            current_user_id,
        )
        try:
            profile: LinkedInProfile = await self._gateway.exchange_code(code, redirect_uri)
        except Exception as exc:
            logger.warning("LinkedInOAuth.link_to_existing_user: code exchange failed — %s", exc)
            raise UnauthorizedError(
                code="linkedin_auth_failed",
                details="LinkedIn authentication failed. Please try again.",
            ) from exc

        logger.info(
            "LinkedInOAuth.link_to_existing_user: code exchanged linkedin_id=%r email=%r",
            profile.linkedin_id,
            profile.email,
        )

        taken = await self._user_repo.find_by_linkedin_id(profile.linkedin_id)
        if taken and taken.id != current_user_id:
            logger.warning(
                "LinkedInOAuth.link_to_existing_user: linkedin_id=%r already attached to user_id=%s",
                profile.linkedin_id,
                taken.id,
            )
            raise ConflictError(
                code="linkedin_already_linked",
                details="This LinkedIn account is already linked to another user.",
            )

        user = await self._user_repo.get_by_id(current_user_id)
        if not user:
            raise NotFoundError(code="user_not_found", details="User not found.")

        user.attach_linkedin(profile)
        await self._user_repo.update(user.id, user)
        logger.info(
            "LinkedInOAuth.link_to_existing_user: linkedin_id=%r linked to user_id=%s",
            profile.linkedin_id,
            user.id,
        )

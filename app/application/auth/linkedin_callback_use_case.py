import logging
from uuid import uuid4

from app.application.auth.ports import LinkedInOAuthGateway, TokenService
from app.application.auth.use_cases import LinkedInAuthResult, TokenPair
from app.application.billing.use_cases import AssignFreemiumOnSignupUseCase
from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.application.users.ports import UserRepository
from app.domain.common.exceptions import ConflictError, UnauthorizedError
from app.domain.users.candidate_profile import CandidateProfile
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, LinkedInProfile

logger = logging.getLogger(__name__)


class LinkedInCallbackUseCase:
    """
    Exchanges a LinkedIn OAuth2 code for a JWT pair.

    Three branches:
      1. Existing Candidate found by linkedin_id → issue JWT (returning user).
      2. Email already registered without LinkedIn (D9) → ConflictError.
      3. No match → create new Candidate, assign freemium, issue JWT (signup).
    """

    def __init__(
        self,
        oauth_gateway: LinkedInOAuthGateway,
        user_repo: UserRepository,
        token_service: TokenService,
        freemium_use_case: AssignFreemiumOnSignupUseCase,
        profile_repo: CandidateProfileRepository | None = None,
    ) -> None:
        self._gateway = oauth_gateway
        self._user_repo = user_repo
        self._token_service = token_service
        self._freemium = freemium_use_case
        self._profile_repo = profile_repo

    async def execute(self, *, code: str, redirect_uri: str) -> LinkedInAuthResult:
        """
        Exchange the LinkedIn authorization code for a LinkedInAuthResult.

        Raises UnauthorizedError on LinkedIn API failure.
        Raises ConflictError(code="email_already_used") when email is already registered.
        """
        logger.info("LinkedInCallback.execute: starting code exchange redirect_uri=%r", redirect_uri)  # noqa: E501
        try:
            profile: LinkedInProfile = await self._gateway.exchange_code(code, redirect_uri)
        except Exception as exc:
            logger.warning("LinkedInCallback.execute: code exchange failed — %s", exc)
            raise UnauthorizedError(
                code="linkedin_auth_failed",
                details="LinkedIn authentication failed. Please try again.",
            ) from exc

        logger.info(
            "LinkedInCallback.execute: code exchanged linkedin_id=%r email=%r",
            profile.linkedin_id,
            profile.email,
        )
        user, is_new_user = await self._resolve_user(profile)
        tokens = self._issue_tokens(user)
        logger.info(
            "LinkedInCallback.execute: JWT issued user_id=%s is_new_user=%s", user.id, is_new_user
        )
        return LinkedInAuthResult(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            is_new_user=is_new_user,
        )

    async def _resolve_user(self, profile: LinkedInProfile) -> tuple[Candidate, bool]:
        """Return (candidate, is_new_user). Raises ConflictError if email is taken."""
        logger.debug("LinkedInCallback._resolve_user: linkedin_id=%r", profile.linkedin_id)

        # Branch 1 — returning Candidate (linkedin_id already attached)
        existing = await self._user_repo.find_by_linkedin_id(profile.linkedin_id)
        if existing:
            logger.info(
                "LinkedInCallback._resolve_user: [returning] user_id=%s", existing.id
            )
            return existing, False

        # Branch 2 — email already registered without LinkedIn (D9)
        email_vo = Email.from_raw(profile.email)
        email_taken = await self._user_repo.get_by_email(email_vo)
        if email_taken:
            logger.warning(
                "LinkedInCallback._resolve_user: [conflict] email=%r already registered",
                profile.email,
            )
            raise ConflictError(
                code="email_already_used",
                details=(
                    "An account with this email already exists. Please log in with your password."
                ),
            )

        # Branch 3 — new signup via LinkedIn
        logger.info("LinkedInCallback._resolve_user: [signup] email=%r", profile.email)
        new_user = Candidate(
            id=uuid4(),
            email=email_vo,
            first_name=profile.first_name,
            last_name=profile.last_name,
            linkedin_id=profile.linkedin_id,
            avatar_url=profile.avatar_url,
            hashed_password=None,
        )
        created = await self._user_repo.create(new_user)
        logger.info("LinkedInCallback._resolve_user: [signup] created user_id=%s", created.id)

        if self._profile_repo is not None:
            await self._profile_repo.save(CandidateProfile(user_id=created.id))

        await self._freemium.execute(user_id=created.id)
        logger.info("LinkedInCallback._resolve_user: [signup] freemium assigned user_id=%s", created.id)  # noqa: E501

        return created, True

    def _issue_tokens(self, user: Candidate) -> TokenPair:
        subject = str(user.id)
        extra = {"role": user.role, "email": str(user.email)}
        return TokenPair(
            access_token=self._token_service.create_access_token(subject, extra),
            refresh_token=self._token_service.create_refresh_token(subject, extra),
        )

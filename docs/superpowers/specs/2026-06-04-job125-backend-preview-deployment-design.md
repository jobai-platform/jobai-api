# JOB-125 — Backend Preview Deployment Per Feature Branch

**Status:** Implemented for review
**Ticket:** JOB-125
**Owner:** Forge
**Related specs:**

- `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md`
- `docs/superpowers/specs/2026-06-03-job124-backend-preview-branch-lifecycle-design.md`
- `docs/superpowers/specs/2026-06-03-preview-security-policy-design.md`

## Goal

Deploy one backend preview runtime per feature branch and connect it to the matching Neon preview branch created by
JOB-124.

Target chain:

```text
feature branch push
  -> create/reuse Neon preview branch
  -> run Alembic migrations on that branch
  -> deploy FastAPI backend preview to Vercel
  -> smoke test /health
  -> publish preview URL in GitHub summary and PR comment
```

## Implementation Decision

Use **Vercel FastAPI backend previews** for the POC.

Rationale:

- The frontend already runs on Vercel, so the review environment can stay on one preview platform.
- It avoids adding a VPS solely for backend feature previews.
- GitHub Actions can still control Neon branch creation, migrations, smoke tests, and PR comments.

Required platform prerequisite:

- A Vercel backend project, e.g. `jobai-api`, imported from `jobai-platform/jobai-api`.
- FastAPI preset with Poetry install command `bash scripts/vercel-install.sh`.
- Vercel project variables and token available to GitHub Actions.

## Runtime Model

Each feature branch maps to the same deterministic slug used by the Neon preview branch, for example:

```text
preview-feature-job-125-07-cicd-deploy-backend-preview-<hash>
```

Generated runtime values:

| Value | Example |
|---|---|
| Vercel backend project | `jobai-api` |
| Backend URL | Vercel deployment URL returned by `vercel deploy` |
| Neon branch | `preview-feature-job-125-<hash>` |
| Frontend origin | Exact Vercel frontend preview URL or configured fallback |

## Workflow Changes

`.github/workflows/backend-preview.yml` now performs:

1. Checkout and dependency installation.
2. Fast test suite against CI Postgres.
3. Neon preview branch creation/reuse through `app.infrastructure.ci.neon_branch_lifecycle`.
4. Alembic migrations against the generated Neon `DATABASE_URL`.
5. Preview metadata generation through `app.infrastructure.ci.backend_preview_deployment`.
6. Vercel deployment using `npx vercel@latest deploy` and branch-specific runtime/build env vars.
7. Public `/health` smoke test against the returned Vercel deployment URL.
8. GitHub Actions summary.
9. PR comment create/update when an open PR exists for the branch.

## Preview Environment Variables

The remote `.env.preview` is generated per branch and contains only preview values:

```text
APP_ENV=preview
DATABASE_URL=<matching Neon preview branch URL>
DATABASE_URL_SYNC=<matching Neon preview branch URL>
SECRET_KEY=<PREVIEW_JWT_SECRET>
JWT_SECRET=<PREVIEW_JWT_SECRET>
PUBLIC_API_BASE_URL=https://<slug>.preview-api.sovrum.dev
FRONTEND_ORIGIN=<exact preview frontend origin>
CORS_ALLOW_ORIGINS=<exact preview frontend origin>
LINKEDIN_CLIENT_ID=dummy
LINKEDIN_CLIENT_SECRET=dummy
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

The workflow does not read production `.env` or `ENV_PROD`.

## GitHub Configuration

Required secrets:

```text
NEON_API_KEY
PREVIEW_JWT_SECRET
VERCEL_TOKEN
```

Required variables:

```text
NEON_PROJECT_ID
NEON_PARENT_BRANCH
VERCEL_BACKEND_PROJECT_ID
VERCEL_ORG_ID
```

Optional variables:

```text
PREVIEW_FRONTEND_ORIGIN
VERCEL_BACKEND_PUBLIC_API_BASE_URL
```

Default values:

- `PREVIEW_FRONTEND_ORIGIN`: `https://<slug>.preview.sovrum.dev`
- `VERCEL_BACKEND_PUBLIC_API_BASE_URL`: `https://jobai-api.vercel.app`

## Security Constraints

- Preview deploys derive their database URL only from the Neon branch lifecycle step.
- Production secrets and production `.env` are not referenced.
- `APP_ENV=preview` is explicit.
- OAuth is disabled with dummy LinkedIn values for this POC path.
- Langfuse tracing is disabled by default in preview.
- CORS uses one exact origin, never `*`.

## Acceptance Criteria Mapping

| Ticket criterion | Implementation |
|---|---|
| Multiple feature backend previews can coexist | One Vercel preview deployment per feature branch push |
| Each backend preview connects only to matching Neon branch | Vercel deploy receives the `DATABASE_URL` exported by JOB-124 helper |
| `/health` passes for deployed preview | `curl -fsS --retry ... <vercel-preview-url>/health` after Vercel deploy |
| Preview deploy does not read production `.env` or credentials | Workflow injects preview env values directly into Vercel deploy; no production env import |
| Build/pull backend image by commit SHA | Not applicable to Vercel FastAPI preview runtime |
| Publish preview URL | Summary plus PR comment marker `<!-- jobai-backend-preview -->` |

## Known Follow-Ups

- JOB-126 must provide the real Vercel preview frontend origin so `CORS_ALLOW_ORIGINS` matches the deployed frontend.
- JOB-128 must delete the matching Neon branch and optionally remove stale Vercel preview deployments.
- JOB-126 must coordinate the frontend preview origin with the backend preview CORS allowlist.

## Vercel Backend Preview POC Note

The local and Docker backend stack remains Python 3.13 through `pyproject.toml` and the `Dockerfile`.

Vercel currently builds Python functions with Python 3.12.13 in the preview import flow. For the Vercel-only POC,
`scripts/vercel-install.sh` temporarily relaxes the Poetry Python constraint during the Vercel build process, refreshes the
lock file in the ephemeral Vercel checkout, then runs `poetry install`. This does not change the committed Python
constraint and should be removed once Vercel supports Python 3.13 for this project or the backend preview hosting decision
changes.

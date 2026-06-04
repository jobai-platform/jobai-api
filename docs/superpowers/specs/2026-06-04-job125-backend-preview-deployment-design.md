# JOB-125 — Backend Preview Deployment Per Feature Branch

**Status:** Implemented and verified
**Ticket:** JOB-125
**Owner:** Forge
**Verified commit:** `037cc37`
**Verified workflow run:** `26968887279`
**Related docs:**

- `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md`
- `docs/superpowers/specs/2026-06-03-job124-backend-preview-branch-lifecycle-design.md`
- `docs/superpowers/specs/2026-06-03-preview-security-policy-design.md`
- `docs/adr/adr-0004-vercel-backend-preview-per-feature-branch.md`
- `docs/deployment/backend-preview-vercel-runbook.md`

## Goal

Deploy one backend preview runtime per feature branch and connect it to the matching Neon preview branch created by
JOB-124.

Target chain:

```text
feature branch push
  -> create/reuse Neon preview branch
  -> run Alembic migrations on that branch
  -> deploy FastAPI backend preview to Vercel
  -> smoke test /health through Vercel protected preview access
  -> publish preview URL in GitHub summary and PR comment
```

## Final Implementation Decision

Use **Vercel FastAPI backend previews** for the POC.

This replaced the initial VPS/SSH deployment assumption because no backend VPS is currently available. The local backend
and infra stack remains Docker-based; Vercel is only the remote branch-preview runtime.

Rationale:

- The frontend already runs on Vercel, so the review environment can stay on one preview platform.
- It avoids adding and operating a VPS solely for backend feature previews.
- GitHub Actions still controls Neon branch creation, migrations, Vercel deployment, smoke testing, and PR comments.
- One feature branch push can produce one backend preview connected to the matching Neon branch.

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

`.github/workflows/backend-preview.yml` performs:

1. Checkout and dependency installation with Python 3.13 + Poetry in GitHub Actions.
2. Fast test suite against CI PostgreSQL.
3. Required configuration validation for Neon and Vercel.
4. Neon preview branch creation/reuse through `app.infrastructure.ci.neon_branch_lifecycle`.
5. Alembic migrations against the generated Neon `DATABASE_URL`.
6. Preview metadata generation through `app.infrastructure.ci.backend_preview_deployment`.
7. Vercel deployment using `npx vercel@latest deploy` and branch-specific runtime/build env vars.
8. Protected `/health` smoke test using `npx vercel@latest curl /health --deployment <deployment-url>`.
9. GitHub Actions summary.
10. PR comment create/update when an open PR exists for the branch.

## Vercel Build Decisions

### Python Version

The committed repository remains Python 3.13:

```toml
python = "^3.13"
```

Vercel currently builds this project with Python 3.12. `scripts/vercel-install.sh` temporarily relaxes the constraint only
inside Vercel's ephemeral build checkout:

```toml
python = ">=3.12,<4.0"
```

This does not change the local Docker stack or the committed `pyproject.toml` constraint.

### Minimal Runtime Install

Full Poetry runtime installation exceeded the Vercel Python function bundle limit. The Vercel install script now installs
only the packages needed to start the FastAPI preview runtime and respond to `/health`.

Heavy adapters are lazy-loaded from `app.core.dependency` so importing `app.main` does not require large optional packages:

- LinkedIn scraper / JobSpy
- S3 / aioboto3
- Ollama / LangGraph / LangChain
- Timescale vector-store adapter

This keeps the preview deploy under Vercel's bundle limit while preserving local Docker behavior.

### Protected Preview Smoke Test

Direct `curl` returns `401` against protected Vercel previews. The workflow uses Vercel CLI's protected-deployment helper:

```bash
npx vercel@latest curl /health --deployment "${deployment_url}"
```

The smoke step exports `VERCEL_PROJECT_ID` because Vercel CLI requires it when `VERCEL_ORG_ID` is present. The command reads
`VERCEL_TOKEN` from the environment instead of accepting a `--token` flag.

## Preview Environment Variables

The Vercel deployment receives preview values directly from GitHub Actions:

```text
APP_ENV=preview
DATABASE_URL=<matching Neon preview branch URL>
DATABASE_URL_SYNC=<matching Neon preview branch URL>
SECRET_KEY=<PREVIEW_JWT_SECRET>
JWT_SECRET=<PREVIEW_JWT_SECRET>
PUBLIC_API_BASE_URL=<configured public API base URL>
FRONTEND_ORIGIN=<exact preview frontend origin or fallback>
CORS_ALLOW_ORIGINS=<exact preview frontend origin or fallback>
LINKEDIN_CLIENT_ID=dummy
LINKEDIN_CLIENT_SECRET=dummy
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

The workflow does not read production `.env` or `ENV_PROD`.

## GitHub Configuration

Required sensitive secrets:

```text
NEON_API_KEY
PREVIEW_JWT_SECRET
VERCEL_TOKEN
```

Required IDs/configuration can be stored as GitHub variables or repository secrets:

```text
NEON_PROJECT_ID
NEON_PARENT_BRANCH
PREVIEW_BACKEND_BASE_DOMAIN
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

## Local-Only Files

These files are intentionally ignored by Git:

```text
.vercel/
env.vercel.preview
.env.vercel.preview
```

`env.vercel.preview` / `.env.vercel.preview` are POC helpers for importing preview env values into Vercel. They must not be
committed. After the POC, move secrets to the selected secret-management process and rotate any manually shared values.

## Security Constraints

- Preview deploys derive their database URL only from the Neon branch lifecycle step.
- Generated Neon `DATABASE_URL` values are masked in GitHub logs.
- Production secrets and production `.env` are not referenced.
- `APP_ENV=preview` is explicit.
- OAuth is disabled with dummy LinkedIn values for this POC path.
- Langfuse tracing is disabled by default in preview.
- CORS uses one exact origin, never `*`.
- Vercel Preview Authentication remains enabled; CI uses `vercel curl` for smoke tests.

## Acceptance Criteria Mapping

| Ticket criterion | Implementation |
|---|---|
| Multiple feature backend previews can coexist | One Vercel preview deployment per feature branch push |
| Each backend preview connects only to matching Neon branch | Vercel deploy receives the `DATABASE_URL` exported by the Neon branch lifecycle helper |
| `/health` passes for deployed preview | `npx vercel@latest curl /health --deployment <vercel-preview-url>` after Vercel deploy |
| Preview deploy does not read production `.env` or credentials | Workflow injects preview env values directly into Vercel deploy; no production env import |
| Build/pull backend image by commit SHA | Not applicable after Vercel preview decision; Docker remains local/CI stack |
| Publish preview URL | Summary plus PR comment marker `<!-- jobai-backend-preview -->` |

## Verification

Final verified state on 2026-06-04:

- Branch: `feature/job-125-07-cicd-deploy-backend-preview-per-feature-branch`
- Commit: `037cc37`
- Backend Preview run: `26968887279`
- Result: passed

Verified workflow steps:

- Fast tests passed.
- Neon preview branch create/reuse passed.
- Alembic migrations passed on the Neon preview branch.
- Vercel deploy passed.
- Protected `/health` smoke test passed through `vercel curl`.
- GitHub summary and PR comment passed.

## Known Follow-Ups

- JOB-126 must provide the real Vercel preview frontend origin so `CORS_ALLOW_ORIGINS` matches the deployed frontend.
- JOB-128 must delete the matching Neon branch and optionally remove stale Vercel preview deployments.
- Revisit the Vercel Python 3.13 compatibility workaround when Vercel supports Python 3.13 for this project.
- Decide whether AI/scraping/S3 endpoints need full preview runtime support or separate preview targets.

# ADR-0004 — Vercel Backend Preview Per Feature Branch

**Status:** Accepted
**Date:** 2026-06-04
**Owner:** Forge
**Related ticket:** JOB-125
**Related PR:** GitHub PR #44

## Context

JOB-125 needs a backend preview environment for every feature branch so reviewers can test frontend and backend changes before merging.

The initial backend-preview direction assumed a VPS deployment path using SSH and Docker. During implementation, the team confirmed that no VPS is available for backend previews. The frontend already runs on Vercel, so using Vercel for backend previews keeps feature-review environments on one platform while the local development stack remains Docker-based.

The repository still targets Python 3.13 locally and in CI, but Vercel Python builds currently run with Python 3.12 in this project. The backend also contains large optional runtime areas for AI, scraping, S3, and local tooling; deploying all dependencies to Vercel exceeded the Python function bundle limit.

## Decision

Use Vercel for the backend preview POC while keeping Docker as the local backend/infra stack.

The preview workflow now:

1. Creates or reuses the deterministic Neon preview branch for the feature branch.
2. Runs Alembic migrations against that Neon preview branch.
3. Deploys the FastAPI backend to the Vercel backend project.
4. Injects branch-specific preview environment variables directly into Vercel at deploy time.
5. Smoke-tests `/health` using `vercel curl`, because preview deployments are protected by Vercel Authentication.
6. Publishes the preview URL in GitHub Actions summary and in the PR comment.

## Key Decisions

### Vercel Instead Of VPS

Decision: deploy backend previews to Vercel instead of SSH/VPS.

Rationale:

- No backend VPS is available for the POC.
- Frontend previews already run on Vercel.
- GitHub Actions can still orchestrate Neon, migrations, deployment, smoke tests, and PR comments.
- This enables front/back preview testing per feature branch with less infrastructure to operate.

Trade-off:

- Vercel serverless previews are not identical to the future Docker/VPS runtime.
- Long-running workers, local Ollama, and full AI/scraping paths are not preview-runtime goals for this POC.

### Keep Docker For Local Stack

Decision: keep the local backend and infra stack on Docker.

Rationale:

- Local development still needs PostgreSQL, local services, and future infra parity.
- Vercel is only the remote branch-preview runtime.
- This avoids changing local developer workflow for JOB-125.

### Keep Python 3.13 In The Repo

Decision: keep `pyproject.toml` strict with `python = "^3.13"` and relax only inside the Vercel install script.

Rationale:

- The project standard remains Python 3.13.
- Vercel currently builds this project with Python 3.12.
- `scripts/vercel-install.sh` patches the Python constraint only in Vercel's ephemeral build workspace.

Trade-off:

- Vercel preview install is intentionally different from local Poetry install.
- This should be revisited when Vercel supports Python 3.13 for this project.

### Install A Minimal Vercel Runtime

Decision: `scripts/vercel-install.sh` installs only the dependencies needed to start the FastAPI preview runtime.

Rationale:

- Installing all Poetry main dependencies exceeded Vercel's Python bundle limit.
- The preview smoke test only requires application startup and `/health`.
- Heavy adapters are lazy-loaded in `app.core.dependency` so importing `app.main` does not require AI, scraping, or S3 packages.

Trade-off:

- Preview endpoints that need excluded optional packages may fail until those packages are added to the Vercel runtime or split into another deploy target.
- This is acceptable for the POC because the branch preview acceptance path is deployment + `/health`.

### Use `vercel curl` For Smoke Tests

Decision: smoke-test protected preview deployments with `npx vercel@latest curl /health --deployment <url>`.

Rationale:

- Direct `curl` received `401` because Vercel Preview Authentication protects deployments.
- Vercel's CLI `curl` command is designed to access protected deployments for automation.
- The command reads `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` from the environment.

Trade-off:

- The smoke test depends on Vercel CLI behavior.
- This is preferable to storing another bypass secret in GitHub for the POC.

### Accept GitHub Secrets Or Variables For Non-Secret IDs

Decision: workflow reads Vercel and Neon IDs from GitHub variables or repository secrets.

Rationale:

- Some values were initially entered as repository secrets.
- Supporting both avoids fragile setup and keeps the workflow unblocked.
- Actual sensitive values remain secrets: `NEON_API_KEY`, `PREVIEW_JWT_SECRET`, and `VERCEL_TOKEN`.

## Consequences

Positive:

- Backend preview deployment now passes end-to-end in GitHub Actions.
- Feature branches can produce a Vercel backend preview connected to a Neon branch.
- Vercel bundle size stays below the Python function limit.
- Production `.env` and production credentials are not used.

Negative / Limitations:

- Vercel preview runtime is a reduced runtime, not the full Docker stack.
- AI/scraping/S3-heavy endpoints may require additional runtime packaging decisions.
- Cleanup of stale Vercel previews and Neon branches remains a follow-up.

## Follow-Ups

- JOB-126: coordinate frontend preview origin with backend CORS.
- JOB-128: clean up Neon preview branches and stale previews after PR close/merge.
- Revisit Vercel Python 3.13 support when available.
- Revisit whether heavy optional backend capabilities need separate preview targets.

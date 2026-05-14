# ADR-0001: CI/CD hardening for JobAI backend

**Status:** Accepted
**Date:** 2026-05-14

## Context

The backend deploy path must be stable before continuing the AI Analysis work. The project already uses GitHub Actions,
Docker, PostgreSQL with pgvector, Alembic migrations, and SSH deployment through Docker Compose. The immediate CI failure
was caused by running tests against a PostgreSQL image without the `vector` extension.

## Decision

GitHub Actions remains the primary CI/CD system. Jenkins is added as an optional mirror pipeline for teams or servers that
need a self-hosted orchestrator, but it does not become the source of truth.

The CI pipeline now:

- Uses `pgvector/pgvector:pg16` for test PostgreSQL.
- Runs the full test suite before Docker image build.
- Builds the Docker image on PRs and pushes.
- Pushes GHCR images only from `main`.
- Uses concurrency controls to avoid stale runs overwriting newer deploys.

The deployment pipeline now:

- Runs only after a successful `Backend CI` workflow on `main`.
- Serializes production deploys.
- Backs up the previous remote compose/env files.
- Runs Alembic migrations before starting the app.
- Runs a smoke test against `/health` and fails the deploy if the app is not healthy.

## Options Considered

### GitHub Actions only

**Pros:** Already present, close to the repository, good PR visibility, simple GHCR auth.

**Cons:** Less useful when a company mandates Jenkins or self-hosted deployment controls.

### Jenkins only

**Pros:** Strong self-hosted control and familiar to many ops teams.

**Cons:** More infrastructure to operate now, more credentials to secure, less direct GitHub PR integration.

### GitHub Actions primary with Jenkins mirror

**Pros:** Keeps the current low-friction path while giving a portable CI definition for self-hosted environments.

**Cons:** Two pipeline definitions must stay aligned when CI logic changes.

## Consequences

- Production deploys are safer because migrations and smoke checks are part of the pipeline.
- Docker images are validated before merge through the PR build step.
- Static quality gates are intentionally not enabled yet because the current repo has existing Ruff, Black, and mypy debt.
- A follow-up quality ticket should normalize formatting and typing before these gates become mandatory.

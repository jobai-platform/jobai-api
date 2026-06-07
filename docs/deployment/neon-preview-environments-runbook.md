# Neon Preview Environments Runbook

**Owner:** Forge
**Last updated:** 2026-06-05
**Related tickets:** JOB-121, JOB-124, JOB-125, JOB-127, JOB-128, JOB-129
**Source of truth:** Git docs in this repository. Notion contains summaries and links back to Git.

## Purpose

This runbook explains how to operate JobAI preview environments without reading workflow internals.

Preview environment model:

```text
feature branch
  -> Vercel backend preview
  -> Neon preview database branch copied from develop-anonymized
  -> optional Vercel frontend preview pointing to the backend preview
```

## Current Decision

Neon preview branching is adopted for non-production preview databases after the POC.

Validated during the POC and follow-up workflows:

- Alembic migrations run successfully against Neon preview branches.
- The active vector migration creates `vector`, `vector(768)` columns, and HNSW indexes through `pgvector`.
- Backend preview deployment runs on Vercel and connects to the generated Neon branch `DATABASE_URL`.
- Protected Vercel `/health` smoke tests pass through `vercel curl`.
- PR-close, manual, and TTL cleanup are implemented for preview resources.

Important compatibility boundary:

- Local Docker still initializes `vectorscale` and `timescaledb` for local/dev experiments.
- Current Alembic migrations require `pgvector`, not `vectorscale` or `timescaledb`.
- Do not introduce a hard Neon preview dependency on `vectorscale` or `timescaledb` unless a new POC proves support.

## Required Access

GitHub repository access:

- read Actions logs;
- run manual workflows;
- read PR comments.

GitHub configuration:

```text
NEON_API_KEY                 secret
NEON_PROJECT_ID              variable or secret
NEON_PARENT_BRANCH           variable or secret, usually develop-anonymized
PREVIEW_JWT_SECRET           secret
VERCEL_TOKEN                 secret
VERCEL_ORG_ID                variable or secret
VERCEL_BACKEND_PROJECT_ID    variable or secret
PREVIEW_TTL_DAYS             optional variable, default 7
VERCEL_BRANCH_ENV_KEYS       optional variable, comma-separated
```

Neon access:

- project containing `develop-anonymized`;
- permission to list, create, and delete branches.

Vercel access:

- backend project linked to the repo;
- token allowed to deploy, list deployments, and delete preview deployments.

## Resource Naming

The raw Git branch is the only manual input operators should provide.

Example:

```text
feature/job-129-10-docsadr-document-neon-preview-environments-runbook-and
```

The backend helper derives the Neon branch using the same sanitizer as creation:

```text
preview-feature-job-129-10-docsadr-document-neon-preview-<hash>
```

Never manually target `main`, `develop`, `develop-anonymized`, `production`, `prod`, or a raw Neon branch id for cleanup.

## Manual Preview Branch Creation

Use this when a preview branch needs to be created or recreated outside the normal push workflow.

Prerequisites:

```bash
export NEON_PROJECT_ID=<project-id>
export NEON_API_KEY=<secret-api-key>
export NEON_PARENT_BRANCH=develop-anonymized
```

Create or reuse the branch:

```bash
poetry run python -m app.infrastructure.ci.neon_branch_lifecycle \
  --branch "feature/job-129-10-docsadr-document-neon-preview-environments-runbook-and" \
  --commit-sha "manual" \
  --project-id "$NEON_PROJECT_ID" \
  --api-key "$NEON_API_KEY" \
  --parent-branch "$NEON_PARENT_BRANCH"
```

Expected result:

```json
{"branch_name": "preview-feature-...", "branch_id": "br_...", "created": true}
```

The helper writes `DATABASE_URL` only when GitHub Actions environment files are present. For local/manual work, retrieve
the connection string from Neon or `neonctl` and convert it to an async SQLAlchemy URL if needed:

```text
postgresql://...?...sslmode=require
  -> postgresql+asyncpg://...?ssl=require
```

## Run Alembic Manually On A Preview Branch

Use this when debugging migrations independently from GitHub Actions.

```bash
export DATABASE_URL="postgresql+asyncpg://..."
export DATABASE_URL_SYNC="postgresql://..."
poetry run alembic upgrade head
```

If only the async URL is available, keep the same host/user/password/database and use a sync driver URL for
`DATABASE_URL_SYNC`.

## Debug Alembic Failures

Checklist:

1. Confirm `DATABASE_URL` points to the preview branch, not local Docker or production.
2. Confirm `DATABASE_URL_SYNC` is set for Alembic.
3. Confirm the Neon branch is ready in the Neon console.
4. Confirm `ssl=require` or Neon-compatible SSL parameters are present.
5. Re-run the failing migration locally against the preview branch.
6. If the failure is extension-related, check whether the migration requires only `vector` or a non-Neon extension.

Known compatibility rule:

- `vector` / `pgvector` is required and validated for current migrations.
- `vectorscale` and `timescaledb` are local-stack extensions and must not be added to preview migrations without a POC.

Rollback options:

- For a migration still under review, fix the migration and rerun `alembic upgrade head` on the preview branch.
- For a broken preview branch, delete and recreate the preview branch from `develop-anonymized`.
- Do not rollback or mutate `develop-anonymized` automatically from a feature workflow.

## Debug Backend Preview Health Check Failures

Symptom:

```text
Smoke test backend preview failed
```

Checklist:

1. Open the `Backend Preview` workflow run.
2. Check `Deploy backend preview to Vercel` logs for build or bundle errors.
3. Check `Smoke test backend preview` logs.
4. Use protected preview access, not direct curl:

```bash
VERCEL_TOKEN=<token> \
VERCEL_ORG_ID=<team-id> \
VERCEL_PROJECT_ID=<backend-project-id> \
npx vercel@latest curl /health --deployment <deployment-url>
```

Common causes:

- Vercel build uses Python 3.12; `scripts/vercel-install.sh` must relax the constraint only in the ephemeral build.
- Full Poetry install exceeds Vercel bundle size; use the minimal runtime install path.
- `DATABASE_URL` or `PREVIEW_JWT_SECRET` was not injected into `vercel deploy`.
- Direct `curl` returns `401` because preview deployments are protected.

## Debug CORS Or Frontend Wrong API URL

Symptoms:

```text
CORS error in browser console
Frontend preview calls production API
Frontend preview calls develop API
```

Checklist:

1. Read the backend PR comment and copy the backend preview URL.
2. Confirm the frontend preview uses the matching branch backend URL.
3. Confirm backend env contains the exact frontend preview origin:

```text
FRONTEND_ORIGIN=https://<frontend-preview>.vercel.app
CORS_ALLOW_ORIGINS=https://<frontend-preview>.vercel.app
CORS_ALLOW_ORIGIN_REGEX=^https://jobai-frontend-[a-z0-9]+-rpsantosvix-gmailcoms-projects\.vercel\.app$
PUBLIC_API_BASE_URL=<backend-public-api-base-url>
```

4. Confirm the browser request origin either exactly matches `CORS_ALLOW_ORIGINS` or matches the anchored
   `CORS_ALLOW_ORIGIN_REGEX`.
5. Re-run the backend preview workflow if the backend was deployed before the frontend URL was known.

Security rule:

- Do not use wildcard CORS for credentialed preview requests.
- Real OAuth callbacks remain disabled/dummy for ephemeral previews unless explicitly configured.

## Manual Cleanup

Use GitHub Actions first. It applies the same safety checks as PR-close cleanup.

```bash
gh workflow run backend-preview-cleanup.yml \
  --ref develop \
  -f mode=branch \
  -f branch="feature/job-129-10-docsadr-document-neon-preview-environments-runbook-and"
```

What it deletes:

- matching Neon preview branch;
- Vercel deployments for the raw feature branch;
- optional branch-specific Vercel env vars listed in `VERCEL_BRANCH_ENV_KEYS`.

What it refuses:

- protected branches;
- non-`preview-*` Neon branches;
- production Vercel deployments.

## Scheduled TTL Cleanup

The scheduled cleanup workflow runs daily and uses `PREVIEW_TTL_DAYS` or `7` days by default.

Manual janitor run:

```bash
gh workflow run backend-preview-cleanup.yml \
  --ref develop \
  -f mode=janitor \
  -f ttl_days=7
```

The janitor deletes stale Vercel deployments only when Vercel exposes safe branch metadata. Deployments without branch
metadata are skipped rather than deleted by age alone.

## Reset Or Rollback A Preview Branch

Use reset when a preview branch is corrupted, contains a bad migration, or must be recreated from the anonymized parent.

Preferred flow:

1. Run manual cleanup for the raw feature branch.
2. Re-run the `Backend Preview` workflow for the feature branch.
3. Confirm the new Neon branch was created from `develop-anonymized`.
4. Confirm Alembic and `/health` pass.

Commands:

```bash
gh workflow run backend-preview-cleanup.yml \
  --ref develop \
  -f mode=branch \
  -f branch="feature/<ticket>"

gh workflow run backend-preview.yml \
  --ref "feature/<ticket>"
```

Do not reset `develop-anonymized` as part of feature rollback. Refreshing `develop-anonymized` is a separate controlled
operation tied to anonymized data refresh policy.

## Emergency Stop

If cleanup appears unsafe:

1. Cancel the GitHub Actions run.
2. Confirm the target branch in the workflow summary.
3. Confirm the helper did not report a protected ref.
4. Delete resources manually in Neon/Vercel only after matching the preview branch slug to the feature branch.
5. Document the incident in Linear before retrying automation.

## Related Docs

- `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md`
- `docs/superpowers/plans/2026-06-03-neon-preview-database-branching.md`
- `docs/deployment/backend-preview-vercel-runbook.md`
- `docs/adr/adr-0003-preview-security-policy.md`
- `docs/adr/adr-0004-vercel-backend-preview-per-feature-branch.md`
- `docs/adr/adr-0005-preview-cleanup-safety-policy.md`
- `docs/adr/adr-0006-neon-preview-database-branching.md`

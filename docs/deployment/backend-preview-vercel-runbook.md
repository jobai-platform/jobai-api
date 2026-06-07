# Backend Preview Vercel Runbook

**Owner:** Forge
**Last updated:** 2026-06-05
**Related tickets:** JOB-125, JOB-128
**Workflows:** `.github/workflows/backend-preview.yml`, `.github/workflows/backend-preview-cleanup.yml`

## Purpose

This runbook explains how backend preview deployments work for feature branches and how to debug them when GitHub Actions or Vercel fails.

The preview model is:

```text
feature branch push
  -> GitHub Actions Backend Preview
  -> Neon preview branch create/reuse
  -> Alembic migrations on Neon branch
  -> Vercel FastAPI preview deploy
  -> Vercel-protected /health smoke test
  -> GitHub summary + PR comment
  -> PR close/manual/TTL cleanup
```

## Runtime Decision

Backend previews run on Vercel for the POC. Local development remains Docker-based.

This was chosen because:

- No VPS is currently available for backend previews.
- The frontend already runs on Vercel.
- Vercel allows one preview deployment per feature branch push.
- GitHub Actions can still control Neon branch lifecycle and migrations.

## Required GitHub Configuration

Sensitive secrets:

```text
NEON_API_KEY
PREVIEW_JWT_SECRET
VERCEL_TOKEN
```

IDs and configuration can be stored either as GitHub variables or repository secrets:

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
PREVIEW_TTL_DAYS
VERCEL_BACKEND_PUBLIC_API_BASE_URL
VERCEL_BRANCH_ENV_KEYS
```

The backend preview workflow also injects this anchored project-specific regex:

```text
CORS_ALLOW_ORIGIN_REGEX=^https://jobai-frontend-[a-z0-9]+-rpsantosvix-gmailcoms-projects\.vercel\.app$
```

It allows credentialed requests from dynamic Vercel previews of the `jobai-frontend` project while rejecting previews
from unrelated `vercel.app` projects. `CORS_ALLOW_ORIGINS` remains configured for exact develop/production origins.

## Required Vercel Configuration

The backend project must be linked to the repository and configured for the FastAPI preview path.

Local-only Vercel link file:

```text
.vercel/project.json
```

This file is ignored by Git and must not be committed.

Expected Vercel project values for this POC:

```text
orgId=team_tIMQ00Eyf9XsHbE9a9LPyaVv
projectId=prj_Jgdt0vJdXI8Tk2kka5JMbxvXqKgK
```

The project install command should run:

```bash
bash scripts/vercel-install.sh
```

## Local Preview Env File

The local import helper file is intentionally ignored by Git:

```text
env.vercel.preview
.env.vercel.preview
```

Use it only to import preview values into Vercel during the POC. Do not commit it.

After the POC, move long-lived secrets to the chosen secret-management process and rotate any credentials that were shared manually during setup.

## How The Workflow Works

1. Installs project dependencies in GitHub Actions with Poetry and Python 3.13.
2. Runs the fast non-integration test suite.
3. Validates required Neon and Vercel configuration.
4. Creates or reuses the Neon branch with `app.infrastructure.ci.neon_branch_lifecycle`.
5. Runs Alembic migrations on the generated Neon preview `DATABASE_URL`.
6. Generates preview metadata with `app.infrastructure.ci.backend_preview_deployment`.
7. Runs `npx vercel@latest deploy` with preview runtime/build env vars.
8. Runs `npx vercel@latest curl /health --deployment <deployment-url>` for the protected smoke test.
9. Writes GitHub summary and updates the PR preview comment.

## How Cleanup Works

Cleanup is handled by `.github/workflows/backend-preview-cleanup.yml`.

Triggers:

- `pull_request.closed` deletes resources for the closed PR head branch.
- `workflow_dispatch` supports manual cleanup for one branch or a manual TTL janitor run.
- `schedule` runs the TTL janitor daily.

Cleanup modes:

| Mode | Target | Behavior |
|---|---|---|
| `branch` | raw Git feature branch | derives the Neon preview branch with the same sanitizer as creation |
| `janitor` | `preview-*` resources older than TTL | deletes stale Neon branches and safe stale Vercel deployments |

Manual branch cleanup example:

```text
Workflow: Backend Preview Cleanup
mode=branch
branch=feature/job-128-09-cicd-cleanup-preview-backend-neon-branch-and-branch
```

Manual janitor example:

```text
Workflow: Backend Preview Cleanup
mode=janitor
ttl_days=7
```

The cleanup helper refuses protected targets before any delete call:

```text
main
develop
develop-anonymized
production
prod
```

Neon deletion is also limited to branch names starting with `preview-`.

### Cleanup Resources

The cleanup workflow deletes:

- Neon preview branch matching `sanitize_branch_name(<feature-branch>)`.
- Vercel backend deployments returned for the target branch.
- Optional branch-specific Vercel env vars listed in `VERCEL_BRANCH_ENV_KEYS`.

JOB-125 passes runtime env vars directly to `vercel deploy`, so `VERCEL_BRANCH_ENV_KEYS` is usually empty for the current
backend POC. Keep it available for future CI-managed branch variables.

### TTL Janitor

Default TTL is `7` days through `PREVIEW_TTL_DAYS`.

The janitor deletes stale Neon branches when:

- the branch name starts with `preview-`;
- the branch is older than the TTL.

The janitor deletes stale Vercel deployments only when:

- the deployment is older than the TTL;
- deployment metadata exposes a non-protected Git branch;
- the deployment is not production.

If Vercel metadata is missing, the janitor skips the deployment instead of guessing.

## Important Implementation Notes

### Python Version

The repository remains Python 3.13:

```toml
python = "^3.13"
```

Vercel currently builds this project with Python 3.12. `scripts/vercel-install.sh` temporarily changes only the ephemeral Vercel build copy to:

```toml
python = ">=3.12,<4.0"
```

Do not relax the committed project constraint for Vercel.

### Bundle Size

Vercel Python functions have a bundle size limit. Installing all Poetry runtime dependencies exceeded the limit.

The install script therefore installs only the minimal packages needed for FastAPI startup and `/health`.

Heavy adapters are lazy-loaded in `app.core.dependency`:

- LinkedIn scraper / JobSpy
- S3 / aioboto3
- Ollama / LangGraph / LangChain
- Timescale vector store adapter

If a preview endpoint starts using one of those adapters, add the required packages deliberately and re-check the bundle size.

### Protected Preview Smoke Test

Direct `curl` returns `401` because Vercel Authentication protects preview deployments.

Use:

```bash
npx vercel@latest curl /health --deployment <deployment-url>
```

The command requires these environment variables in GitHub Actions:

```text
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

## Troubleshooting

### Missing Vercel IDs

Symptom:

```text
VERCEL_BACKEND_PROJECT_ID is required for backend preview deployment
VERCEL_ORG_ID is required for backend preview deployment
```

Fix:

- Add `VERCEL_BACKEND_PROJECT_ID` and `VERCEL_ORG_ID` as GitHub variables or repository secrets.
- Confirm `VERCEL_TOKEN` exists as a secret.

### Vercel Python Version Fails Poetry

Symptom:

```text
Current Python version (3.12.x) is not allowed by the project (^3.13)
```

Fix:

- Confirm Vercel install command is `bash scripts/vercel-install.sh`.
- Confirm the script still patches the Python constraint only during Vercel build.

### Poetry Lock Changed In Vercel

Symptom:

```text
pyproject.toml changed significantly since poetry.lock was last generated
```

Current fix:

- The Vercel install path no longer runs full `poetry install`; it installs a minimal runtime with `pip`.

### Bundle Size Exceeds Vercel Limit

Symptom:

```text
Total bundle size (...) exceeds the size limit
```

Fix:

- Do not run full Poetry install in Vercel.
- Keep heavy adapters lazy-loaded.
- Add only required preview runtime packages to `scripts/vercel-install.sh`.

### Direct Smoke Test Returns 401

Symptom:

```text
curl: (22) The requested URL returned error: 401
```

Fix:

- Use `vercel curl`, not direct `curl`, for protected Vercel preview deployments.

### `vercel curl` Complains About Project IDs

Symptom:

```text
You specified VERCEL_ORG_ID but you forgot to specify VERCEL_PROJECT_ID
```

Fix:

- Set `VERCEL_PROJECT_ID` in the smoke step from `VERCEL_BACKEND_PROJECT_ID`.

### `vercel curl` Rejects `--token`

Symptom:

```text
curl: option --token: is unknown
```

Fix:

- Do not pass `--token` to `vercel curl`.
- Export `VERCEL_TOKEN` in the environment instead.

### Cleanup Refuses A Branch

Symptom:

```text
Refusing to cleanup protected branch ref
Refusing to cleanup non-preview Neon branch
```

Fix:

- Pass the raw feature branch name to manual cleanup.
- Do not pass `develop`, `develop-anonymized`, `main`, `production`, or a raw Neon branch id.
- Let the cleanup helper derive the Neon preview branch internally.

### Cleanup Does Not Delete Vercel Deployments In Janitor Mode

Symptom:

```text
No stale preview resources older than 7 days
```

or Neon branches are deleted but Vercel deployments remain.

Fix:

- Confirm the deployments expose branch metadata in Vercel.
- If metadata is missing, use manual branch cleanup or delete the deployment in Vercel.
- Do not loosen janitor matching to age-only deletion; that could delete unrelated previews.

## Validation Commands

Local checks used for JOB-125:

```bash
python - <<'PY'
import yaml
from pathlib import Path
with Path('.github/workflows/backend-preview.yml').open() as f:
    yaml.safe_load(f)
print('yaml ok')
PY

poetry run python - <<'PY'
import app.main
print(app.main.app.title)
PY

poetry run pytest tests/unit/test_backend_preview_deployment.py tests/unit/test_neon_branch_lifecycle.py -q
poetry run ruff check app/core/dependency.py tests/unit/test_backend_preview_deployment.py tests/unit/test_neon_branch_lifecycle.py
bash -n scripts/vercel-install.sh

python - <<'PY'
import yaml
from pathlib import Path
with Path('.github/workflows/backend-preview-cleanup.yml').open() as f:
    yaml.safe_load(f)
print('cleanup yaml ok')
PY

poetry run pytest tests/unit/test_backend_preview_cleanup.py tests/unit/test_neon_branch_lifecycle.py -q
poetry run ruff check app/infrastructure/ci/backend_preview_cleanup.py tests/unit/test_backend_preview_cleanup.py
```

Expected result:

```text
yaml ok
JobAI API Platform
6 passed
All checks passed
```

## Final Verified State

On 2026-06-04, GitHub Actions run `26968887279` passed the backend preview workflow after commit `037cc37`.

Verified steps:

- Neon preview branch create/reuse passed.
- Alembic migrations passed.
- Vercel deploy passed.
- Protected `/health` smoke test passed through `vercel curl`.
- GitHub summary and PR comment passed.

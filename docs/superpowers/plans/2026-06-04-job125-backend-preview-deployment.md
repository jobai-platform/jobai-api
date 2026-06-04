# JOB-125 — Backend Preview Deployment Plan

## Objective

Ship the backend preview deployment layer after JOB-124 creates the Neon preview branch, using Vercel for backend
feature previews during the POC.

## Scope

In scope:

- Vercel FastAPI backend preview deployment path.
- Branch-specific preview env injection into Vercel deploys.
- Vercel-only Poetry install helper for Python 3.12 preview runtime compatibility.
- Deterministic Neon preview branch per feature branch.
- `/health` smoke test against the returned Vercel deployment URL.
- GitHub Actions summary and PR comment.

Out of scope:

- PR-close cleanup, handled by JOB-128.
- Frontend Vercel coordination, handled by JOB-126.
- Production Neon migration.
- Docker/VPS preview hosting.

## Execution Steps

1. Read ticket, Notion reference, and existing Git docs.
2. Create the JOB-125 branch from `origin/develop` if missing.
3. Audit current `.github/workflows/backend-preview.yml` from JOB-124.
4. Add tested CI helper for preview metadata and PR comment content.
5. Add Vercel FastAPI entrypoint configuration in `pyproject.toml`.
6. Add `scripts/vercel-install.sh` so Vercel can build with Python 3.12 while the committed repo remains Python 3.13.
7. Extend backend preview workflow:
   - run fast tests;
   - validate Neon and Vercel CI configuration;
   - create/reuse Neon branch;
   - run migrations on Neon branch;
   - deploy backend preview to Vercel with branch-specific env;
   - smoke test public `/health`;
   - publish summary and PR comment.
8. Add JOB-125 spec documenting decisions, required secrets, env values, and follow-ups.
9. Validate targeted unit tests, shell syntax, TOML parsing, and YAML parsing locally.

## Validation

Local validation:

```bash
bash -n scripts/vercel-install.sh
python - <<'PY'
from pathlib import Path
import yaml
with Path('.github/workflows/backend-preview.yml').open() as f:
    yaml.safe_load(f)
print('YAML parsed')
PY
python - <<'PY'
import tomllib
from pathlib import Path
with Path('pyproject.toml').open('rb') as handle:
    data = tomllib.load(handle)
assert data['tool']['vercel']['entrypoint'] == 'app.main:app'
print('pyproject vercel entrypoint ok')
PY
poetry run pytest tests/unit/test_backend_preview_deployment.py tests/unit/test_neon_branch_lifecycle.py -q
poetry run ruff check app/infrastructure/ci/backend_preview_deployment.py app/infrastructure/ci/neon_branch_lifecycle.py tests/unit/test_backend_preview_deployment.py tests/unit/test_neon_branch_lifecycle.py
```

Expected result:

```text
YAML parsed
pyproject vercel entrypoint ok
6 passed
All checks passed
```

GitHub validation after PR:

- Push branch.
- Confirm `Backend Preview` creates/reuses the Neon branch.
- Confirm Alembic migrations run on the Neon branch.
- Confirm `vercel deploy` returns a backend preview URL.
- Confirm `/health` passes against the Vercel deployment URL.
- Confirm GitHub summary and PR comment show the preview URL.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Vercel Python runtime is 3.12 while repo requires 3.13 | `scripts/vercel-install.sh` temporarily relaxes Poetry and refreshes the lock only during Vercel build |
| Vercel project variables are missing | Workflow validates `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_BACKEND_PROJECT_ID` before Neon work |
| Frontend preview origin is unknown | Use `PREVIEW_FRONTEND_ORIGIN` override until JOB-126 wires Vercel coordination |
| Preview DB URL appears in logs | Neon helper masks generated `DATABASE_URL` in GitHub Actions |
| Cleanup is not automated yet | JOB-128 owns Neon branch deletion and stale Vercel preview cleanup |

## Completion Criteria

- CI helper tests pass.
- `backend-preview.yml` parses as YAML.
- Workflow contains DB lifecycle, migration, Vercel deployment, smoke test, summary, and PR comment steps.
- Spec and plan are committed with the implementation.

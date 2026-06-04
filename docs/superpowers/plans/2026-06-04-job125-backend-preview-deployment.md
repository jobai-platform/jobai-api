# JOB-125 — Backend Preview Deployment Plan

**Status:** Completed and verified
**Verified commit:** `037cc37`
**Verified workflow run:** `26968887279`

## Objective

Ship the backend preview deployment layer after JOB-124 creates the Neon preview branch, using Vercel for backend feature
previews during the POC.

## Scope

In scope:

- Vercel FastAPI backend preview deployment path.
- Branch-specific preview env injection into Vercel deploys.
- Vercel-only install helper for Python 3.12 preview runtime compatibility.
- Minimal Vercel runtime dependency installation to stay under function bundle limits.
- Lazy loading of heavy optional adapters so `app.main` can start in the Vercel preview runtime.
- Deterministic Neon preview branch per feature branch.
- Protected `/health` smoke test through Vercel CLI.
- GitHub Actions summary and PR comment.
- Documentation of decisions and runbook.

Out of scope:

- PR-close cleanup, handled by JOB-128.
- Frontend Vercel coordination, handled by JOB-126.
- Production Neon migration.
- VPS preview hosting.
- Full AI/scraping/S3 runtime support inside Vercel previews.

## Execution Steps

1. Read ticket, branch, and existing preview docs.
2. Create or reuse the JOB-125 branch from `origin/develop`.
3. Audit the existing `.github/workflows/backend-preview.yml` from JOB-124.
4. Add tested CI helper for preview metadata and PR comment content.
5. Add Vercel FastAPI entrypoint configuration in `pyproject.toml`.
6. Add `scripts/vercel-install.sh` so Vercel can build with Python 3.12 while the committed repo remains Python 3.13.
7. Extend backend preview workflow:
   - run fast tests;
   - validate Neon and Vercel CI configuration;
   - accept required IDs from GitHub variables or repository secrets;
   - create/reuse Neon branch;
   - run migrations on Neon branch;
   - deploy backend preview to Vercel with branch-specific env;
   - smoke test protected `/health` with `vercel curl`;
   - publish summary and PR comment.
8. Add `.vercel` and local preview env files to `.gitignore`.
9. Create local `.vercel/project.json` for the Vercel backend project; keep it ignored.
10. Create local ignored preview env helper file for POC secret import.
11. Fix Vercel-specific CI failures discovered during live validation:
    - missing Vercel IDs entered as secrets rather than variables;
    - Vercel Python 3.12 vs project Python 3.13;
    - Vercel Poetry lock mismatch;
    - Vercel Python bundle size limit;
    - protected preview `401` from direct `curl`;
    - `vercel curl` environment requirements.
12. Document implementation decisions in ADR-0004.
13. Add the Vercel backend preview runbook.
14. Validate locally and through GitHub Actions.

## Decisions Taken

| Decision | Rationale | Consequence |
|---|---|---|
| Use Vercel instead of VPS for backend previews | No backend VPS is available; frontend already uses Vercel | Preview runtime is Vercel serverless, not Docker/VPS |
| Keep Docker for local backend/infra | Local stack still needs Postgres and future infra parity | Vercel is remote preview only |
| Keep committed Python constraint at `^3.13` | Repository standard remains Python 3.13 | Vercel script patches only ephemeral build copy |
| Install minimal Vercel runtime with `pip` | Full Poetry install exceeded Vercel bundle size | Preview runtime supports startup and `/health`; heavy endpoints need future packaging decisions |
| Lazy-load heavy adapters | Avoid importing AI/scraping/S3 packages during `app.main` startup | Optional adapters load only when their dependencies are used |
| Use `vercel curl` for smoke test | Direct `curl` returns `401` on protected previews | CI smoke works without disabling Vercel Preview Authentication |
| Accept IDs from variables or secrets | User entered some non-sensitive IDs as secrets during setup | Workflow is less fragile and still keeps real secrets as secrets |

## Validation

Local validation:

```bash
python - <<'PY'
from pathlib import Path
import yaml
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
```

Observed result:

```text
yaml ok
JobAI API Platform
6 passed
All checks passed
```

GitHub validation:

- Branch: `feature/job-125-07-cicd-deploy-backend-preview-per-feature-branch`
- Commit: `037cc37`
- Workflow run: `26968887279`
- Backend Preview job: passed in `2m13s`

Verified GitHub steps:

- Fast test suite passed.
- Configuration validation passed.
- Neon preview branch create/reuse passed.
- Alembic migrations passed.
- Vercel deploy passed.
- Protected `/health` smoke test passed with `vercel curl`.
- GitHub summary passed.
- PR comment update passed.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Vercel Python runtime is 3.12 while repo requires 3.13 | `scripts/vercel-install.sh` temporarily relaxes only the Vercel build copy |
| Vercel project variables are missing | Workflow validates `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_BACKEND_PROJECT_ID` before Neon work |
| Vercel IDs are entered as secrets instead of variables | Workflow accepts IDs from either GitHub variables or secrets |
| Frontend preview origin is unknown | Use `PREVIEW_FRONTEND_ORIGIN` override until JOB-126 wires frontend/backend coordination |
| Preview DB URL appears in logs | Neon helper masks generated `DATABASE_URL` in GitHub Actions |
| Vercel function bundle is too large | Minimal Vercel install + lazy imports of heavy optional adapters |
| Vercel Preview Authentication returns `401` to direct `curl` | Use `npx vercel@latest curl` for the smoke test |
| Cleanup is not automated yet | JOB-128 owns Neon branch deletion and stale Vercel preview cleanup |

## Completion Criteria

- CI helper tests pass.
- `backend-preview.yml` parses as YAML.
- Workflow contains DB lifecycle, migration, Vercel deployment, protected smoke test, summary, and PR comment steps.
- Spec, plan, ADR, and runbook document the final implementation and decisions.
- Backend Preview workflow passes on GitHub Actions.

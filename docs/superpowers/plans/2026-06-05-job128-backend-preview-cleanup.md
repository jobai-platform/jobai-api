# JOB-128 — Backend Preview Cleanup Plan

**Status:** Draft for implementation
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-128

## Objective

Close the preview environment lifecycle by deleting backend preview resources after PR close and by running a scheduled
TTL janitor for orphaned resources.

## Scope

In scope:

- add a cleanup workflow for PR close, manual dispatch, and scheduled janitor runs;
- delete matching Neon preview branches safely;
- delete matching Vercel backend preview deployments safely;
- support optional branch-specific Vercel env var cleanup for future CI-managed variables;
- post cleanup summaries in GitHub Actions and PR comments when a PR exists;
- document the cleanup runbook.

Out of scope:

- production cleanup;
- deletion of Git branches;
- cleanup of frontend preview resources owned by JOB-126;
- changing local Docker development stack.

## Execution Steps

1. Confirm JOB-128 branch from Linear and create it from `origin/develop` if missing.
2. Inspect JOB-124/JOB-125 helpers and workflows.
3. Write this plan and the design spec.
4. Add tests for cleanup safety, target derivation, TTL filtering, and Vercel metadata filtering.
5. Add `app.infrastructure.ci.backend_preview_cleanup` helper.
6. Add `.github/workflows/backend-preview-cleanup.yml`.
7. Update backend preview runbook with cleanup operations.
8. Validate unit tests, workflow YAML, shell-free CLI parsing, and ruff.
9. Commit, push, and open a PR for review.

## Decisions Taken

| Decision | Reason | Trade-Off |
|---|---|---|
| Reuse JOB-124 sanitizer | Cleanup targets the exact Neon branch created by preview workflow | Manual users must pass raw branch names, not arbitrary resource ids |
| Reject non-`preview-*` Neon branch names | Prevent production/develop deletion | Cleanup cannot target custom non-preview branches |
| Use Vercel REST API for deployment deletion | API supports listing by branch and deleting by id/url | Requires `VERCEL_TOKEN`, project id, and org id in CI |
| Keep Vercel env cleanup optional | JOB-125 passes env directly to deploy and does not persist branch vars | Future branch env cleanup needs configured env keys |
| Skip Vercel deployments with missing branch metadata in janitor | Avoid deleting unrelated previews by age only | Some stale Vercel deployments may require manual cleanup |
| Soft-delete Neon branches by default | Neon supports recovery grace period | Hard delete can be added later if cost pressure requires it |

## Test Plan

Run focused tests first:

```bash
poetry run pytest tests/unit/test_backend_preview_cleanup.py -q
```

Then validate related preview lifecycle helpers:

```bash
poetry run pytest tests/unit/test_backend_preview_cleanup.py tests/unit/test_neon_branch_lifecycle.py -q
```

Static checks:

```bash
poetry run ruff check app/infrastructure/ci/backend_preview_cleanup.py tests/unit/test_backend_preview_cleanup.py
python - <<'PY'
from pathlib import Path
import yaml

yaml.safe_load(Path('.github/workflows/backend-preview-cleanup.yml').read_text())
PY
```

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Cleanup deletes a protected Neon branch | require sanitized `preview-*` branch name and reject protected refs |
| Manual cleanup receives the Neon branch name instead of raw Git branch | document expected input and derive all resource names internally |
| Vercel deployment list lacks branch metadata | skip unsafe janitor deletion and report skipped deployments |
| Closed PR comment is unavailable | always write GitHub Actions summary; PR comment only when `pull_request.number` exists |
| Secrets leak in logs | never print DB URLs or tokens; only print branch names, ids, and deployment ids |

## Completion Criteria

- Cleanup workflow exists and supports PR close, manual dispatch, and schedule.
- Manual cleanup targets one branch safely.
- Scheduled janitor applies a TTL to orphaned preview resources.
- Protected branches are rejected by tests and implementation.
- Runbook explains cleanup operations and troubleshooting.

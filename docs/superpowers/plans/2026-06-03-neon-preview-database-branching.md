 # Neon Preview Database Branching — Implementation Plan

**Date:** 2026-06-03
**Last updated:** 2026-06-05
**Status:** Cycle 38 implemented for preview environments
**Spec:** `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md`
**Final ADR:** `docs/adr/adr-0006-neon-preview-database-branching.md`
**Runbook:** `docs/deployment/neon-preview-environments-runbook.md`

---

## 1. Objective

Implement a complete feature-preview environment model for JobAI:

```text
feature branch
  -> Vercel frontend preview
  -> backend preview deployment
  -> Neon preview database branch copied from anonymized develop
```

The implementation must protect production, avoid personal-data exposure, run Alembic migrations on isolated databases, and clean up preview resources automatically.

---

## 2. Recommended Rollout

Do not migrate everything at once.

Completed cycle sequence:

1. POC Neon compatibility.
2. Define preview security policy.
3. Add Neon branch lifecycle workflow.
4. Add Vercel backend preview deployment.
5. Add cleanup and TTL janitor.
6. Finalize docs, ADR, runbook, rollback, and Notion summaries.

Future-cycle items:

- Connect frontend preview to the matching backend preview URL.
- Finalize `develop-anonymized` refresh cadence and owner.
- Decide separately whether production should move to Neon.

---

## 3. Phase 0 — Validation And Decisions

### Tasks

- [x] Confirm backend preview hosting provider: Vercel for the POC.
- [ ] Confirm whether frontend/backend repos are separate or monorepo.
- [x] Confirm whether feature DB branches are created on push or PR open: feature branch push.
- [x] Confirm OAuth behavior in previews: dummy/disabled for ephemeral previews unless explicitly configured.
- [x] Confirm object storage strategy for previews: no production object storage reads; future bucket/prefix isolation remains open.
- [ ] Confirm anonymization source and refresh frequency for `develop-anonymized`.
- [x] Confirm whether `timescaledb` and `vectorscale` are hard requirements: not required for current preview migrations.

### Deliverables

- [x] Approved technical spec.
- [x] Approved implementation plan.
- [x] Decision record or ADR if Neon is adopted beyond POC.

### Acceptance Criteria

- All open questions in the spec have an owner or explicit decision.
- No implementation starts before extension compatibility is validated.

---

## 4. Phase 1 — Neon Compatibility POC

### Goal

Validate that the current backend can run against Neon without weakening existing database behavior.

### Tasks

- [ ] Create a Neon project for JobAI non-production.
- [ ] Create a test branch manually.
- [ ] Create a test role with least privileges.
- [ ] Configure local `.env` against the Neon test branch.
- [ ] Run:

```bash
poetry run alembic upgrade head
poetry run pytest tests/infrastructure/ -q
poetry run pytest tests/presentation/ -q
```

- [ ] Validate extensions:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

- [ ] Validate vector index creation from current migrations.
- [ ] Validate `TimescaleVectorStoreAdapter` similarity queries.
- [ ] Document extension support results.

### Expected Findings

The likely minimum viable path is `pgvector` support. If `vectorscale` or `timescaledb` is unavailable on Neon, the team must decide whether those extensions are truly required for hosted environments.

### Acceptance Criteria

- Alembic migrations pass on Neon.
- Vector embedding tables and HNSW indexes are created successfully.
- The backend can run `/health` with Neon `DATABASE_URL`.
- Any unsupported extension has a documented mitigation.

---

## 5. Phase 2 — Develop-Anonymized Branch

### Goal

Create the long-lived parent database for all non-production feature branches.

### Tasks

- [ ] Create Neon branch `develop-anonymized`.
- [ ] Define anonymization scripts in git.
- [ ] Remove or mask:

```text
emails
names
phone numbers
addresses
OAuth tokens
payment identifiers
CV content
uploaded document references
LLM traces containing personal data
```

- [ ] Add deterministic seed data for:

```text
Candidate
BusinessAccount
JobPosting
Application
SearchAgent
SkillMatch
AIAnalysis
Subscription test states
```

- [ ] Run Alembic on `develop-anonymized`.
- [ ] Run backend smoke test against `develop-anonymized`.
- [ ] Document refresh process and owner.

### Acceptance Criteria

- `develop-anonymized` contains useful test data.
- No production personal data remains.
- Refresh process is repeatable.
- Feature branches can be safely derived from this branch.

---

## 6. Phase 3 — GitHub Actions For Neon Branch Lifecycle

### Goal

Automate preview DB creation, migration, and deletion.

### New Secrets And Variables

Secrets:

```text
NEON_API_KEY
PREVIEW_JWT_SECRET
PREVIEW_DEPLOY_HOST
PREVIEW_DEPLOY_USER
PREVIEW_DEPLOY_SSH_KEY
PREVIEW_GHCR_TOKEN
```

Variables:

```text
NEON_PROJECT_ID
NEON_PARENT_BRANCH=develop-anonymized
PREVIEW_BACKEND_BASE_DOMAIN
```

### New Workflow: `backend-preview.yml`

Trigger:

```yaml
on:
  push:
    branches-ignore:
      - main
      - develop
```

Steps:

- [ ] Checkout.
- [ ] Set up Python and Poetry.
- [ ] Install dependencies.
- [ ] Run fast test suite:

```bash
poetry run pytest -q
```

- [ ] Build Docker image with commit SHA.
- [ ] Sanitize branch name.
- [ ] Create or reuse Neon branch from `develop-anonymized`.
- [ ] Export `DATABASE_URL`.
- [ ] Run:

```bash
poetry run alembic upgrade head
```

- [ ] Deploy backend preview with branch-specific env.
- [ ] Smoke test:

```bash
curl -fsS https://<branch>.preview-api.sovrum.dev/health
```

- [ ] Write GitHub Actions summary.
- [ ] Post/update PR comment if PR exists.

### New Workflow: `backend-preview-cleanup.yml`

Trigger:

```yaml
on:
  pull_request:
    types:
      - closed
  workflow_dispatch:
```

Steps:

- [ ] Sanitize branch name.
- [ ] Delete backend preview deployment.
- [ ] Delete Neon branch.
- [ ] Delete branch-specific Vercel env var if this workflow manages it.
- [ ] Post cleanup summary.

### Acceptance Criteria

- Feature branch push creates a Neon branch.
- Migration failure stops deployment.
- Backend preview URL is deterministic.
- Cleanup removes all preview resources.

---

## 7. Phase 4 — Backend Preview Hosting

### Preferred POC Option

Use existing SSH + Docker Compose if the current server has enough capacity. Otherwise choose a preview-app platform before implementation.

### Tasks For SSH + Docker Compose

- [ ] Add reverse proxy support for wildcard branch subdomains.
- [ ] Create one compose project per branch:

```text
jobai-preview-<sanitized-branch>
```

- [ ] Generate `.env.preview.<branch>` from CI.
- [ ] Use isolated environment values:

```text
APP_ENV=preview
DATABASE_URL=<neon branch url>
JWT_SECRET=<preview secret>
CORS_ALLOW_ORIGINS=<matching frontend preview origin>
PUBLIC_API_BASE_URL=https://<branch>.preview-api.sovrum.dev
```

- [ ] Ensure preview deployments cannot read production `.env`.
- [ ] Add preview smoke test.
- [ ] Add cleanup command.

### Acceptance Criteria

- Multiple feature backends can run without port conflicts.
- Each preview connects only to its own Neon branch.
- Reverse proxy routes branch URLs correctly.
- Cleanup stops and removes preview containers/network config.

---

## 8. Phase 5 — Frontend Preview Coordination

### Goal

Ensure every Vercel preview calls its matching backend preview.

### Tasks

- [ ] Choose coordination model:

```text
Option C: branch-specific Vercel env var from CI
or
Option B: combined frontend/backend orchestration workflow
```

- [ ] Set or inject:

```text
NEXT_PUBLIC_API_BASE_URL=https://<branch>.preview-api.sovrum.dev
```

- [ ] Ensure frontend preview deploy runs after backend preview is ready.
- [ ] Verify CORS with the actual Vercel preview URL.
- [ ] Verify frontend can call:

```text
/api/v1/...
/health
auth endpoints if enabled
```

### Acceptance Criteria

- Feature preview frontend calls feature preview backend.
- No preview calls production backend accidentally.
- No preview calls shared develop backend unless explicitly configured as fallback.

---

## 9. Phase 6 — CORS, Auth, Cookies, OAuth

### Tasks

- [ ] Audit current backend CORS config.
- [ ] Add support for exact preview origins or controlled regex.
- [ ] Decide cookie policy before HTTP-only sessions are enabled.
- [ ] Disable real OAuth in feature previews for first iteration, unless needed.
- [ ] Allow OAuth callbacks only for develop and production initially.
- [ ] Document provider callback requirements.

### Acceptance Criteria

- Feature preview requests pass CORS.
- Credentialed requests do not use wildcard origins.
- OAuth behavior is explicit per environment.

---

## 10. Phase 7 — Object Storage And AI Preview Policy

### Tasks

- [ ] Define preview object storage bucket or prefix.
- [ ] Ensure previews never read production files.
- [ ] Decide whether preview AI flows use shared non-production Ollama.
- [ ] Add environment tag for Langfuse traces or disable preview tracing.
- [ ] Add seed files if Candidate CV flows need E2E testing.

### Acceptance Criteria

- Preview DB rows do not reference production object keys.
- Preview AI calls cannot leak production data.
- Observability traces are separated from production.

---

## 11. Phase 8 — Develop And Production Hardening

### Develop

- [ ] Add backend develop deployment if not already present.
- [ ] Point backend develop to `develop-anonymized`.
- [ ] Run Alembic on develop deploy.
- [ ] Smoke test develop.

### Production

- [ ] Keep existing production deploy isolated.
- [ ] Protect Neon production branch if production moves to Neon.
- [ ] Use distinct production credentials.
- [ ] Verify rollback process.
- [ ] Update production runbook.

### Acceptance Criteria

- Develop and production are clearly separated.
- Preview workflows cannot mutate production.
- Production migration and smoke test remain mandatory.

---

## 12. Phase 9 — Cleanup, TTL, And Cost Controls

### Tasks

- [ ] Add PR-close cleanup.
- [ ] Add manual cleanup workflow.
- [ ] Add scheduled janitor workflow for stale preview branches.
- [ ] Define TTL, e.g. 7 days after last commit or PR close.
- [ ] Monitor Neon branch count and compute usage.
- [ ] Alert if preview branch count exceeds threshold.

### Acceptance Criteria

- Merged/closed PRs do not leave active DB branches.
- Orphaned previews are cleaned automatically.
- Cost risk is bounded.

---

## 13. Phase 10 — Documentation And ADR

### Tasks

- [x] Update `.env.example`.
- [x] Add backend preview runbook: `docs/deployment/backend-preview-vercel-runbook.md`.
- [x] Add Neon preview environments runbook: `docs/deployment/neon-preview-environments-runbook.md`.
- [x] Add Neon branching ADR: `docs/adr/adr-0006-neon-preview-database-branching.md`.
- [x] Add troubleshooting guide:

```text
Neon branch creation fails
Alembic migration fails
backend preview healthcheck fails
CORS fails
frontend points to wrong backend
cleanup fails
```

- [x] Publish readable summary to Notion.

### Acceptance Criteria

- New engineer can understand the environment model from docs.
- Operators can clean up or rollback previews without reading workflow internals.

---

## 14. Proposed PR Breakdown

### PR 1 — Neon POC Documentation

- Add spec and plan.
- Add extension compatibility notes.
- No runtime changes.

### PR 2 — Backend Config Preparation

- Extend env config.
- Add tests for CORS env parsing if needed.
- Update `.env.example`.

### PR 3 — Neon Branch Lifecycle Workflow

- Add branch create/delete workflows.
- No backend deploy yet.
- Validate migrations against Neon branch.

### PR 4 — Backend Preview Deployment

- Add preview deploy workflow.
- Add smoke test.
- Add cleanup.

### PR 5 — Frontend Coordination

- Add branch-specific `NEXT_PUBLIC_API_BASE_URL` handling.
- Verify Vercel preview calls preview backend.

### PR 6 — Hardening

- Add TTL janitor.
- Add schema diff comments.
- Add runbook and ADR.

---

## 15. Manual Test Script For POC

```bash
# 1. Create or select a Neon test branch manually.
export DATABASE_URL='postgresql+asyncpg://...'

# 2. Run migrations.
poetry run alembic upgrade head

# 3. Run relevant integration tests.
poetry run pytest tests/infrastructure/ -q
poetry run pytest tests/presentation/ -q

# 4. Start backend.
poetry run uvicorn app.main:app --reload

# 5. Smoke test.
curl -fsS http://127.0.0.1:8000/health
```

---

## 16. Definition Of Done

The full implementation is done when:

- `main`, `develop`, and feature branches have isolated backend/database targets.
- feature branch push creates a preview DB from anonymized develop.
- Alembic runs on preview DB before backend preview deploy.
- frontend preview calls matching backend preview.
- CORS/auth behavior works for preview.
- cleanup removes backend preview and Neon branch.
- docs and runbooks are updated.
- production cannot be mutated by preview workflows.

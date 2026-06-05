# Neon Preview Database Branching — JobAI Backend
## Technical Spec

**Date:** 2026-06-03
**Last updated:** 2026-06-05
**Status:** Implemented for preview environments — POC accepted
**Owner:** Backend / Platform
**Related systems:** Backend API, Frontend Vercel CI/CD, GitHub Actions, Neon Postgres, Alembic, Ollama, MinIO, Langfuse
**Final ADR:** `docs/adr/adr-0006-neon-preview-database-branching.md`
**Runbook:** `docs/deployment/neon-preview-environments-runbook.md`

---

## 1. Executive Summary

JobAI evaluated and adopted Neon as the managed PostgreSQL provider for isolated feature preview environments.

The target workflow is:

- `main` uses a protected production database.
- `develop` uses a long-lived anonymized database branch.
- each feature branch or PR gets an ephemeral Neon branch derived from `develop-anonymized`.
- each feature branch also gets a backend preview deployment wired to that Neon branch.
- each frontend Vercel preview points to the matching backend preview through `NEXT_PUBLIC_API_BASE_URL`.
- feature preview resources are deleted when the PR is merged or closed.

This gives each feature a complete review environment:

```text
frontend preview
  -> backend preview
  -> Neon preview branch copied from anonymized develop
```

The preview database must never be derived directly from production. It must derive from `develop-anonymized`.

Final implementation summary:

- JOB-124 creates or reuses deterministic Neon preview branches.
- JOB-125 deploys Vercel backend previews and runs protected `/health` smoke tests.
- JOB-127 defines preview security boundaries.
- JOB-128 cleans preview branches/deployments on PR close, manual dispatch, and TTL janitor.
- JOB-129 finalizes Git docs, ADR, runbook, rollback, and Notion summaries.

---

## 2. Context

The frontend is now deployed by GitHub Actions through Vercel CLI:

- feature branches deploy to Vercel Preview.
- `develop` deploys to a Vercel develop environment.
- `main` deploys to Vercel production.
- preview deployments are cleaned up after merge.

The backend currently uses:

- FastAPI.
- Python 3.13.
- Alembic migrations.
- PostgreSQL-compatible database URLs.
- local Docker development with TimescaleDB and extensions.
- `pgvector` for vector embeddings.
- `vectorscale` and `timescaledb` in local initialization.
- Ollama for local AI inference.
- MinIO for local object storage.
- Langfuse self-hosted locally for LLM observability.
- GitHub Actions for CI and production deployment.

Current backend CI uses `pgvector/pgvector:pg16` for test PostgreSQL. Local dev uses `timescale/timescaledb-ha:pg16` and initializes:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

The POC validated the current hosted preview requirement: PostgreSQL + `pgvector` / `vector`. Local-only `vectorscale`
and `timescaledb` initialization remains outside the preview runtime until a future compatibility POC proves a need.

---

## 2.1 POC Compatibility Results

Validated and accepted for preview environments:

| Area | Result | Notes |
|---|---|---|
| Neon branch lifecycle | Passed | deterministic `preview-*` branch created/reused from `develop-anonymized` |
| Alembic migrations | Passed | migrations run on Neon preview branches before backend preview deploy |
| `pgvector` / `vector` | Passed | current migration creates `vector`, `vector(768)`, and HNSW indexes |
| `vectorscale` | Not required for preview | local Docker initializes it, but current migrations do not require it |
| `timescaledb` | Not required for preview | local Docker initializes it, but current migrations do not require it |
| Backend preview | Passed | Vercel deploy connects to branch-specific Neon `DATABASE_URL` |
| Protected health check | Passed | smoke test uses `npx vercel@latest curl /health --deployment <url>` |
| Cleanup | Passed | PR close/manual/TTL workflow removes safe preview resources |

Decision boundary:

- Neon is adopted for preview database branching.
- Production database migration to Neon remains a separate decision.
- Local Docker remains the full local backend/infra stack.

---

## 3. Goals

1. Provide isolated database environments for feature development and preview testing.
2. Keep production security-first and protected.
3. Use a long-lived `develop` database branch based on anonymized data.
4. Create one ephemeral DB branch per feature branch or PR.
5. Apply Alembic migrations to every ephemeral branch before exposing the backend preview.
6. Wire frontend previews to matching backend previews.
7. Clean up all preview resources after PR merge or close.
8. Preserve the backend architecture and deployment discipline already in place.
9. Avoid exposing production personal data in feature, preview, or develop environments.

---

## 4. Non-Goals

The first implementation should not:

- migrate production to Neon before a compatibility and rollback POC is complete.
- expose production data to previews.
- replace local Docker development immediately.
- change application layer, domain layer, or DDD boundaries.
- introduce OpenAI or Anthropic backend calls.
- solve object-storage branching for MinIO/S3 beyond documenting the dependency.
- make frontend fake repositories real unless required for preview validation.

---

## 5. Proposed Environment Model

### 5.1 Branch Hierarchy

```text
Neon project: jobai

production                    protected
└── develop-anonymized         long-lived, reset intentionally
    ├── preview-feature-job-109 ephemeral
    ├── preview-feature-job-123 ephemeral
    └── preview-bugfix-auth     ephemeral
```

Alternative if production starts outside Neon:

```text
external production DB
└── scheduled sanitized import into Neon develop-anonymized
    ├── preview-feature-* ephemeral
```

### 5.2 Runtime Environments

| Git branch | Frontend | Backend | Database |
|---|---|---|---|
| `main` | Vercel production | backend production | Neon `production` protected |
| `develop` | Vercel develop | backend develop | Neon `develop-anonymized` |
| `feature/*` | Vercel preview | backend preview | Neon ephemeral branch from `develop-anonymized` |

### 5.3 Why DB Preview Alone Is Not Enough

The frontend uses `NEXT_PUBLIC_API_BASE_URL`.

If every Vercel preview points to the same backend staging URL, all previews still share the same database. A per-feature database only becomes useful when the backend process for that feature is started with that feature's `DATABASE_URL`.

The implementation must therefore include backend preview deployment, not only Neon branch creation.

---

## 6. Data Security And Compliance

### 6.1 Production

Production is security-first:

- protected Neon branch.
- separate credentials.
- no feature or develop workflow can reset, delete, or migrate production directly.
- production migrations only run through the production deploy workflow.
- manual break-glass credentials kept outside normal CI where possible.

### 6.2 Develop Dataset

`develop-anonymized` must be long-lived and must contain:

- realistic schema.
- realistic but anonymized records.
- deterministic seed data where useful.
- no real user secrets.
- no OAuth tokens.
- no payment provider secrets.
- no real Candidate CV contents unless anonymized.
- no personal emails, names, phone numbers, addresses, or documents.

Recommended strategy:

1. maintain explicit anonymization SQL/scripts in git.
2. periodically refresh `develop-anonymized` from production only through that anonymization process.
3. treat Neon anonymized branches as a possible future acceleration, not the only compliance control while the feature is beta.

### 6.3 Preview Branches

Preview branches derive only from `develop-anonymized`.

They can contain:

- test Candidates.
- test BusinessAccounts.
- test JobPostings.
- test Applications.
- AIAnalysis data generated in preview.
- vector embeddings based on anonymized/test content.

They must not contain:

- production Candidate data.
- production BusinessAccount data.
- production OAuth tokens.
- production Stripe customer or subscription identifiers unless safely mocked/anonymized.

---

## 7. Backend Deployment Design

### 7.1 Current Production Deployment

Current production deployment runs after successful `Backend CI` on `main` and deploys through SSH + Docker Compose:

```text
Backend CI success on main
  -> deploy.yml
  -> SSH server
  -> write docker-compose.prod.yml and .env from GitHub secrets
  -> docker compose pull
  -> alembic upgrade head
  -> docker compose up -d
  -> /health smoke test
```

This path should remain separate from preview deployment.

### 7.2 Required Preview Deployment Shape

The preview deployer must be able to create or update a backend runtime per feature branch with:

- image tag or commit SHA.
- `APP_ENV=preview`.
- `DATABASE_URL` for the matching Neon branch.
- `DATABASE_URL_SYNC` if Alembic requires a sync URL later.
- `JWT_SECRET` preview value.
- CORS allowlist containing the Vercel preview URL or a safe preview domain pattern.
- OAuth callback settings disabled or explicitly preview-aware.
- object storage configuration for preview.
- Ollama/AI inference strategy for preview.
- observability configured as non-production.

### 7.3 Backend Preview Hosting Options

#### Option A — Existing VPS with Docker Compose per branch

Run feature backends on the existing deployment host, using one compose project per sanitized branch name.

Example project:

```text
jobai-preview-feature-job-109
```

Pros:

- reuses current SSH deployment model.
- no new platform needed.
- GitHub Actions can control lifecycle.

Cons:

- needs reverse proxy automation.
- needs port/domain allocation.
- previews can consume VPS CPU/RAM.
- cleanup must be reliable.

#### Option B — Fly.io / Render / Railway preview apps

Deploy one backend preview app per feature branch.

Pros:

- native preview-app style.
- easier public URLs.
- isolated compute.

Cons:

- introduces another platform.
- more secrets and billing.
- must validate Docker, migrations, and cleanup.

#### Option C — Single backend with dynamic DB routing

One backend instance chooses DB by request hostname/header.

Pros:

- fewer deployments.
- less infrastructure.

Cons:

- higher application risk.
- easy to leak data across tenants/environments.
- complicates dependency injection and connection pooling.
- not recommended for JobAI preview isolation.

Recommendation for POC: Option A if the current VPS has capacity, otherwise Option B. Do not use Option C.

---

## 8. Neon Integration Design

### 8.1 Integration Mode

Use manual GitHub Actions integration for backend-controlled CI/CD.

Reason:

- the frontend already uses explicit Vercel CLI deployments.
- the backend needs to create DB branches before migrations and backend preview deploy.
- `NEXT_PUBLIC_API_BASE_URL` must point to a backend URL, not directly to the database.
- manual actions give the clearest lifecycle control.

Vercel-Neon automatic integration can still be useful later for frontend-only projects, but it is not enough for this backend-centric review-app workflow.

### 8.2 Required GitHub Secrets And Variables

Secrets:

| Name | Scope | Purpose |
|---|---|---|
| `NEON_API_KEY` | GitHub Actions secret | Create/delete/reset branches |
| `PREVIEW_JWT_SECRET` | GitHub Actions secret | Backend preview JWT signing |
| `PREVIEW_DEPLOY_HOST` | GitHub Actions secret | Preview backend host if using SSH |
| `PREVIEW_DEPLOY_USER` | GitHub Actions secret | SSH user |
| `PREVIEW_DEPLOY_SSH_KEY` | GitHub Actions secret | SSH key |
| `PREVIEW_GHCR_TOKEN` | GitHub Actions secret | Pull backend image if required |
| `PREVIEW_ENV_BASE` | GitHub Actions secret | Non-sensitive preview env template if kept as secret |

Variables:

| Name | Scope | Purpose |
|---|---|---|
| `NEON_PROJECT_ID` | GitHub Actions variable | Neon project identifier |
| `NEON_PARENT_BRANCH` | GitHub Actions variable | Usually `develop-anonymized` |
| `PREVIEW_BACKEND_BASE_DOMAIN` | GitHub Actions variable | e.g. `preview-api.sovrum.dev` |
| `PREVIEW_CORS_BASE_DOMAIN` | GitHub Actions variable | e.g. `vercel.app` or custom preview domain |

### 8.3 Branch Naming

Branch names must be deterministic and sanitized:

```text
preview-${github.head_ref || github.ref_name}
```

Sanitization rules:

- lowercase.
- replace `/`, `_`, and unsupported characters with `-`.
- trim to Neon branch name length limits.
- append short SHA if collision risk exists.

Example:

```text
feature/job-109-linkedin-auth
-> preview-feature-job-109-linkedin-auth
```

### 8.4 Migration Flow

Every preview DB branch must run:

```bash
poetry run alembic upgrade head
```

This happens before backend preview exposure.

If migration fails:

- mark workflow failed.
- do not deploy or update backend preview.
- optionally delete the failed preview DB branch.
- post failure summary to the PR.

### 8.5 Schema Diff

Add a later quality gate:

- compare preview branch schema against `develop-anonymized`.
- post schema diff as PR comment.

This is useful for reviewing Alembic migrations before merge.

---

## 9. Frontend Integration

### 9.1 Required Contract

Frontend preview must receive:

```text
NEXT_PUBLIC_API_BASE_URL=https://<branch>.preview-api.sovrum.dev
```

The frontend workflow currently deploys preview branches independently. The backend preview URL must be available before or during the frontend deployment.

### 9.2 Coordination Options

#### Option A — Backend workflow comments URL, frontend remains manual

Backend creates preview URL and posts it to PR. Frontend preview points to shared staging until manually configured.

Not enough for target workflow.

#### Option B — Combined orchestration workflow

One GitHub workflow creates DB branch, deploys backend preview, injects or updates the frontend preview environment, then deploys frontend.

Best long-term but requires cross-repo coordination if frontend/backend are separate repositories.

#### Option C — Branch-specific Vercel environment variable

Backend workflow sets a branch-specific `NEXT_PUBLIC_API_BASE_URL` in Vercel before the frontend preview deploy runs.

Good fit if Vercel CLI/API can be called from GitHub Actions and branch-specific preview variables are acceptable.

Recommendation: Option C for POC if the frontend and backend repos are separate; Option B if they are in a monorepo or if a shared orchestration repo exists.

---

## 10. Backend Configuration Changes

The backend should standardize these environment variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `local`, `test`, `preview`, `develop`, `production` |
| `DATABASE_URL` | async SQLAlchemy URL for application runtime |
| `DATABASE_URL_SYNC` | sync URL for Alembic if needed |
| `DATABASE_URL_TEST` | test database URL |
| `CORS_ALLOW_ORIGINS` | comma-separated explicit origins |
| `CORS_ALLOW_ORIGIN_REGEX` | optional regex for controlled preview domains |
| `FRONTEND_ORIGIN` | default frontend origin for links/callbacks |
| `PUBLIC_API_BASE_URL` | backend public URL for callbacks and smoke tests |
| `OAUTH_REDIRECT_BASE_URL` | optional explicit auth callback base |
| `OBJECT_STORAGE_BUCKET` | bucket/prefix per environment |
| `LANGFUSE_HOST` | observability endpoint |

Current `.env.example` includes `DATABASE_URL`, `DATABASE_URL_TEST`, `FRONTEND_ORIGIN`, and `CORS_ALLOW_ORIGINS`. It should be extended during implementation.

---

## 11. CORS And Auth

### 11.1 CORS

Preview CORS should avoid a broad wildcard if cookies or credentials are used.

Preferred:

- explicit custom preview domain pattern, e.g. `https://*.preview.sovrum.dev`.
- branch-specific explicit origins where possible.

Acceptable for early preview:

- allow `https://*.vercel.app` only if no credentialed cookie session is used and risk is accepted.

If HTTP-only cookies are introduced:

- `Access-Control-Allow-Credentials=true`.
- exact origins, not wildcard.
- `SameSite=None`.
- `Secure=true`.
- cookie domain strategy documented per environment.

### 11.2 OAuth Callbacks

OAuth providers often require explicit callback URLs.

Options:

- disable OAuth login in ephemeral previews.
- use one stable callback domain per preview backend and route by state.
- only enable OAuth for `develop` and `production`.

Recommendation for POC: disable real OAuth callbacks in ephemeral previews unless a specific feature requires testing OAuth.

---

## 12. Object Storage And AI Dependencies

### 12.1 Object Storage

Database branching does not branch file/object storage.

If Candidate CVs or generated documents are stored in MinIO/S3, preview environments need:

- a preview bucket, or
- branch-specific object prefixes, or
- seeded fake files only.

Do not point previews at production object storage.

### 12.2 Ollama

Ollama local inference remains the backend AI provider.

For deployed previews:

- either use a shared non-production Ollama endpoint.
- or disable expensive AI flows unless needed.
- or use a preview AI worker with limited capacity.

No OpenAI/Anthropic API keys should be added.

### 12.3 Langfuse

Preview traces should be separated from production:

- separate Langfuse project, or
- environment tag `preview`, or
- disabled tracing for ephemeral previews.

---

## 13. Database Extension Compatibility

Neon supports PostgreSQL and `pgvector`, but the project also references `vectorscale` and `timescaledb`.

Before implementation, validate:

1. `CREATE EXTENSION IF NOT EXISTS vector;`
2. `CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;`
3. `CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;`
4. current Alembic migrations on a fresh Neon branch.
5. HNSW vector indexes.
6. existing AIAnalysis vector search behavior.

Current migration `2026_05_07_1643-aac3238ce036_create_vector_embeddings_tables_with_...` creates only `vector` directly, but local init creates `vectorscale` and `timescaledb`. If Neon does not support `vectorscale` or `timescaledb`, options are:

- keep only `pgvector` for Neon previews.
- remove hard dependency on `vectorscale` where not required.
- keep local TimescaleDB for local dev, Neon for preview/develop/prod with extension parity documented.
- choose a managed provider with required extension support if TimescaleDB-specific features become mandatory.

This is a blocking validation item.

---

## 14. CI/CD Workflow Proposal

### 14.1 Backend Preview Create/Update

Trigger:

```yaml
on:
  push:
    branches-ignore:
      - main
      - develop
```

High-level steps:

```text
checkout
install dependencies
run unit tests
build backend image
sanitize branch name
create or reset Neon branch from develop-anonymized
export DATABASE_URL
run alembic upgrade head against Neon branch
deploy backend preview using DATABASE_URL
run smoke test /health
publish backend preview URL
optionally update frontend Vercel branch-specific NEXT_PUBLIC_API_BASE_URL
```

### 14.2 Backend Develop Deploy

Trigger:

```yaml
on:
  push:
    branches:
      - develop
```

High-level steps:

```text
run Backend CI
deploy backend develop
run alembic upgrade head against Neon develop-anonymized
smoke test
```

Whether `develop-anonymized` is reset before deploy must be explicit and manual or scheduled, not automatic on every merge.

### 14.3 Backend Production Deploy

Production remains isolated:

```text
Backend CI success on main
deploy production
run Alembic once
smoke test
```

No preview branch action should have permission to mutate production.

### 14.4 Cleanup

Trigger:

```yaml
on:
  pull_request:
    types:
      - closed
```

High-level steps:

```text
sanitize branch name
delete backend preview deployment
delete Neon branch
delete branch-specific Vercel env var if created
post cleanup summary
```

Cleanup should also support `workflow_dispatch`.

---

## 15. Observability And Auditability

Each preview deploy should record:

- Git branch.
- commit SHA.
- Neon branch name.
- backend preview URL.
- frontend preview URL if available.
- migration revision before/after.
- cleanup status.

Minimum implementation:

- GitHub Actions summary.
- PR comment with URLs and DB branch.

Later:

- Notion/Linear update.
- deployment registry table.

---

## 16. Rollback Strategy

### Preview

Rollback means:

- redeploy previous commit to same preview branch, or
- delete/recreate the preview DB branch from `develop-anonymized`.

Operational preview reset flow:

```bash
gh workflow run backend-preview-cleanup.yml \
  --ref develop \
  -f mode=branch \
  -f branch="feature/<ticket>"

gh workflow run backend-preview.yml \
  --ref "feature/<ticket>"
```

The cleanup workflow refuses protected branches and non-`preview-*` Neon branches.

### Develop

Rollback options:

- redeploy previous backend image.
- restore/reset `develop-anonymized` from last known safe parent.
- rerun anonymized seed/import.

### Production

Production rollback must remain separate and should follow the production runbook. Neon point-in-time restore can be evaluated, but should not replace the current operational rollback plan until tested.

---

## 17. Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Production data leaks into previews | High | Use `develop-anonymized` as only preview parent |
| Neon lacks required extensions | High | Run extension POC before migration |
| Backend previews not implemented | High | Treat backend preview as required for DB isolation |
| Cleanup fails | Medium | Add scheduled janitor workflow and branch TTL |
| Preview costs grow | Medium | Delete branches on PR close, add TTL, monitor Neon usage |
| OAuth preview callbacks become unmanageable | Medium | Disable OAuth in ephemeral previews first |
| Object storage shared accidentally | High | Separate bucket/prefix per env |
| Vercel env coordination fails | Medium | Use deterministic backend preview URL per branch |
| Alembic migration breaks develop branch | Medium | Run migration on ephemeral branch first and schema diff |

---

## 18. Acceptance Criteria

The design was ready for implementation when:

- Neon extension compatibility was validated for current preview migrations.
- production/develop/preview branch hierarchy was approved.
- preview branches were constrained to `develop-anonymized`.
- backend preview hosting was selected as Vercel for the POC.
- required secrets and variables were listed and created.
- CORS/auth policy for previews was documented.
- cleanup policy was implemented with PR close, manual fallback, and TTL janitor.

The POC is successful and accepted because:

- pushing a feature branch creates a Neon preview branch from `develop-anonymized`.
- Alembic migrations run successfully on that branch.
- backend preview starts with that branch's `DATABASE_URL`.
- `/health` succeeds on the backend preview through protected Vercel access.
- cleanup workflow can remove matching preview backend deployments and Neon branches.
- Notion contains readable summaries and links back to Git docs.

---

## 19. Remaining Open Questions

Resolved during the cycle:

- Backend previews are hosted on Vercel for the POC.
- Preview DB branches are created on feature branch pushes by the backend preview workflow.
- Default TTL is `7` days unless `PREVIEW_TTL_DAYS` overrides it.
- Current preview migrations require `pgvector`, not `vectorscale` or `timescaledb`.

Still open for future cycles:

1. How should frontend previews consume the matching backend preview URL once JOB-126 is implemented?
2. What is the canonical refresh cadence and owner for `develop-anonymized`?
3. Should production eventually move to Neon, or should Neon remain preview/develop only?
4. Should preview object storage use isolated buckets or branch prefixes?
5. Should Vercel branch-specific environment variables be managed by backend CI or a cross-repo orchestration workflow?

---

## 20. References

- Final ADR: `docs/adr/adr-0006-neon-preview-database-branching.md`
- Preview runbook: `docs/deployment/neon-preview-environments-runbook.md`
- Backend Vercel preview runbook: `docs/deployment/backend-preview-vercel-runbook.md`
- Preview security ADR: `docs/adr/adr-0003-preview-security-policy.md`
- Backend preview ADR: `docs/adr/adr-0004-vercel-backend-preview-per-feature-branch.md`
- Cleanup safety ADR: `docs/adr/adr-0005-preview-cleanup-safety-policy.md`
- Neon GitHub Actions branching: https://neon.com/docs/guides/branching-github-actions
- Neon Vercel integration overview: https://neon.com/docs/guides/vercel/
- Neon database branching guide: https://neon.com/blog/practical-guide-to-database-branching
- Existing backend CI/CD ADR: `docs/architecture/adr-0001-ci-cd-hardening.md`
- Production runbook: `docs/deployment/production-runbook.md`

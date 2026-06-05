# ADR-0006 — Adopt Neon Preview Database Branching

**Status:** Accepted
**Date:** 2026-06-05
**Owner:** Forge
**Related tickets:** JOB-121, JOB-124, JOB-125, JOB-127, JOB-128, JOB-129

## Context

JobAI needs isolated review environments for feature branches. A frontend preview alone is not enough because backend
changes and database migrations must be tested against a matching non-production database.

The project evaluated Neon for preview database branching during the preview-environments cycle.

## Decision

Adopt Neon preview database branching for non-production feature previews.

The environment model is:

```text
main                    -> production runtime        -> protected production database
develop                 -> develop runtime           -> develop-anonymized database branch
feature/* or PR branch  -> Vercel backend preview    -> Neon preview branch from develop-anonymized
```

Preview branches are always derived from `develop-anonymized`, never directly from production.

GitHub Actions owns the lifecycle:

- create or reuse a deterministic Neon preview branch;
- run Alembic migrations on that branch;
- deploy the backend preview to Vercel with the branch `DATABASE_URL`;
- smoke test `/health` through protected Vercel preview access;
- cleanup on PR close, manual dispatch, and TTL janitor.

## POC Results

Validated:

- current Alembic migrations run against Neon preview branches;
- `pgvector` / `vector` extension supports current vector embedding tables and HNSW indexes;
- backend preview deploys to Vercel and boots with a Neon preview `DATABASE_URL`;
- protected `/health` smoke test passes via `npx vercel@latest curl`;
- cleanup can delete matching preview branches and safe preview deployments;
- workflows prevent production/develop cleanup targets.

Not adopted as Neon preview requirements:

- `vectorscale`;
- `timescaledb`.

Those extensions remain part of the local Docker stack unless a future POC proves hosted support and business need.

## Consequences

Positive:

- each feature branch can have an isolated preview database;
- Alembic failures are caught before reviewers use the backend preview;
- production data stays out of preview branches by using `develop-anonymized` as the parent;
- cleanup reduces branch sprawl and cost risk.

Trade-offs:

- preview database behavior is PostgreSQL + `pgvector`, not the full local TimescaleDB stack;
- Vercel backend previews use a reduced serverless runtime for the POC;
- `develop-anonymized` refresh remains a controlled process outside feature workflows;
- GitHub Actions secrets and variables are required for Neon and Vercel operations.

## Alternatives Considered

### Shared Develop Database

Rejected because concurrent feature branches could mutate the same database and hide migration conflicts.

### Local Docker Only

Rejected for remote review because reviewers need branch-specific environments without running local infrastructure.

### VPS Preview Databases

Deferred because no backend VPS is available for the POC, and the frontend already uses Vercel previews.

### Neon GitHub Integration Template Only

Not adopted as-is. The Neon GitHub integration is useful for provisioning `NEON_API_KEY` and `NEON_PROJECT_ID`, but the
project needs custom safety checks, Vercel backend deployment, protected smoke tests, and TTL cleanup.

## Follow-Ups

- Keep Git docs as source of truth and Notion as readable summary.
- Add frontend/backend URL coordination once JOB-126 is implemented.
- Define the long-term `develop-anonymized` refresh cadence and owner.
- Revisit production database provider separately; this ADR only adopts Neon preview branching.

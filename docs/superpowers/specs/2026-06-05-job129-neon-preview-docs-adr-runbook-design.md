# JOB-129 — Neon Preview Environments Docs, ADR, Runbook, And Rollback

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-129

## Goal

Finalize the preview-environments cycle by making Git docs the source of truth and publishing readable Notion summaries
that link back to Git.

## Scope

This ticket documents final decisions and operations after JOB-121, JOB-124, JOB-125, JOB-127, and JOB-128.

In scope:

- update the Neon technical spec with POC results;
- add the Neon preview branching ADR;
- add an operator runbook for manual branch creation, Alembic failures, health checks, CORS, cleanup, and rollback;
- update `.env.example` with preview workflow variables;
- update Notion Engineering and Design Specs summaries.

Out of scope:

- new runtime workflow changes;
- production migration to Neon;
- frontend/backend URL orchestration, which remains a future-cycle item.

## Final Documentation Set

| Purpose | Git document |
|---|---|
| Technical spec | `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md` |
| Implementation plan | `docs/superpowers/plans/2026-06-03-neon-preview-database-branching.md` |
| Operator runbook | `docs/deployment/neon-preview-environments-runbook.md` |
| Backend Vercel preview runbook | `docs/deployment/backend-preview-vercel-runbook.md` |
| Neon adoption ADR | `docs/adr/adr-0006-neon-preview-database-branching.md` |
| Security ADR | `docs/adr/adr-0003-preview-security-policy.md` |
| Backend preview ADR | `docs/adr/adr-0004-vercel-backend-preview-per-feature-branch.md` |
| Cleanup ADR | `docs/adr/adr-0005-preview-cleanup-safety-policy.md` |

## POC Results To Document

Validated:

- Neon preview branches can be created from `develop-anonymized`.
- Alembic migrations run against Neon preview branches.
- Current migrations require `pgvector` / `vector` and HNSW indexes.
- `vectorscale` and `timescaledb` are not required for current preview migrations.
- Vercel backend previews can boot with branch-specific Neon `DATABASE_URL`.
- Protected `/health` smoke tests pass through `vercel curl`.
- Cleanup works through PR close, manual dispatch, and TTL janitor.

## Acceptance Criteria Mapping

| Criterion | Delivery |
|---|---|
| Git docs remain source of truth | Git docs contain full spec, ADR, runbook, rollback, and env references |
| Notion has readable summary and links to Git | Engineering and Design Specs pages point back to Git paths |
| Future engineer can operate previews without workflow internals | Runbook includes manual branch creation, migration debug, health/CORS debug, cleanup, rollback |

## Validation

Documentation validation:

- Markdown files are committed in Git.
- `.env.example` contains preview variable names without real secret values.
- Notion pages contain summaries only and link back to Git docs.
- No real Neon/Vercel token or database password is committed.

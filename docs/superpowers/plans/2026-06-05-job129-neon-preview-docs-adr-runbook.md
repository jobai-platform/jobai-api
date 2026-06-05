# JOB-129 — Neon Preview Docs, ADR, Runbook Plan

**Status:** Implemented
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-129

## Objective

Close cycle 38 by documenting the final Neon preview environment model, decisions, operations, and rollback paths.

## Tasks

1. Retrieve JOB-129 and create the feature branch from `develop`.
2. Audit existing preview docs, ADRs, runbooks, `.env.example`, and Notion pages.
3. Update the Neon technical spec with final POC compatibility results.
4. Update the global implementation plan with final cycle status.
5. Add `docs/deployment/neon-preview-environments-runbook.md`.
6. Add `docs/adr/adr-0006-neon-preview-database-branching.md`.
7. Update `.env.example` with preview workflow variables.
8. Update Notion Engineering and Design Specs summaries with links back to Git docs.
9. Validate docs for secret leakage and broken obvious references.
10. Commit, push, and open a PR.

## Documentation Decisions

| Decision | Reason |
|---|---|
| Git remains source of truth | Avoid drift and preserve reviewable docs in PRs |
| Notion is summary-only | Useful for reading and stakeholder visibility without duplicating details |
| Runbook is separate from Vercel runbook | Operators need Neon branch, migration, cleanup, and rollback commands in one place |
| ADR separates preview adoption from production migration | Neon preview branching is accepted; production provider choice remains separate |

## Validation Commands

```bash
git diff --check
rg -n "np[g]_|na[p]i_|vercel_[A-Za-z0-9]|postgresql://[^[:space:]]*np[g]_" docs .env.example
```

## Completion Criteria

- JOB-129 docs are in Git.
- Notion summary is updated and links back to Git docs.
- No real secrets are committed.
- PR is created for review.

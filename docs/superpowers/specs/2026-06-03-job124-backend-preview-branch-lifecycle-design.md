# JOB-124 — Backend Preview Branch Lifecycle

**Status:** Draft  
**Ticket:** JOB-124  
**Owner:** Forge  
**Related spec:** `docs/superpowers/specs/2026-06-03-neon-preview-database-branching-design.md`

## Goal

Automate the Neon preview branch lifecycle for feature branches using the existing backend CI style:

- sanitize the Git branch name deterministically
- create or reuse a Neon branch derived from `develop-anonymized`
- export a secure `DATABASE_URL` for the preview branch
- run `poetry run alembic upgrade head`
- fail the workflow if migration fails
- write a GitHub Actions summary with the preview branch metadata

## Scope

This ticket focuses on the database branch lifecycle only.

It does not add backend deployment, frontend wiring, or cleanup automation.

## Decisions

- Use `npx neonctl` inside GitHub Actions rather than a custom HTTP client.
- Keep the branch naming deterministic so a feature branch maps to one preview DB branch.
- Derive preview branches only from `develop-anonymized`.
- Never allow the workflow to target production.
- Make migration failure block the workflow.

## Workflow shape

```text
push feature/*
  -> checkout
  -> install dependencies
  -> sanitize branch name
  -> create or reuse Neon branch from develop-anonymized
  -> export DATABASE_URL
  -> run alembic upgrade head
  -> write summary
```

## Acceptance criteria

- Feature branch push creates or reuses a Neon preview branch.
- The branch name is deterministic and safe for Neon.
- `DATABASE_URL` is available to the migration step without printing secrets.
- Alembic failure fails the workflow.
- The workflow cannot mutate production.


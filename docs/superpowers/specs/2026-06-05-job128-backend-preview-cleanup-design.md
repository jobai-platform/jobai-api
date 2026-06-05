# JOB-128 — Backend Preview Cleanup, TTL, And Cost Controls

**Status:** Draft for implementation
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-128
**Depends on:** JOB-124, JOB-125

## Goal

Automatically clean backend preview resources when a pull request is merged or closed, and provide a safe manual and
scheduled fallback for orphaned resources.

The cleanup flow must remove resources created by the preview pipeline without risking production, `develop`, or
`develop-anonymized` resources.

## Context

JOB-124 introduced deterministic Neon preview branch creation with `sanitize_branch_name()`.

JOB-125 introduced Vercel backend previews for feature branches. The backend preview deploy currently passes branch
runtime variables directly to `vercel deploy`; it does not persist branch-specific Vercel project environment variables.

JOB-128 closes the lifecycle by deleting stale preview resources.

## Resource Model

Each feature branch maps to a deterministic preview slug:

```text
feature/job-128-09-cicd-cleanup-preview-backend-neon-branch-and-branch
  -> preview-feature-job-128-09-cicd-cleanup-preview-backend-<hash>
```

Resources owned by this slug:

| Resource | Ownership Signal | Cleanup Strategy |
|---|---|---|
| Neon preview branch | branch name starts with `preview-` and matches sanitized feature branch | delete by Neon branch id |
| Vercel backend deployments | Vercel deployment `branch` or Git metadata matches feature branch | delete deployment ids through Vercel API |
| Branch-specific Vercel env vars | optional future env key + `gitBranch` metadata | delete only when explicitly configured |

## Safety Rules

Cleanup must refuse to delete:

- `main`
- `develop`
- `develop-anonymized`
- `production`
- `prod`
- any Neon branch not starting with `preview-`
- any Vercel deployment whose branch metadata points to a protected branch

Manual cleanup receives a raw Git branch name and derives the Neon preview branch with the same sanitizer as creation.

## Workflow Design

Add `.github/workflows/backend-preview-cleanup.yml`.

Triggers:

- `pull_request.closed`: cleanup the closed PR head branch.
- `workflow_dispatch`: cleanup one explicit branch safely.
- `schedule`: run TTL janitor for orphaned preview branches and stale deployments.

Modes:

| Mode | Input Source | Scope |
|---|---|---|
| PR close | `github.event.pull_request.head.ref` | one branch |
| Manual | `workflow_dispatch.inputs.branch` | one branch |
| Scheduled | `preview-*` resources older than TTL | orphan cleanup |

## Implementation Design

Add a small infrastructure CI helper:

```text
app/infrastructure/ci/backend_preview_cleanup.py
```

Responsibilities:

- reuse `sanitize_branch_name()` from `neon_branch_lifecycle.py`;
- validate cleanup targets before any destructive action;
- locate and delete a Neon preview branch;
- locate and delete Vercel deployments for a branch;
- optionally delete CI-managed branch-specific Vercel env vars;
- list stale preview resources for the TTL janitor;
- print GitHub Actions outputs and summary JSON without exposing secrets.

The helper uses only CI infrastructure concerns and stays outside domain/application layers.

## TTL Policy

Default TTL: `7` days.

The scheduled janitor deletes:

- Neon preview branches older than `PREVIEW_TTL_DAYS`;
- Vercel preview deployments older than `PREVIEW_TTL_DAYS` when their branch metadata is safe and non-protected.

If Vercel metadata is missing, the janitor skips the deployment rather than guessing.

## Acceptance Criteria Mapping

| Ticket Criterion | Implementation |
|---|---|
| Closed/merged PRs do not leave active preview DB branches | PR-close workflow deletes matching Neon preview branch |
| Orphaned previews are cleaned by TTL workflow | scheduled workflow deletes stale `preview-*` Neon branches and safe stale Vercel previews |
| Cleanup cannot delete production or `develop-anonymized` | helper rejects protected branch refs and non-`preview-*` Neon names |
| Manual cleanup can target one branch safely | workflow dispatch requires explicit branch and runs the same safety checks |

## Validation Strategy

Unit tests:

- safety rejects protected branch refs;
- cleanup target uses the same Neon sanitizer as creation;
- stale Neon branches are filtered by TTL and `preview-` prefix;
- Vercel deployments without safe branch metadata are skipped;
- cleanup summary does not include secrets.

Workflow validation:

- YAML parses;
- helper CLI supports `branch` and `janitor` modes;
- focused tests pass;
- ruff passes on touched files.

## Follow-Ups

- If JOB-126 adds frontend branch-specific env vars, reuse the optional env cleanup hook.
- If Vercel deploy metadata is insufficient for TTL deployment cleanup, add explicit CI metadata during deploy.
- Decide whether to add Slack or Linear notification when janitor deletes resources.

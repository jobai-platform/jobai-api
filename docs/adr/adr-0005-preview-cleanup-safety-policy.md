# ADR-0005 — Preview Cleanup Safety Policy

**Status:** Accepted
**Date:** 2026-06-05
**Owner:** Forge
**Related ticket:** JOB-128

## Context

Backend preview resources now include Neon preview branches and Vercel backend preview deployments. These resources are
temporary and should be removed after PR close, but cleanup is destructive and must not affect production, `develop`, or
`develop-anonymized`.

## Decision

Cleanup targets are derived from the raw Git feature branch and the existing Neon preview sanitizer. Manual cleanup does
not accept arbitrary Neon branch names or production-like refs as destructive targets.

The cleanup helper rejects:

- `main`
- `develop`
- `develop-anonymized`
- `production`
- `prod`
- Neon branch names that do not start with `preview-`

Scheduled TTL cleanup deletes Vercel deployments only when branch metadata is present and safe. Deployments without safe
branch metadata are skipped instead of being deleted by age alone.

## Consequences

- Closed PRs and manual cleanup can safely target one feature branch.
- Stale Neon preview branches can be deleted by TTL.
- Some Vercel deployments may require manual cleanup if Vercel does not expose branch metadata.
- The policy favors safety over aggressive cost cleanup.

## Follow-Ups

- Add explicit Vercel deployment metadata if the Vercel API does not reliably expose branch refs for CLI deployments.
- Revisit hard-delete Neon behavior only if soft-delete recovery windows create unacceptable cost pressure.

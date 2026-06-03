# ADR-0003: Preview Security Policy for CORS, OAuth, Cookies, Storage and AI

## Status

Accepted

## Context

JobAI now has a preview-oriented deployment model:

- frontend previews on Vercel
- backend preview deployments
- Neon preview databases derived from `develop-anonymized`

The remaining risk is not database branching itself. The risk is the surrounding runtime:

- browser auth across preview domains
- cookie behavior across sites
- accidental reads from production storage
- preview AI or tracing that can observe production data

## Decision

1. Ephemeral previews do not use real OAuth in the first iteration.
2. CORS uses an exact allowlist only.
3. HTTP-only cookies remain the default for `develop` and `production`.
4. Ephemeral previews must not depend on cross-site cookies as the primary login path.
5. Preview storage must use separate non-production credentials or buckets.
6. Preview AI must not point to production endpoints or production data.
7. Preview Langfuse is disabled by default.

## Consequences

Positive:

- preview environments stay auditable and easy to reason about
- production data leakage paths are reduced
- the auth model stays stable for develop and production

Negative:

- previews cannot exercise the full OAuth browser flow by default
- preview feature smoke tests may need a dedicated non-public auth path
- storage and AI previews need explicit environment wiring

## Follow-up work

- add the preview-specific config flags required by the policy
- add tests for the policy-sensitive code paths
- document the preview auth fallback for smoke tests if one is needed


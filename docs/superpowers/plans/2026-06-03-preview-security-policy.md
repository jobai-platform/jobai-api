# Preview Security Policy — Implementation Plan

**Ticket:** JOB-127  
**Status:** Draft  
**Owner:** Forge

## Objective

Turn the preview security policy into an explicit, testable backend contract for preview environments.

## What we are deciding

1. OAuth behavior in ephemeral previews
2. CORS allowlist strategy
3. HTTP-only cookie policy
4. Preview object storage isolation
5. Preview AI / Ollama behavior
6. Preview Langfuse behavior

## Decision summary

- Ephemeral previews do not use real OAuth in the first iteration.
- CORS remains an exact allowlist; no wildcard and no broad regex by default.
- Production and develop keep HTTP-only refresh cookies with secure settings.
- Previews must not rely on cross-site cookie auth as the primary login path.
- Preview storage must be isolated from production through separate buckets or credentials.
- Preview AI must never touch production data or production endpoints.
- Preview Langfuse is off by default.

## Implementation plan

### Phase 1 — Document the policy

- [ ] Publish the preview security policy in repo docs.
- [ ] Record the decision in Linear as a reference document.
- [ ] Add a short Notion entry under the backend architecture documentation.

### Phase 2 — Add explicit config surfaces

- [ ] Introduce preview-specific env vars only where they are needed to express the policy.
- [ ] Keep the CORS list exact and auditable.
- [ ] Make preview-specific enable/disable flags explicit rather than implicit.

### Phase 3 — Harden auth and browser behavior

- [ ] Ensure preview does not depend on real OAuth.
- [ ] Keep the existing cookie model for develop/production.
- [ ] Add tests for preview vs non-preview auth behavior once code changes land.

### Phase 4 — Lock down storage and AI dependencies

- [ ] Define separate preview storage credentials or buckets.
- [ ] Ensure preview AI configuration cannot resolve production endpoints.
- [ ] Keep Langfuse disabled unless a non-production project is explicitly configured.

### Phase 5 — Verification

- [ ] Add tests for CORS origin handling.
- [ ] Add tests for environment-specific cookie flags if the code changes.
- [ ] Add tests for storage/AI/Langfuse config defaults.

## Acceptance criteria

- Preview behavior is documented and unambiguous.
- Production data cannot leak into preview storage or preview AI.
- Browser auth behavior does not depend on fragile cross-site cookies in ephemeral previews.
- Preview CORS remains explicit and exact.

## Out of scope for this ticket

- full preview auth implementation
- preview object storage provisioning
- preview AI worker orchestration
- production bucket migration


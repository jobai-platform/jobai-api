# JOB-124 — Backend Preview Branch Lifecycle Plan

**Status:** Draft  
**Owner:** Forge

## Execution plan

### 1. Document the workflow

- [ ] Record the preview branch lifecycle rules.
- [ ] Cross-link the existing Neon preview branching spec.
- [ ] Publish the ticket context in Notion and Linear.

### 2. Implement the CI helper

- [ ] Add a small CI helper module for deterministic branch sanitization.
- [ ] Add Neon branch creation/reuse logic through `npx neonctl`.
- [ ] Export the preview `DATABASE_URL` into the GitHub Actions environment.

### 3. Add the workflow

- [ ] Create `.github/workflows/backend-preview.yml`.
- [ ] Trigger on feature branch pushes only.
- [ ] Run branch creation/reuse before Alembic.
- [ ] Fail the workflow when migration fails.
- [ ] Write a summary with branch metadata and migration result.

### 4. Verify

- [ ] Unit test the branch-name sanitizer.
- [ ] Unit test async URL conversion from Neon connection strings.
- [ ] Validate the workflow file against the repo CI conventions.

## Acceptance criteria

- The workflow matches the backend CI style already used in this repo.
- Preview DB lifecycle is deterministic and reusable.
- The migration gate blocks bad preview branches before any later deploy step.


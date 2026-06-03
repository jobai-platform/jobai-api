# Preview Security Policy — CORS, OAuth, Cookies, Object Storage, AI

**Ticket:** JOB-127  
**Status:** Draft  
**Owner:** Forge  
**Scope:** Backend preview environments for JobAI / Sovrum

## Goal

Define the security posture for preview environments before the backend preview is exposed broadly.
The objective is to keep previews isolated from production data, minimize surprise browser behavior,
and keep the preview stack operational without opening unsafe shortcuts.

## Current state

The backend already has:

- strict CORS allowlist from `CORS_ALLOW_ORIGINS`
- `APP_ENV` support for `dev`, `preview`, `develop`, `production`
- HTTP-only refresh cookie handling in auth routes
- `S3_*` configuration for object storage
- local Ollama and optional Langfuse configuration

The current implementation is intentionally permissive in a few places because the preview policy
had not yet been defined:

- refresh cookies are always written with `Secure=true` and `SameSite=Lax`
- CORS uses exact origins only, not regex
- LinkedIn OAuth is implemented for non-preview environments
- object storage is not environment-isolated yet by policy
- AI and tracing have no preview-specific guardrail yet

## Decisions

### 1. OAuth in ephemeral previews

Real OAuth is disabled in ephemeral feature previews for the first iteration.

Rationale:

- preview URLs are ephemeral and unstable
- OAuth callback registration becomes noisy and easy to leak
- browser-based auth flows add complexity before the preview security policy is stable
- the first priority is to validate preview environment wiring, not social login edge cases

Allowed environments:

- `develop`: real OAuth enabled
- `production`: real OAuth enabled
- `preview`: real OAuth disabled unless a ticket explicitly re-enables it for a controlled test
- `dev`: local helper flows may remain available

### 2. CORS

Use an exact allowlist only.

Policy:

- no wildcard origins
- no broad regex matching as the default policy
- every preview deployment must know its frontend origin explicitly
- `allow_credentials=true` remains enabled only when the exact origin is trusted

Rationale:

- credentials and wildcard CORS are a bad combination
- exact allowlists are easy to audit and easier to revoke
- the current code already validates exact origins, which matches the policy

Operational rule:

- the CI/CD pipeline must inject the preview frontend origin explicitly into the backend preview
- `develop` and `production` keep static exact origins

### 3. Cookies and preview browser sessions

HTTP-only cookies remain the default for `develop` and `production`.

Cookie policy:

- `HttpOnly=true`
- `Secure=true`
- `SameSite=Lax` for same-site environments
- host-only cookie domain unless a future ticket requires a stricter domain policy
- `Path=/`

Preview policy:

- ephemeral previews must not depend on browser cookie auth as the primary login path
- real OAuth is off, so preview browser sessions should not need a LinkedIn round trip
- if a preview needs auth for a controlled smoke test, use a preview-specific non-public mechanism
  rather than changing the production cookie model

Rationale:

- cross-site preview frontends are fragile with third-party cookies
- browser cookie behavior varies across environments and blockers
- we should not design the preview experience around a weak auth path

### 4. Object storage

Preview storage must never read from production storage.

Policy:

- production gets its own bucket and credentials
- `develop` gets its own bucket or namespace
- previews use a non-production bucket or a distinct account with branch-scoped prefixes
- preview cleanup must delete preview objects when the preview branch is removed

Recommended first iteration:

- separate bucket per environment family
- branch prefix inside the preview bucket, e.g. `preview/<branch-name>/...`

Rationale:

- prefixing alone is not enough if credentials are too broad
- production leakage must be impossible by configuration
- cleanup is simpler when preview objects are namespaced

### 5. AI and Ollama behavior

Preview AI is allowed only against non-production data.

Policy:

- previews use either a shared non-production Ollama endpoint or disable expensive AI flows by default
- no preview path may call a production AI endpoint
- preview AI should not be able to read production embeddings or production job/candidate data

Recommended first iteration:

- keep AI turned on only when the preview backend is pointed at anonymized preview data
- use a shared non-production Ollama endpoint for preview workloads
- keep expensive or long-running generation paths behind an explicit flag if needed

Rationale:

- the preview stack already exists to test product behavior against synthetic/anonymized data
- AI infrastructure should not be a path back to production data

### 6. Langfuse

Preview tracing is disabled by default.

Policy:

- `develop` may use a separate non-production Langfuse project if observability is required
- ephemeral previews default to no tracing
- if tracing is enabled in preview, it must be a preview-only project or a clearly tagged namespace

Rationale:

- trace payloads can contain sensitive prompts, tokens, and identifiers
- disabled by default is the safest baseline

## Required environment variables

The implementation will likely need a few explicit env vars to express this policy cleanly:

- `APP_ENV`
- `CORS_ALLOW_ORIGINS`
- `FRONTEND_ORIGIN`
- `PUBLIC_API_BASE_URL`
- `ENABLE_OAUTH_PREVIEW` or equivalent guard
- `S3_BUCKET_CVS` plus preview-specific bucket/prefix variables
- `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `OLLAMA_BASE_URL`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`

## Validation approach

Policy validation should be covered with tests where code changes land:

- CORS preflight against exact preview origins
- auth route behavior when preview OAuth is disabled
- cookie flags for non-preview environments
- storage configuration tests ensuring preview cannot point at production buckets
- Langfuse disabled-by-default behavior when keys are absent

## Open questions

- Do we want a dedicated preview auth helper route for smoke tests?
- Do we want preview storage to use separate buckets or a single bucket with strict branch prefixes plus distinct credentials?
- Do we want preview AI to be disabled by default or enabled against shared non-production Ollama?


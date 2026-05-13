# CLAUDE.md — JobAI Plateforme
# Hexagonal Architecture · DDD · TDD First · FastAPI · Python 3.13

## Commands

```bash
# Install dependencies
poetry install

# Start dev environment (PostgreSQL + app)
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
poetry run alembic upgrade head

# Start dev server (hot reload)
poetry run uvicorn app.main:app --reload

# Run all tests
poetry run pytest -q

# Run by layer
poetry run pytest tests/domain/ -q
poetry run pytest tests/application/ -q
poetry run pytest tests/infrastructure/ -q
poetry run pytest tests/presentation/ -q

# Run a single test file
poetry run pytest tests/application/billing/test_use_cases.py -v

# Run a single test by name
poetry run pytest tests/domain/billing/test_subscription_domain.py::test_name -v

# Lint / format
poetry run ruff check .
poetry run black .
poetry run mypy .
```

---

## 🤖 Ollama — Local AI Inference

### Starting with Docker (recommended)

```bash
# Start all services including Ollama
docker-compose -f docker-compose.dev.yml up -d

# Wait for Ollama to be ready (~30s)
docker-compose -f docker-compose.dev.yml ps

# Download required models (one time, ~4.4 GB)
./scripts/ollama-pull-models.sh
```

### Local development without Docker

```bash
# Install Ollama: https://ollama.com
brew install ollama          # macOS

# Start the server
ollama serve

# Download the models
ollama pull nomic-embed-text   # embeddings (274 MB)
ollama pull mistral:7b         # LLM FAST tier (4.1 GB)
```

### Models used

| Model | Usage | Size | Tier |
|---|---|---|---|
| `nomic-embed-text` | Vector embeddings | 274 MB | all |
| `mistral:7b` | LLM completions | 4.1 GB | FAST |
| `mistral-nemo:12b` | LLM completions | 7.1 GB | BALANCED (optional) |

### Key environment variables

| Variable | Local default | Docker value |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` |
| `OLLAMA_LLM_MODEL` | `mistral:7b` | `mistral:7b` |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | `nomic-embed-text` |
| `OLLAMA_TIMEOUT` | `120.0` | `120.0` |

### Verify Ollama is working

```bash
# Health check
curl http://localhost:11434/api/tags

# Quick embedding test
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "hello world"}'

# Quick LLM test
curl http://localhost:11434/api/generate \
  -d '{"model": "mistral:7b", "prompt": "Say hello", "stream": false}'
```

---

## 🧱 Architecture — Hexagonal (Ports & Adapters) + DDD

Strict layer separation. **Never import across layers in the wrong direction.**

```
app/
├── domain/          # Pure business logic — ZERO framework imports
│   ├── users/
│   ├── billing/
│   └── common/      # Shared value objects (Email, Money, etc.)
│
├── application/     # Use cases + ports (abstract interfaces)
│   ├── users/
│   ├── auth/
│   └── billing/
│
├── infrastructure/  # Concrete implementations of ports
│   ├── persistence/
│   │   ├── models/       # SQLAlchemy ORM models (infra only)
│   │   └── repositories/ # Implements app ports
│   ├── billing/
│   │   └── stripe/       # Stripe gateway
│   └── security/         # JWT, hashing
│
└── presentation/    # FastAPI routes, Pydantic DTOs, mappers
    └── api/v1/
```

### Layer Rules (STRICT)

| Layer | Can import | Cannot import |
|---|---|---|
| `domain/` | stdlib only | SQLAlchemy, FastAPI, Pydantic, anything infra |
| `application/` | `domain/` | SQLAlchemy, FastAPI, infrastructure |
| `infrastructure/` | `domain/`, `application/`, SQLAlchemy, Stripe... | `presentation/` |
| `presentation/` | `application/`, Pydantic, FastAPI | `infrastructure/` directly |

### Adding a New Bounded Context

1. `app/domain/<context>/` — entities, value objects, domain services
2. `app/application/<context>/ports.py` — abstract interfaces (ABC or Protocol)
3. `app/application/<context>/use_cases.py` — orchestration only
4. `app/infrastructure/persistence/models/<context>.py` — ORM model
5. `app/infrastructure/persistence/repositories/<context>_sqlalchemy.py` — implements port
6. `app/presentation/api/v1/<context>_routes.py` — FastAPI router (zero business logic)
7. Wire DI in `app/core/dependency.py`

---

## 🧩 DDD — Ubiquitous Language should reflect the domain language. For JobAI

Always use these exact terms in code, tests, and comments:

| Term | Definition |
|---|---|
| `Candidate` | Job seeker (user looking for employment) |
| `JobPosting` | Job offer published by a BusinessAccount |
| `Application` | A Candidate's submission to a JobPosting |
| `SearchAgent` | Autonomous AI agent that searches jobs on behalf of a Candidate |
| `BusinessAccount` | Company connected to the platform |
| `SkillMatch` | AI-computed compatibility score between a profile and a JobPosting |
| `AIAnalysis` | AI-generated content (summary, rewrite, matching, scoring) |
| `Review / Rating` | Feedback retrieved via Google My Business |
| `Subscription` | Billing plan for Candidate or BusinessAccount |

### Bounded Contexts

- **Users / Auth** — registration, login, JWT, OAuth Google
- **Job Search** — JobPosting, Application, SearchAgent
- **AI Analysis** — LLMs, matching, RAG, MCP, rewriting, scoring (LangChain, Pinecone)
- **Businesses / Integrations** — Google My Business, Stripe billing

---

## 🧪 TDD — Test First (MANDATORY)

**Never write implementation before tests.**

Order: `tests/domain/` → `tests/application/` → `tests/infrastructure/` → `tests/presentation/`

### Test Structure

```
tests/
├── domain/          # Pure unit tests — no DB, no mocks of framework
├── application/     # Use case tests — use Fakes from tests/fakes/
├── infrastructure/  # Integration tests — real DB (auto-rollback)
├── presentation/    # E2E route tests — AsyncClient + DB session override
└── fakes/           # In-memory repositories (InMemoryUserRepo, etc.)
```

### Fixtures (conftest.py)

- `db_session` — transaction-scoped, auto-rolled-back after each test
- `client` — FastAPI `AsyncClient` with `get_async_session` overridden
- `create_user_in_db` — factory for seeding test users

Use `pytest-asyncio` with `asyncio_mode = "strict"`.

### Test Naming Convention

```python
# Domain tests — pure, no mocks
def test_candidate_raises_when_email_invalid(): ...
def test_skill_match_score_is_between_0_and_1(): ...

# Application tests — use Fakes
async def test_create_candidate_use_case_returns_candidate_entity(): ...
async def test_create_candidate_raises_conflict_when_email_exists(): ...

# Presentation tests — use client fixture
async def test_post_candidates_returns_201_with_valid_payload(): ...
async def test_post_candidates_returns_422_with_missing_email(): ...
```

---

## 🧠 Domain Layer Patterns

```python
# Entity — mutable, has identity
@dataclass(slots=True)
class Candidate:
    id: UUID
    email: Email
    full_name: str
    is_active: bool = True

# Value Object — immutable, no identity
@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")
```

**Domain rules:**
- Entities use `@dataclass(slots=True)` — mutable
- Value Objects use `@dataclass(frozen=True, slots=True)` — immutable
- Domain services hold cross-cutting rules (e.g., `SoftDeleteService`)
- Domain raises `ValueError` / custom domain exceptions — never HTTP exceptions
- Zero imports from SQLAlchemy, Pydantic, FastAPI

---

## ⚙️ Application Layer Patterns

```python
# Port (interface) — defined in application, implemented in infra
class CandidateRepository(ABC):
    @abstractmethod
    async def save(self, candidate: Candidate) -> None: ...

    @abstractmethod
    async def find_by_email(self, email: Email) -> Candidate | None: ...

# Use Case
class CreateCandidateUseCase:
    def __init__(self, repo: CandidateRepository) -> None:
        self._repo = repo

    async def execute(self, command: CreateCandidateCommand) -> Candidate:
        existing = await self._repo.find_by_email(Email(command.email))
        if existing:
            raise ConflictError("Email already registered")
        candidate = Candidate(id=uuid4(), email=Email(command.email), ...)
        await self._repo.save(candidate)
        return candidate
```

**Application rules:**
- Use cases raise `AppError` subclasses (`NotFoundError`, `ConflictError`, etc.)
- Never import infrastructure directly
- One use case = one class = one file

---

## 🗄️ Infrastructure Layer Patterns

```python
# ORM Model (infra only — never imported in domain or application)
class CandidateModel(Base):
    __tablename__ = "candidates"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)

# Repository — implements application port
class SQLAlchemyCandidateRepository(CandidateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, candidate: Candidate) -> None:
        model = _to_model(candidate)
        self._session.add(model)

def _to_domain(model: CandidateModel) -> Candidate:
    return Candidate(id=model.id, email=Email(model.email), ...)

def _to_model(candidate: Candidate) -> CandidateModel:
    return CandidateModel(id=candidate.id, email=candidate.email.value, ...)
```

---

## 🌐 Presentation Layer Patterns

```python
# DTO — Pydantic v2, presentation layer only
class CreateCandidateRequest(BaseModel):
    email: EmailStr
    full_name: str

class CandidateResponse(BaseModel):
    id: UUID
    email: str
    full_name: str

# Route — zero business logic
@router.post("/candidates", response_model=CandidateResponse, status_code=201)
async def create_candidate(
    body: CreateCandidateRequest,
    use_case: Annotated[CreateCandidateUseCase, Depends(get_create_candidate_use_case)],
) -> CandidateResponse:
    candidate = await use_case.execute(CreateCandidateCommand(**body.model_dump()))
    return map_to_response(candidate)
```

**Error mapping:** `exception_handlers.py` converts `AppError` → `{"code": "...", "detail": "..."}` HTTP responses.

---

## 💉 Dependency Injection

All factories in `app/core/dependency.py`. Services constructed per-request via `Annotated[T, Depends(...)]`.

```python
async def get_create_candidate_use_case(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CreateCandidateUseCase:
    repo = SQLAlchemyCandidateRepository(session)
    return CreateCandidateUseCase(repo)
```

Tests override `get_async_session` to inject a transaction-scoped test session.

---

## 🔑 Key Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL (psycopg, sync — Alembic) |
| `DATABASE_URL_TEST` | PostgreSQL (asyncpg, test suite) |
| `JWT_SECRET` | Token signing |
| `STRIPE_SECRET` | Stripe API key |
| `OPENAI_API_KEY` | AI features (LangChain) |

---

## 🧼 Quality Rules (KISS · DRY · SOLID · YAGNI)

- **KISS** — simplest solution that passes the tests
- **DRY** — shared logic lives in domain or application, never duplicated in routes
- **SOLID** — ports = interfaces; depend on abstractions, not concretions
- **YAGNI** — don't implement what isn't needed for the current ticket

**Red flags to avoid:**
- Business logic inside FastAPI routes
- SQLAlchemy models imported in `domain/` or `application/`
- HTTP status codes raised inside use cases
- Mocks instead of Fakes for domain/application tests
- God classes / use cases doing more than one thing

---

## 📋 Code Style

- Line length: **120 characters** (black + ruff + isort)
- Python **3.13** minimum; type hints required everywhere
- Ruff: ALL rules enabled except `D` (docstrings) and `ANN101`/`ANN102`
- `@dataclass(slots=True)` for entities
- `@dataclass(frozen=True, slots=True)` for value objects

# JOB-36 — TimescaleDB + pgvectorscale: Migrations & VectorStorePort

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup vector storage infrastructure using TimescaleDB + pgvectorscale — replace the existing `postgres:17` container, create the 3 Alembic migrations (`ai_analyses`, `candidate_embeddings`, `job_embeddings`), implement `VectorStorePort` ABC and its `TimescaleVectorStoreAdapter`.

**Architecture:** The existing hexagonal structure is extended: the port lives in `app/application/ai_analysis/ports.py`, the adapter in `app/infrastructure/ai/timescale_vector_store.py`. The three migrations are standalone and chain off the latest existing revision. The `docker-compose.dev.yml` is updated to swap `postgres:17-alpine` for `timescale/timescaledb-ha:pg16` (which bundles pgvector + pgvectorscale) and adds the extension-enable SQL init script.

**Tech Stack:** TimescaleDB-HA pg16, pgvector 0.7+, pgvectorscale, SQLAlchemy 2 (async), Alembic, `pgvector` Python package, pytest-asyncio (strict mode)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `docker-compose.dev.yml` | Swap DB image, add init SQL volume |
| Create | `scripts/init-extensions.sql` | `CREATE EXTENSION` statements run at container first boot |
| Create | `app/application/ai_analysis/__init__.py` | Package marker |
| Create | `app/application/ai_analysis/ports.py` | `VectorStorePort` ABC + `SimilarityResult` VO |
| Create | `app/infrastructure/persistence/models/ai_analysis.py` | SQLAlchemy ORM model for `ai_analyses` |
| Create | `app/infrastructure/persistence/models/candidate_embedding.py` | ORM model for `candidate_embeddings` |
| Create | `app/infrastructure/persistence/models/job_embedding.py` | ORM model for `job_embeddings` |
| Create | `app/infrastructure/ai/__init__.py` | Package marker |
| Create | `app/infrastructure/ai/timescale_vector_store.py` | Implements `VectorStorePort` |
| Create | `migrations/versions/YYYYMMDD-<rev>_enable_vector_extensions.py` | Migration 1: enable pgvector + pgvectorscale |
| Create | `migrations/versions/YYYYMMDD-<rev>_create_ai_analyses_table.py` | Migration 2: `ai_analyses` table |
| Create | `migrations/versions/YYYYMMDD-<rev>_create_embedding_tables.py` | Migration 3: `candidate_embeddings` + `job_embeddings` + HNSW indexes |
| Create | `tests/fakes/ai_analysis/__init__.py` | Package marker |
| Create | `tests/fakes/ai_analysis/fake_vector_store_port.py` | In-memory `VectorStorePort` for unit tests |
| Create | `tests/infrastructure/ai_analysis/__init__.py` | Package marker |
| Create | `tests/infrastructure/ai_analysis/test_timescale_vector_store.py` | Integration tests (requires running TimescaleDB) |

---

## Task 1: Swap Docker DB image + enable extensions at boot

**Concept:** `timescale/timescaledb-ha:pg16` est une image Timescale qui inclut PostgreSQL 16, TimescaleDB, pgvector et pgvectorscale préinstallés. Le dossier `/docker-entrypoint-initdb.d/` est exécuté automatiquement au **premier démarrage** du container (quand le volume est vide). On y monte un script SQL qui active les extensions.

**Files:**
- Modify: `docker-compose.dev.yml`
- Create: `scripts/init-extensions.sql`

- [ ] **Step 1.1: Créer le script SQL d'initialisation des extensions**

```sql
-- scripts/init-extensions.sql
-- Ce script est exécuté une seule fois au premier démarrage du container.
-- Il active les extensions nécessaires dans la base jobai_db.
\c jobai_db;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

- [ ] **Step 1.2: Mettre à jour docker-compose.dev.yml**

Remplace le bloc `db:` entier par :

```yaml
  db:
    image: timescale/timescaledb-ha:pg16
    restart: unless-stopped
    container_name: timescaledb-container-dev
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: jobai_db
      TIMESCALEDB_TELEMETRY: "off"
    ports:
      - ${POSTGRES_PORT:-5432}:5432
    networks:
      - postgres
    volumes:
      - timescale-data:/var/lib/postgresql/data
      - ./scripts/init-extensions.sql:/docker-entrypoint-initdb.d/init-extensions.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d jobai_db"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Et dans la section `volumes:` en bas du fichier, remplace `postgres-data:` par `timescale-data:` :

```yaml
volumes:
  timescale-data:
  minio-data:
```

- [ ] **Step 1.3: Supprimer l'ancien volume Docker et redémarrer**

> ⚠️ Cette commande supprime toutes les données locales de dev. C'est intentionnel — le changement d'image implique un format de données incompatible.

```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d db
```

- [ ] **Step 1.4: Vérifier que les extensions sont actives**

```bash
docker exec timescaledb-container-dev psql -U postgres -d jobai_db -c "\dx"
```

Attendu dans la liste : `vector`, `vectorscale`, `timescaledb`.

- [ ] **Step 1.5: Commit**

```bash
git add docker-compose.dev.yml scripts/init-extensions.sql
git commit -m "infra: swap postgres:17 for timescaledb-ha:pg16 with pgvector + pgvectorscale"
```

---

## Task 2: Ajouter la dépendance Python `pgvector`

**Concept:** Le package Python `pgvector` expose le type `Vector` pour SQLAlchemy et permet d'utiliser les opérateurs de distance (`<->`, `<=>`, `<#>`) dans les requêtes ORM.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 2.1: Ajouter pgvector aux dépendances**

```bash
poetry add pgvector
```

- [ ] **Step 2.2: Vérifier l'installation**

```bash
poetry run python -c "from pgvector.sqlalchemy import Vector; print('pgvector OK')"
```

Attendu : `pgvector OK`

- [ ] **Step 2.3: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "deps: add pgvector Python package for vector column type"
```

---

## Task 3: `VectorStorePort` ABC + `SimilarityResult` VO (application layer)

**Concept:** Le port est une interface abstraite (ABC) définie dans la couche application. Il ne contient aucune dépendance vers SQLAlchemy ou TimescaleDB — seulement des types Python purs. `SimilarityResult` est un value object qui encapsule le résultat d'une recherche de similarité.

**Files:**
- Create: `app/application/ai_analysis/__init__.py`
- Create: `app/application/ai_analysis/ports.py`

- [ ] **Step 3.1: Créer `app/application/ai_analysis/__init__.py`**

```python
```
(fichier vide)

- [ ] **Step 3.2: Écrire le test qui force la définition du port**

```python
# tests/application/ai_analysis/test_vector_store_port.py
from uuid import UUID
from app.application.ai_analysis.ports import VectorStorePort, SimilarityResult


def test_similarity_result_is_value_object():
    result = SimilarityResult(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        score=0.92,
        metadata={"job_id": "abc"},
    )
    assert result.score == 0.92
    assert result.id == UUID("00000000-0000-0000-0000-000000000001")


def test_similarity_result_immutable():
    result = SimilarityResult(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        score=0.5,
        metadata={},
    )
    try:
        result.score = 0.9  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass


def test_vector_store_port_is_abstract():
    import inspect
    assert inspect.isabstract(VectorStorePort)
```

- [ ] **Step 3.3: Lancer le test pour vérifier qu'il échoue**

```bash
poetry run pytest tests/application/ai_analysis/test_vector_store_port.py -v
```

Attendu : `ImportError` ou `ModuleNotFoundError` — le module n'existe pas encore.

- [ ] **Step 3.4: Implémenter `app/application/ai_analysis/ports.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    id: UUID
    score: float
    metadata: dict


class VectorStorePort(ABC):
    @abstractmethod
    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None: ...

    @abstractmethod
    async def search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[SimilarityResult]: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
```

- [ ] **Step 3.5: Créer le `__init__.py` du package de tests**

```bash
touch tests/application/ai_analysis/__init__.py
```

- [ ] **Step 3.6: Lancer les tests**

```bash
poetry run pytest tests/application/ai_analysis/test_vector_store_port.py -v
```

Attendu : 3 tests PASSED.

- [ ] **Step 3.7: Commit**

```bash
git add app/application/ai_analysis/ tests/application/ai_analysis/
git commit -m "feat(ai-analysis): add VectorStorePort ABC and SimilarityResult VO"
```

---

## Task 4: Fake `VectorStorePort` pour les tests applicatifs

**Concept:** Un Fake est une implémentation en mémoire d'un port, utilisée dans les tests de la couche application à la place du vrai adapter (qui nécessiterait une DB). Il doit se comporter exactement comme le vrai — pas de `unittest.mock`.

**Files:**
- Create: `tests/fakes/ai_analysis/__init__.py`
- Create: `tests/fakes/ai_analysis/fake_vector_store_port.py`

- [ ] **Step 4.1: Écrire le test du fake (le fake doit lui-même être testable)**

```python
# tests/fakes/ai_analysis/test_fake_vector_store_port.py
import pytest
from uuid import UUID
from tests.fakes.ai_analysis.fake_vector_store_port import FakeVectorStorePort


@pytest.mark.asyncio
async def test_fake_upsert_and_search():
    store = FakeVectorStorePort()
    vec = [0.1] * 768
    uid = UUID("00000000-0000-0000-0000-000000000001")
    await store.upsert(uid, vec, {"type": "candidate"})
    results = await store.search(vec, top_k=5)
    assert len(results) == 1
    assert results[0].id == uid


@pytest.mark.asyncio
async def test_fake_delete_removes_entry():
    store = FakeVectorStorePort()
    vec = [0.5] * 768
    uid = UUID("00000000-0000-0000-0000-000000000002")
    await store.upsert(uid, vec, {})
    await store.delete(uid)
    results = await store.search(vec, top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_fake_search_returns_top_k():
    store = FakeVectorStorePort()
    for i in range(10):
        uid = UUID(f"00000000-0000-0000-0000-{i:012d}")
        await store.upsert(uid, [float(i) / 10] * 768, {})
    results = await store.search([0.5] * 768, top_k=3)
    assert len(results) == 3
```

- [ ] **Step 4.2: Lancer le test pour vérifier qu'il échoue**

```bash
poetry run pytest tests/fakes/ai_analysis/test_fake_vector_store_port.py -v
```

Attendu : `ImportError`.

- [ ] **Step 4.3: Créer les `__init__.py`**

```bash
touch tests/fakes/ai_analysis/__init__.py
touch tests/fakes/ai_analysis/test_fake_vector_store_port.py  # déjà créé à l'étape 4.1
```

- [ ] **Step 4.4: Implémenter `tests/fakes/ai_analysis/fake_vector_store_port.py`**

```python
import math
from uuid import UUID

from app.application.ai_analysis.ports import SimilarityResult, VectorStorePort


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class FakeVectorStorePort(VectorStorePort):
    def __init__(self) -> None:
        self._store: dict[UUID, tuple[list[float], dict]] = {}

    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None:
        self._store[id] = (vector, metadata)

    async def search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        scored = [
            SimilarityResult(id=uid, score=_cosine_similarity(vector, vec), metadata=meta)
            for uid, (vec, meta) in self._store.items()
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    async def delete(self, id: UUID) -> None:
        self._store.pop(id, None)
```

- [ ] **Step 4.5: Lancer les tests**

```bash
poetry run pytest tests/fakes/ai_analysis/ -v
```

Attendu : 3 tests PASSED.

- [ ] **Step 4.6: Commit**

```bash
git add tests/fakes/ai_analysis/
git commit -m "test(ai-analysis): add FakeVectorStorePort with cosine similarity"
```

---

## Task 5: ORM models — `ai_analyses`, `candidate_embeddings`, `job_embeddings`

**Concept:** Les ORM models restent dans la couche infrastructure (`app/infrastructure/persistence/models/`). Ils sont découverts automatiquement par Alembic via `import_all_models()` dans `migrations/env.py`. Le type `Vector` vient de `pgvector.sqlalchemy`.

**Files:**
- Create: `app/infrastructure/persistence/models/ai_analysis.py`
- Create: `app/infrastructure/persistence/models/candidate_embedding.py`
- Create: `app/infrastructure/persistence/models/job_embedding.py`

- [ ] **Step 5.1: Créer `app/infrastructure/persistence/models/ai_analysis.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class AIAnalysisModel(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_posting_id", name="uq_ai_analyses_candidate_job"),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    quality_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="balanced")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skills_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 5.2: Créer `app/infrastructure/persistence/models/candidate_embedding.py`**

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class CandidateEmbeddingModel(Base):
    __tablename__ = "candidate_embeddings"
    __table_args__ = (
        Index(
            "ix_candidate_embeddings_vector_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vector: Mapped[list] = mapped_column(Vector(768), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

- [ ] **Step 5.3: Créer `app/infrastructure/persistence/models/job_embedding.py`**

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class JobEmbeddingModel(Base):
    __tablename__ = "job_embeddings"
    __table_args__ = (
        Index(
            "ix_job_embeddings_vector_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vector: Mapped[list] = mapped_column(Vector(768), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

> **Note sur `candidates` vs `candidate_profiles`:** Le FK `candidates.id` suppose l'existence d'une table `candidates`. Si dans ta base c'est `candidate_profiles`, ajuste le FK pour pointer vers `candidate_profiles.id`. Vérifie avec : `docker exec timescaledb-container-dev psql -U postgres -d jobai_db -c "\dt public.*"`

- [ ] **Step 5.4: Commit**

```bash
git add app/infrastructure/persistence/models/ai_analysis.py \
        app/infrastructure/persistence/models/candidate_embedding.py \
        app/infrastructure/persistence/models/job_embedding.py
git commit -m "feat(ai-analysis): add ORM models for ai_analyses, candidate_embeddings, job_embeddings"
```

---

## Task 6: Migrations Alembic (3 migrations)

**Concept:** Alembic génère les migrations en comparant les ORM models avec le schéma actuel de la base. On crée 3 migrations dans l'ordre : (1) activer les extensions pgvector, (2) créer `ai_analyses`, (3) créer les tables d'embeddings avec HNSW.

> **Prérequis :** La base doit tourner (`docker-compose -f docker-compose.dev.yml up -d db`) et les migrations précédentes doivent être appliquées (`poetry run alembic upgrade head`).

**Files:**
- Create: `migrations/versions/YYYYMMDD_<rev>_enable_vector_extensions.py`
- Create: `migrations/versions/YYYYMMDD_<rev>_create_ai_analyses_table.py`
- Create: `migrations/versions/YYYYMMDD_<rev>_create_embedding_tables.py`

- [ ] **Step 6.1: Vérifier l'état actuel des migrations**

```bash
poetry run alembic upgrade head
poetry run alembic current
```

Note le revision ID affiché — c'est le `down_revision` de ta première nouvelle migration.

- [ ] **Step 6.2: Générer la migration 1 — activation des extensions**

Les extensions ont été activées par le script SQL au démarrage, mais Alembic doit en avoir connaissance pour garantir l'idempotence en CI. On crée une migration manuelle (pas autogenerate) :

```bash
poetry run alembic revision --message "enable_pgvector_and_pgvectorscale_extensions"
```

Puis édite le fichier généré dans `migrations/versions/` :

```python
"""enable_pgvector_and_pgvectorscale_extensions

Revision ID: <généré automatiquement>
Revises: cc9efd2af8eb   # ← remplace par le dernier revision ID existant
Create Date: <date>
"""
from typing import Sequence, Union
from alembic import op

revision: str = "<généré>"
down_revision: Union[str, Sequence[str], None] = "cc9efd2af8eb"  # ← dernier existant
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vectorscale")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

- [ ] **Step 6.3: Appliquer la migration 1 et vérifier**

```bash
poetry run alembic upgrade head
poetry run alembic current
```

- [ ] **Step 6.4: Générer la migration 2 — table `ai_analyses`**

```bash
poetry run alembic revision --autogenerate --message "create_ai_analyses_table"
```

Ouvre le fichier généré et vérifie que `upgrade()` contient bien la création de `ai_analyses` avec la contrainte UNIQUE. Si Alembic a généré des opérations inattendues (sur d'autres tables), supprime-les — garde uniquement ce qui concerne `ai_analyses`.

Applique :

```bash
poetry run alembic upgrade head
```

- [ ] **Step 6.5: Générer la migration 3 — tables d'embeddings + HNSW**

```bash
poetry run alembic revision --autogenerate --message "create_candidate_and_job_embedding_tables"
```

> ⚠️ Alembic ne génère **pas** les index HNSW automatiquement (pgvector custom index). Après avoir appliqué l'autogenerate pour les colonnes, tu devras ajouter manuellement dans `upgrade()` :

```python
# Dans la migration générée, après la création des tables, ajoute :
op.execute("""
    CREATE INDEX IF NOT EXISTS ix_candidate_embeddings_vector_hnsw
    ON public.candidate_embeddings
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
""")
op.execute("""
    CREATE INDEX IF NOT EXISTS ix_job_embeddings_vector_hnsw
    ON public.job_embeddings
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
""")
```

Et dans `downgrade()` :

```python
op.execute("DROP INDEX IF EXISTS public.ix_candidate_embeddings_vector_hnsw")
op.execute("DROP INDEX IF EXISTS public.ix_job_embeddings_vector_hnsw")
```

Applique :

```bash
poetry run alembic upgrade head
```

- [ ] **Step 6.6: Vérifier les tables et les indexes dans la base**

```bash
docker exec timescaledb-container-dev psql -U postgres -d jobai_db -c "\dt public.*"
docker exec timescaledb-container-dev psql -U postgres -d jobai_db -c "\di public.*embedding*"
```

Attendu : tables `ai_analyses`, `candidate_embeddings`, `job_embeddings` + les index HNSW.

- [ ] **Step 6.7: Commit**

```bash
git add migrations/versions/
git commit -m "feat(ai-analysis): add migrations for extensions, ai_analyses, and embedding tables with HNSW indexes"
```

---

## Task 7: `TimescaleVectorStoreAdapter` — implémentation du port

**Concept:** L'adapter implémente `VectorStorePort` avec SQLAlchemy async. La recherche de similarité utilise l'opérateur `<=>` (distance cosine de pgvector). Il stocke les vecteurs dans `candidate_embeddings` par défaut, avec la table sélectionnable via un paramètre de construction (`table: Literal["candidate", "job"]`).

**Files:**
- Create: `app/infrastructure/ai/__init__.py`
- Create: `app/infrastructure/ai/timescale_vector_store.py`

- [ ] **Step 7.1: Créer `app/infrastructure/ai/__init__.py`**

```python
```
(fichier vide)

- [ ] **Step 7.2: Implémenter `app/infrastructure/ai/timescale_vector_store.py`**

```python
from typing import Literal
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import SimilarityResult, VectorStorePort
from app.infrastructure.persistence.models.candidate_embedding import CandidateEmbeddingModel
from app.infrastructure.persistence.models.job_embedding import JobEmbeddingModel

_MODEL_MAP = {
    "candidate": CandidateEmbeddingModel,
    "job": JobEmbeddingModel,
}
_FK_MAP = {
    "candidate": "candidate_id",
    "job": "job_posting_id",
}


class TimescaleVectorStoreAdapter(VectorStorePort):
    def __init__(self, session: AsyncSession, table: Literal["candidate", "job"] = "candidate") -> None:
        self._session = session
        self._model = _MODEL_MAP[table]
        self._fk_field = _FK_MAP[table]

    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None:
        existing = await self._session.get(self._model, id)
        if existing is not None:
            existing.vector = vector  # type: ignore[assignment]
            existing.metadata_ = metadata  # type: ignore[assignment]
        else:
            fk_value = metadata.get(self._fk_field, id)
            obj = self._model(
                id=id,
                **{self._fk_field: fk_value},
                vector=vector,
                metadata_=metadata,
            )
            self._session.add(obj)
        await self._session.flush()

    async def search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[SimilarityResult]:
        stmt = (
            select(
                self._model.id,
                self._model.metadata_,
                (self._model.vector.cosine_distance(vector)).label("distance"),
            )
            .order_by(text("distance ASC"))
            .limit(top_k)
        )
        result = await self._session.execute(stmt)
        return [
            SimilarityResult(id=row.id, score=1.0 - row.distance, metadata=row.metadata_)
            for row in result
        ]

    async def delete(self, id: UUID) -> None:
        stmt = delete(self._model).where(self._model.id == id)
        await self._session.execute(stmt)
        await self._session.flush()
```

- [ ] **Step 7.3: Commit**

```bash
git add app/infrastructure/ai/
git commit -m "feat(ai-analysis): implement TimescaleVectorStoreAdapter"
```

---

## Task 8: Tests d'intégration de l'adapter

**Concept:** Ces tests frappent la vraie base TimescaleDB (pas de mock). Ils utilisent la même fixture `db_session` transactionnelle que le reste du projet — chaque test est automatiquement rollback. Ils sont marqués `@pytest.mark.integration` pour pouvoir être exclus en CI rapide.

**Files:**
- Create: `tests/infrastructure/ai_analysis/__init__.py`
- Create: `tests/infrastructure/ai_analysis/test_timescale_vector_store.py`

- [ ] **Step 8.1: Vérifier que la fixture `db_session` est disponible**

```bash
grep -r "db_session" tests/conftest.py
```

Si elle n'existe pas, regarde dans `tests/infrastructure/` — copie le pattern de `tests/infrastructure/job_search/` pour la fixture.

- [ ] **Step 8.2: Créer `tests/infrastructure/ai_analysis/__init__.py`**

```bash
touch tests/infrastructure/ai_analysis/__init__.py
```

- [ ] **Step 8.3: Écrire les tests d'intégration**

```python
# tests/infrastructure/ai_analysis/test_timescale_vector_store.py
import pytest
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.ai.timescale_vector_store import TimescaleVectorStoreAdapter


CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upsert_and_search_returns_result(db_session: AsyncSession):
    adapter = TimescaleVectorStoreAdapter(db_session, table="candidate")
    vec = [0.1] * 768
    uid = uuid4()

    await adapter.upsert(uid, vec, {"candidate_id": str(CANDIDATE_ID)})
    results = await adapter.search(vec, top_k=5)

    assert len(results) >= 1
    ids = [r.id for r in results]
    assert uid in ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upsert_is_idempotent(db_session: AsyncSession):
    adapter = TimescaleVectorStoreAdapter(db_session, table="candidate")
    uid = uuid4()
    vec1 = [0.1] * 768
    vec2 = [0.9] * 768

    await adapter.upsert(uid, vec1, {"candidate_id": str(CANDIDATE_ID)})
    await adapter.upsert(uid, vec2, {"candidate_id": str(CANDIDATE_ID)})

    results = await adapter.search(vec2, top_k=1)
    assert results[0].id == uid
    assert results[0].score > 0.99


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_removes_vector(db_session: AsyncSession):
    adapter = TimescaleVectorStoreAdapter(db_session, table="candidate")
    uid = uuid4()
    vec = [0.5] * 768

    await adapter.upsert(uid, vec, {"candidate_id": str(CANDIDATE_ID)})
    await adapter.delete(uid)

    results = await adapter.search(vec, top_k=10)
    ids = [r.id for r in results]
    assert uid not in ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_returns_results_ordered_by_similarity(db_session: AsyncSession):
    adapter = TimescaleVectorStoreAdapter(db_session, table="candidate")

    close_uid = uuid4()
    far_uid = uuid4()
    query_vec = [1.0] * 768

    await adapter.upsert(close_uid, [1.0] * 768, {"candidate_id": str(CANDIDATE_ID)})
    await adapter.upsert(far_uid, [0.0] * 768, {"candidate_id": str(CANDIDATE_ID)})

    results = await adapter.search(query_vec, top_k=2)
    assert results[0].id == close_uid
    assert results[0].score > results[1].score
```

- [ ] **Step 8.4: Lancer uniquement les tests d'intégration**

```bash
# Assure-toi que TimescaleDB tourne
docker-compose -f docker-compose.dev.yml up -d db

poetry run pytest tests/infrastructure/ai_analysis/ -v -m integration
```

Attendu : 4 tests PASSED.

- [ ] **Step 8.5: Commit final**

```bash
git add tests/infrastructure/ai_analysis/
git commit -m "test(ai-analysis): add integration tests for TimescaleVectorStoreAdapter"
```

---

## Self-review — Couverture du ticket JOB-36

| Exigence ticket | Couverte par |
|---|---|
| Enable `pgvector` and `pgvectorscale` in Docker | Task 1 (docker-compose + init SQL) + Task 6 migration 1 |
| Alembic migration `candidate_embeddings` (vector(768), HNSW) | Task 5.2 + Task 6.5 |
| Alembic migration `job_embeddings` (vector(768), HNSW) | Task 5.3 + Task 6.5 |
| Alembic migration `ai_analyses` (status, scores, tokens, UNIQUE) | Task 5.1 + Task 6.4 |
| `VectorStorePort` ABC in `app/application/ai_analysis/ports.py` | Task 3 |
| `TimescaleVectorStoreAdapter` in `app/infrastructure/ai/timescale_vector_store.py` | Task 7 |
| UNIQUE(candidate_id, job_posting_id) on ai_analyses | Task 5.1 (`UniqueConstraint`) + Task 6.4 (migration) |
| HNSW index `vector_cosine_ops` | Task 5.2, 5.3 (ORM) + Task 6.5 (migration manuelle) |
| Embedding dimension 768 | Task 5.2, 5.3 (`Vector(768)`) |

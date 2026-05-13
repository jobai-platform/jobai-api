# JOB-38 — LangGraph Matching Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter le pipeline LangGraph à 5 nœuds qui calcule le score de matching entre un profil candidat et une offre d'emploi, avec traçage complet via Langfuse.

**Architecture:** Un DAG (graphe orienté acyclique) LangGraph orchestre 5 nœuds séquentiels — chaque nœud reçoit un état partagé, l'enrichit, et passe au suivant. L'état voyage de nœud en nœud et contient tout le contexte de l'analyse. Le résultat final est un `MatchScore` persisté via `AIAnalysisRepository`.

**Tech Stack:** `langgraph ^0.2`, `langchain-ollama ^0.2`, `langfuse ^2.0`, `langchain ^0.3`, Ollama local (mistral:7b / nomic-embed-text), TimescaleDB + pgvector (déjà en place).

---

## 🎓 Comprendre LangGraph — de A à Z

### Pourquoi pas juste écrire des fonctions Python classiques ?

Tu pourrais écrire `result = scorer(extractor(profile, job))` — ça marcherait pour un MVP. Mais LangGraph apporte 4 choses critiques pour la prod :

1. **État partagé typé** — chaque nœud lit et écrit dans un dictionnaire d'état structuré. Si le nœud 3 plante, tu peux inspecter exactement ce que les nœuds 1 et 2 ont produit.
2. **Retry conditionnel** — le nœud `semantic_retriever` peut reboucler sur lui-même si la confiance est trop faible (`score < 0.6` → reformuler + réessayer, max 3 fois). Impossible proprement avec des fonctions chainées.
3. **Observabilité native** — LangGraph émet des événements à chaque transition de nœud. Langfuse les capture automatiquement via un callback → tu vois le DAG entier dans un dashboard.
4. **Swappabilité** — demain tu veux brancher MCP servers (JOB-39) à la place des appels directs Ollama → tu changes l'implémentation du nœud sans toucher à la structure du DAG.

### Ce qu'est un "état" LangGraph

```
PipelineState = {
  candidate_id: UUID,
  job_posting_id: UUID,
  tier: AnalysisQualityTier,        ← injecté au début
  structured_profile: dict | None,  ← rempli par node 1
  structured_job: dict | None,      ← rempli par node 2
  context_jobs: list[dict],         ← rempli par node 3
  raw_scores: dict | None,          ← rempli par node 4
  match_score: MatchScore | None,   ← rempli par node 5
  retry_count: int,                 ← géré par node 3
  error: str | None,                ← rempli si un nœud plante
}
```

Chaque nœud reçoit cet état, retourne un **dict partiel** (uniquement les clés qu'il modifie), et LangGraph fusionne automatiquement.

### Le DAG visualisé

```
START
  │
  ▼
[Node 1: profile_extractor]
  ─ Appelle Ollama (mistral:7b) avec le texte brut du profil
  ─ Retourne: structured_profile = {skills[], experience_years, locations[], salary_range}
  │
  ▼
[Node 2: job_extractor]
  ─ Appelle Ollama avec la description du job
  ─ Retourne: structured_job = {required_skills[], seniority, location, salary_range}
  │
  ▼
[Node 3: semantic_retriever]  ← peut boucler (max 3 fois)
  ─ Génère un embedding du profil via nomic-embed-text
  ─ Cherche les 5 jobs les plus similaires dans pgvector (contexte RAG)
  ─ Si confidence < 0.6 → retry_count++ → reboucle sur lui-même
  ─ Retourne: context_jobs = [{title, skills, similarity_score}, ...]
  │
  ▼
[Node 4: scorer]
  ─ Appelle Ollama avec structured_profile + structured_job + context_jobs
  ─ Demande un JSON avec 4 scores numériques (skills, experience, location, salary)
  ─ Retourne: raw_scores = {skills: 0.8, experience: 0.6, location: 1.0, salary: 0.7}
  │
  ▼
[Node 5: reporter]
  ─ Appelle Ollama pour générer l'explication textuelle
  ─ Calcule l'overall_score = moyenne pondérée des 4 scores
  ─ Construit le MatchScore VO et le persiste via AIAnalysisRepository
  ─ Retourne: match_score = MatchScore(overall=0.78, ..., explanation="...")
  │
  ▼
END
```

### Ce qu'est Langfuse

Langfuse est un outil d'observabilité spécialisé pour les pipelines LLM. Il tourne en self-hosted (Docker) et capture :
- Chaque appel LLM : prompt envoyé, réponse reçue, modèle utilisé, tokens consommés, latence
- La structure complète du DAG : quel nœud a appelé quel modèle, dans quel ordre
- Les coûts estimés par analyse

Tu accèdes à tout ça via `http://localhost:3001`. C'est essentiel pour déboguer pourquoi un score est mauvais — tu vois exactement ce que l'LLM a reçu en entrée.

### Comment ça s'intègre dans l'architecture hexagonale

```
Présentation (FastAPI)
    │  POST /api/v1/analyses/
    ▼
Application (Use Case — JOB-40)
    │  ComputeMatchScoreUseCase
    │  → appelle AIAnalysisPipelinePort.run(...)
    ▼
Infrastructure (ce qu'on construit ici — JOB-38)
    │  LangGraphMatchingPipeline implements AIAnalysisPipelinePort
    │  → orchestre les 5 nœuds
    │  → chaque nœud appelle OllamaLLMGateway (déjà en place)
    │  → node 3 appelle TimescaleVectorStoreAdapter (déjà en place)
    │  → node 5 persiste via AIAnalysisRepository (à créer ici)
    ▼
Domaine
    MatchScore VO, AIAnalysis entity (déjà en place)
```

---

## Périmètre JOB-38

**Inclus :**
- Dépendances langgraph/langchain/langfuse
- Service Langfuse dans docker-compose.dev.yml
- `AIAnalysisPipelinePort` (port application)
- `AIAnalysisRepository` port + implémentation SQLAlchemy
- `PipelineState` TypedDict
- Les 5 nœuds du DAG
- `LangGraphMatchingPipeline` (le graphe assemblé)
- `LangfuseCallbackHandler`
- Tests unitaires des nœuds (LLM mocké)

**Hors périmètre :**
- MCP servers → JOB-39
- `ComputeMatchScoreUseCase` et use cases applicatifs → JOB-40
- Endpoints FastAPI → JOB-41

---

## Fichiers créés / modifiés

| Fichier | Action | Responsabilité |
|---|---|---|
| `pyproject.toml` | Modifier | Ajouter langgraph, langchain-ollama, langfuse, structlog |
| `docker-compose.dev.yml` | Modifier | Ajouter service Langfuse (port 3001) |
| `app/application/ai_analysis/ports.py` | Modifier | Ajouter `AIAnalysisPipelinePort` et `AIAnalysisRepository` |
| `app/infrastructure/ai/pipeline/state.py` | Créer | `PipelineState` TypedDict — l'état partagé du DAG |
| `app/infrastructure/ai/pipeline/nodes.py` | Créer | Les 5 fonctions de nœuds du DAG |
| `app/infrastructure/ai/pipeline/graph.py` | Créer | Assemblage du DAG LangGraph |
| `app/infrastructure/ai/langfuse_callback.py` | Créer | Callback Langfuse pour le tracing |
| `app/infrastructure/persistence/repositories/ai_analysis_sqlalchemy.py` | Créer | Implémente `AIAnalysisRepository` |
| `tests/infrastructure/ai/test_pipeline_nodes.py` | Créer | Tests unitaires des 5 nœuds (LLM mocké) |
| `tests/infrastructure/ai/test_langgraph_pipeline.py` | Créer | Test d'intégration du pipeline complet (mocké) |
| `tests/fakes/ai_analysis/fake_pipeline_port.py` | Créer | Fake `AIAnalysisPipelinePort` pour les tests use cases (JOB-40) |
| `tests/fakes/ai_analysis/in_memory_ai_analysis_repo.py` | Créer | Fake `AIAnalysisRepository` en mémoire |

---

## Task 1 — Dépendances et service Langfuse

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.dev.yml`

**Contexte :** On installe les libs LangGraph/LangChain avant d'écrire le code — ça permet de vérifier qu'il n'y a pas de conflits de versions dès le début. Langfuse tourne en Docker sur le port 3001 (3000 est souvent déjà pris par le frontend).

- [ ] **Step 1 — Ajouter les dépendances dans `pyproject.toml`**

Dans la section `[tool.poetry.dependencies]` :

```toml
langgraph = "^0.2"
langchain = "^0.3"
langchain-community = "^0.3"
langchain-ollama = "^0.2"
langfuse = "^2.0"
structlog = "^24.0"
```

- [ ] **Step 2 — Installer**

```bash
poetry install
```

Résultat attendu : pas d'erreur de conflit. Si conflit sur `langchain` vs `langchain-community`, ajuster les versions mineures.

- [ ] **Step 3 — Ajouter Langfuse dans `docker-compose.dev.yml`**

Ajouter après le service `ollama` :

```yaml
  langfuse:
    image: langfuse/langfuse:latest
    container_name: langfuse-container-dev
    ports:
      - ${LANGFUSE_PORT:-3001}:3000
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/jobai_db
      NEXTAUTH_SECRET: ${LANGFUSE_SECRET:-changeme-langfuse-secret}
      NEXTAUTH_URL: http://localhost:3001
      SALT: ${LANGFUSE_SALT:-changeme-langfuse-salt}
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend
      - postgres
    restart: unless-stopped
```

- [ ] **Step 4 — Ajouter les variables Langfuse dans `.env.example`**

```bash
# Langfuse — LLM observability
LANGFUSE_PORT=3001
LANGFUSE_SECRET=changeme-langfuse-secret
LANGFUSE_SALT=changeme-langfuse-salt
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://langfuse:3000
```

Et les mêmes dans `.env` (`.env` n'est pas commité).

- [ ] **Step 5 — Vérifier la syntaxe docker-compose**

```bash
docker compose -f docker-compose.dev.yml config --quiet
```

Résultat attendu : aucune erreur.

- [ ] **Step 6 — Commit**

```bash
git add pyproject.toml poetry.lock docker-compose.dev.yml .env.example
git commit -m "feat(ai): add langgraph, langchain, langfuse dependencies and Langfuse Docker service"
```

---

## Task 2 — Ports application : AIAnalysisPipelinePort et AIAnalysisRepository

**Files:**
- Modify: `app/application/ai_analysis/ports.py`

**Contexte :** On ajoute 2 nouveaux ports (interfaces abstraites) au fichier existant. `AIAnalysisPipelinePort` est ce que le use case appellera — il ne sait pas que c'est LangGraph derrière. `AIAnalysisRepository` est l'interface pour persister/lire les `AIAnalysis`. En hexagonal, les use cases ne dépendent que de ces abstractions.

- [ ] **Step 1 — Écrire les tests qui vérifient que les ports sont bien définis**

Créer `tests/application/ai_analysis/test_ports.py` :

```python
import pytest
from uuid import uuid4
from app.application.ai_analysis.ports import AIAnalysisPipelinePort, AIAnalysisRepository
from app.domain.ai_analysis.enums import AnalysisQualityTier


def test_pipeline_port_is_abstract():
    """AIAnalysisPipelinePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIAnalysisPipelinePort()  # type: ignore


def test_analysis_repository_is_abstract():
    """AIAnalysisRepository cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIAnalysisRepository()  # type: ignore
```

- [ ] **Step 2 — Lancer le test pour confirmer qu'il échoue**

```bash
poetry run pytest tests/application/ai_analysis/test_ports.py -v
```

Résultat attendu : `ImportError` ou `AttributeError` — les classes n'existent pas encore.

- [ ] **Step 3 — Ajouter les ports dans `app/application/ai_analysis/ports.py`**

Ajouter à la fin du fichier existant (qui contient déjà `VectorStorePort`) :

```python
from abc import abstractmethod
from uuid import UUID

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


class AIAnalysisPipelinePort(ABC):
    """Runs the full matching pipeline for a candidate/job pair.

    Implementations: LangGraphMatchingPipeline (infra), FakeAIPipelinePort (tests).
    """

    @abstractmethod
    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore: ...


class AIAnalysisRepository(ABC):
    """Persists and retrieves AIAnalysis aggregates."""

    @abstractmethod
    async def save(self, analysis: AIAnalysis) -> None: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> AIAnalysis | None: ...

    @abstractmethod
    async def find_by_candidate_and_job(
        self, candidate_id: UUID, job_posting_id: UUID
    ) -> AIAnalysis | None: ...

    @abstractmethod
    async def find_by_candidate(
        self, candidate_id: UUID, limit: int = 20
    ) -> list[AIAnalysis]: ...
```

Note : `ABC` est déjà importé dans le fichier existant. Vérifier et n'ajouter l'import que s'il manque.

- [ ] **Step 4 — Lancer le test pour confirmer qu'il passe**

```bash
poetry run pytest tests/application/ai_analysis/test_ports.py -v
```

Résultat attendu : 2 tests `PASSED`.

- [ ] **Step 5 — Lancer la suite complète**

```bash
poetry run pytest -q
```

Résultat attendu : tous les tests passent (242+).

- [ ] **Step 6 — Commit**

```bash
git add app/application/ai_analysis/ports.py tests/application/ai_analysis/test_ports.py
git commit -m "feat(ai): add AIAnalysisPipelinePort and AIAnalysisRepository ports"
```

---

## Task 3 — PipelineState : le dictionnaire d'état du DAG

**Files:**
- Create: `app/infrastructure/ai/pipeline/__init__.py`
- Create: `app/infrastructure/ai/pipeline/state.py`
- Test: `tests/infrastructure/ai/test_pipeline_state.py`

**Contexte :** `PipelineState` est un `TypedDict` — un dictionnaire Python avec des clés typées. LangGraph utilise ce type pour valider ce que chaque nœud peut lire/écrire. C'est l'équivalent d'un contrat entre les nœuds : nœud 2 sait que `structured_profile` a été mis par nœud 1 parce que c'est dans le TypedDict.

- [ ] **Step 1 — Écrire le test**

Créer `tests/infrastructure/ai/test_pipeline_state.py` :

```python
from uuid import uuid4
from app.infrastructure.ai.pipeline.state import PipelineState, make_initial_state
from app.domain.ai_analysis.enums import AnalysisQualityTier


def test_make_initial_state_sets_defaults():
    """GIVEN valid IDs and tier
    WHEN make_initial_state is called
    THEN state has None for all computed fields and retry_count=0
    """
    candidate_id = uuid4()
    job_posting_id = uuid4()
    analysis_id = uuid4()

    state = make_initial_state(
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        tier=AnalysisQualityTier.FAST,
        analysis_id=analysis_id,
    )

    assert state["candidate_id"] == candidate_id
    assert state["job_posting_id"] == job_posting_id
    assert state["tier"] == AnalysisQualityTier.FAST
    assert state["analysis_id"] == analysis_id
    assert state["structured_profile"] is None
    assert state["structured_job"] is None
    assert state["context_jobs"] == []
    assert state["raw_scores"] is None
    assert state["match_score"] is None
    assert state["retry_count"] == 0
    assert state["error"] is None
```

- [ ] **Step 2 — Lancer le test pour confirmer qu'il échoue**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_state.py -v
```

Résultat attendu : `ModuleNotFoundError`.

- [ ] **Step 3 — Créer le package**

```bash
touch app/infrastructure/ai/pipeline/__init__.py
```

- [ ] **Step 4 — Créer `app/infrastructure/ai/pipeline/state.py`**

```python
from typing import TypedDict
from uuid import UUID

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


class PipelineState(TypedDict):
    candidate_id: UUID
    job_posting_id: UUID
    analysis_id: UUID
    tier: AnalysisQualityTier
    structured_profile: dict | None
    structured_job: dict | None
    context_jobs: list[dict]
    raw_scores: dict | None
    match_score: MatchScore | None
    retry_count: int
    error: str | None


def make_initial_state(
    candidate_id: UUID,
    job_posting_id: UUID,
    tier: AnalysisQualityTier,
    analysis_id: UUID,
) -> PipelineState:
    return PipelineState(
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        analysis_id=analysis_id,
        tier=tier,
        structured_profile=None,
        structured_job=None,
        context_jobs=[],
        raw_scores=None,
        match_score=None,
        retry_count=0,
        error=None,
    )
```

- [ ] **Step 5 — Lancer le test**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_state.py -v
```

Résultat attendu : 1 test `PASSED`.

- [ ] **Step 6 — Commit**

```bash
git add app/infrastructure/ai/pipeline/ tests/infrastructure/ai/test_pipeline_state.py
git commit -m "feat(ai): add PipelineState TypedDict for LangGraph DAG"
```

---

## Task 4 — Nodes 1 & 2 : profile_extractor et job_extractor

**Files:**
- Create: `app/infrastructure/ai/pipeline/nodes.py`
- Modify: `tests/infrastructure/ai/test_pipeline_nodes.py`

**Contexte :** Ces deux nœuds font la même chose : ils prennent du texte brut (profil ou offre) et demandent à Ollama de le structurer en JSON. C'est de l'**extraction d'entités** — on passe de "Je suis dev Python avec 5 ans d'expérience à Genève" à `{"skills": ["Python"], "experience_years": 5, "locations": ["Genève"]}`. On mocke Ollama dans les tests — on teste la logique du nœud, pas Ollama.

- [ ] **Step 1 — Écrire les tests pour les nœuds 1 et 2**

Créer `tests/infrastructure/ai/test_pipeline_nodes.py` :

```python
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.infrastructure.ai.pipeline.state import make_initial_state
from app.infrastructure.ai.pipeline.nodes import profile_extractor_node, job_extractor_node


@pytest.fixture
def base_state():
    return make_initial_state(
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        tier=AnalysisQualityTier.FAST,
        analysis_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_profile_extractor_node_returns_structured_profile(base_state):
    """GIVEN a state with candidate text in metadata
    WHEN profile_extractor_node is called with a mocked LLM
    THEN structured_profile is populated with parsed JSON
    """
    base_state["_candidate_text"] = "Python developer, 5 years, Geneva"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value='{"skills": ["Python"], "experience_years": 5, "locations": ["Geneva"], "salary_range": null}')

    result = await profile_extractor_node(base_state, llm=mock_llm)

    assert result["structured_profile"] is not None
    assert result["structured_profile"]["skills"] == ["Python"]
    assert result["structured_profile"]["experience_years"] == 5
    assert result["error"] is None


@pytest.mark.asyncio
async def test_profile_extractor_node_handles_invalid_json(base_state):
    """GIVEN the LLM returns non-JSON text
    WHEN profile_extractor_node is called
    THEN error is set and structured_profile is None
    """
    base_state["_candidate_text"] = "some text"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value="Sorry, I cannot help with that.")

    result = await profile_extractor_node(base_state, llm=mock_llm)

    assert result["structured_profile"] is None
    assert result["error"] is not None
    assert "JSON" in result["error"]


@pytest.mark.asyncio
async def test_job_extractor_node_returns_structured_job(base_state):
    """GIVEN a state with job description text
    WHEN job_extractor_node is called with a mocked LLM
    THEN structured_job is populated
    """
    base_state["_job_text"] = "Senior Python Engineer, remote, 100k-130k CHF"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value='{"required_skills": ["Python"], "seniority": "Senior", "location": "Remote", "salary_range": {"min": 100000, "max": 130000}}')

    result = await job_extractor_node(base_state, llm=mock_llm)

    assert result["structured_job"] is not None
    assert result["structured_job"]["seniority"] == "Senior"
    assert result["error"] is None
```

- [ ] **Step 2 — Lancer les tests pour confirmer qu'ils échouent**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_nodes.py -v
```

Résultat attendu : `ImportError` — `nodes.py` n'existe pas.

- [ ] **Step 3 — Créer `app/infrastructure/ai/pipeline/nodes.py`** avec les nœuds 1 et 2

```python
import json
import logging

from langchain_core.language_models import BaseLLM

from app.infrastructure.ai.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

_PROFILE_EXTRACTION_PROMPT = """Extract structured information from this candidate profile.
Return ONLY a valid JSON object with these exact keys:
- "skills": list of technical skills (strings)
- "experience_years": integer or null
- "locations": list of preferred locations (strings)
- "salary_range": {{"min": int, "max": int}} or null

Candidate profile:
{text}"""

_JOB_EXTRACTION_PROMPT = """Extract structured information from this job posting.
Return ONLY a valid JSON object with these exact keys:
- "required_skills": list of required technical skills (strings)
- "seniority": one of "Junior", "Mid", "Senior", "Lead" or null
- "location": location string or "Remote" or null
- "salary_range": {{"min": int, "max": int}} or null

Job posting:
{text}"""


def _parse_llm_json(response: str, context: str) -> dict | None:
    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("Node %s: LLM did not return valid JSON: %.100s", context, response)
        return None


async def profile_extractor_node(state: PipelineState, llm: BaseLLM) -> dict:
    text = state.get("_candidate_text", "")
    if not text:
        return {"error": "profile_extractor: no candidate text provided", "structured_profile": None}

    prompt = _PROFILE_EXTRACTION_PROMPT.format(text=text)
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "profile_extractor")

    if parsed is None:
        return {"error": "profile_extractor: LLM did not return valid JSON", "structured_profile": None}

    return {"structured_profile": parsed, "error": None}


async def job_extractor_node(state: PipelineState, llm: BaseLLM) -> dict:
    text = state.get("_job_text", "")
    if not text:
        return {"error": "job_extractor: no job text provided", "structured_job": None}

    prompt = _JOB_EXTRACTION_PROMPT.format(text=text)
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "job_extractor")

    if parsed is None:
        return {"error": "job_extractor: LLM did not return valid JSON", "structured_job": None}

    return {"structured_job": parsed, "error": None}
```

Note : `_candidate_text` et `_job_text` sont des clés "privées" de l'état (préfixe `_`), injectées par le pipeline avant le lancement. Le TypedDict `PipelineState` sera étendu dans Task 5 pour inclure ces champs.

- [ ] **Step 4 — Étendre `PipelineState` pour inclure les champs texte**

Dans `app/infrastructure/ai/pipeline/state.py`, ajouter à `PipelineState` :

```python
class PipelineState(TypedDict):
    # ... champs existants ...
    _candidate_text: str   # texte brut du profil candidat, injecté avant le lancement
    _job_text: str         # texte brut de l'offre, injecté avant le lancement
```

Et dans `make_initial_state` :

```python
def make_initial_state(
    candidate_id: UUID,
    job_posting_id: UUID,
    tier: AnalysisQualityTier,
    analysis_id: UUID,
    candidate_text: str = "",
    job_text: str = "",
) -> PipelineState:
    return PipelineState(
        # ... champs existants ...
        _candidate_text=candidate_text,
        _job_text=job_text,
    )
```

- [ ] **Step 5 — Lancer les tests**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_nodes.py -v
```

Résultat attendu : 3 tests `PASSED`.

- [ ] **Step 6 — Commit**

```bash
git add app/infrastructure/ai/pipeline/nodes.py app/infrastructure/ai/pipeline/state.py tests/infrastructure/ai/test_pipeline_nodes.py
git commit -m "feat(ai): add profile_extractor and job_extractor pipeline nodes"
```

---

## Task 5 — Nodes 3, 4, 5 : semantic_retriever, scorer, reporter

**Files:**
- Modify: `app/infrastructure/ai/pipeline/nodes.py`
- Modify: `tests/infrastructure/ai/test_pipeline_nodes.py`

**Contexte :** Ces 3 nœuds sont le cœur du matching.
- **Node 3 (RAG)** : génère un embedding du profil, cherche les 5 jobs similaires dans pgvector pour donner du contexte au scorer. Si la similarité max est < 0.6, il reformule et réessaie (max 3 fois).
- **Node 4 (scoring)** : avec profil structuré + job structuré + contexte des jobs similaires, demande à Ollama de noter 4 dimensions sur 1.0.
- **Node 5 (reporter)** : transforme les scores numériques en `MatchScore` VO avec une explication textuelle en langage naturel.

- [ ] **Step 1 — Ajouter les tests des nœuds 3, 4, 5 dans `tests/infrastructure/ai/test_pipeline_nodes.py`**

Ajouter à la fin du fichier existant :

```python
from app.infrastructure.ai.pipeline.nodes import (
    semantic_retriever_node,
    scorer_node,
    reporter_node,
)
from app.application.ai_analysis.ports import SimilarityResult
from app.domain.ai_analysis.value_objects import MatchScore


@pytest.mark.asyncio
async def test_semantic_retriever_node_returns_context_jobs(base_state):
    """GIVEN structured_profile is set
    WHEN semantic_retriever_node is called with mocked embedding + vector store
    THEN context_jobs is populated with similarity results
    """
    base_state["structured_profile"] = {"skills": ["Python"], "experience_years": 5}

    mock_embedding = AsyncMock()
    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    mock_vector_store = AsyncMock()
    mock_vector_store.search_similar_jobs = AsyncMock(return_value=[
        SimilarityResult(id=uuid4(), similarity_score=0.85, metadata={"title": "Python Dev"}),
    ])

    result = await semantic_retriever_node(
        base_state, embedding_port=mock_embedding, vector_store=mock_vector_store
    )

    assert len(result["context_jobs"]) == 1
    assert result["context_jobs"][0]["similarity_score"] == 0.85
    assert result["error"] is None


@pytest.mark.asyncio
async def test_semantic_retriever_retries_when_low_confidence(base_state):
    """GIVEN max similarity < 0.6 on first attempt
    WHEN semantic_retriever_node is called
    THEN retry_count is incremented
    """
    base_state["structured_profile"] = {"skills": ["Python"]}
    base_state["retry_count"] = 0

    mock_embedding = AsyncMock()
    mock_embedding.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    mock_vector_store = AsyncMock()
    mock_vector_store.search_similar_jobs = AsyncMock(return_value=[
        SimilarityResult(id=uuid4(), similarity_score=0.4, metadata={}),
    ])

    result = await semantic_retriever_node(
        base_state, embedding_port=mock_embedding, vector_store=mock_vector_store
    )

    assert result["retry_count"] == 1


@pytest.mark.asyncio
async def test_scorer_node_returns_raw_scores(base_state):
    """GIVEN structured_profile, structured_job, and context_jobs are set
    WHEN scorer_node is called with mocked LLM
    THEN raw_scores is populated with 4 float scores
    """
    base_state["structured_profile"] = {"skills": ["Python"], "experience_years": 5}
    base_state["structured_job"] = {"required_skills": ["Python"], "seniority": "Senior"}
    base_state["context_jobs"] = []

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value='{"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}'
    )

    result = await scorer_node(base_state, llm=mock_llm)

    assert result["raw_scores"] is not None
    assert result["raw_scores"]["skills"] == 0.9
    assert result["error"] is None


@pytest.mark.asyncio
async def test_reporter_node_returns_match_score(base_state):
    """GIVEN raw_scores are set
    WHEN reporter_node is called with mocked LLM
    THEN match_score VO is returned with valid scores and explanation
    """
    base_state["structured_profile"] = {"skills": ["Python"]}
    base_state["structured_job"] = {"required_skills": ["Python"]}
    base_state["raw_scores"] = {"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value="Strong Python skills match. Experience slightly below requirement."
    )

    result = await reporter_node(base_state, llm=mock_llm)

    assert result["match_score"] is not None
    assert isinstance(result["match_score"], MatchScore)
    assert 0.0 <= result["match_score"].overall <= 1.0
    assert len(result["match_score"].explanation) > 0
```

- [ ] **Step 2 — Lancer les tests pour confirmer qu'ils échouent**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_nodes.py -v
```

Résultat attendu : `ImportError` sur `semantic_retriever_node`, etc.

- [ ] **Step 3 — Ajouter les nœuds 3, 4, 5 dans `app/infrastructure/ai/pipeline/nodes.py`**

Ajouter à la fin du fichier existant :

```python
from app.application.ai_analysis.ports import SimilarityResult, VectorStorePort
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.value_objects import MatchScore

_SCORING_PROMPT = """You are a job matching expert. Score the compatibility between this candidate and job.

CANDIDATE:
{profile}

JOB REQUIREMENT:
{job}

SIMILAR JOBS FOR CONTEXT:
{context}

Return ONLY a valid JSON object with these exact keys (float values between 0.0 and 1.0):
{{"skills": <float>, "experience": <float>, "location": <float>, "salary": <float>}}"""

_EXPLANATION_PROMPT = """Write a 2-3 sentence explanation of this job match in a professional tone.
Be specific about strengths and gaps.

Scores: skills={skills}, experience={experience}, location={location}, salary={salary}
Candidate profile: {profile}
Job requirements: {job}

Write the explanation in the same language as the job description."""

_CONFIDENCE_THRESHOLD = 0.6
_MAX_RETRIES = 3


async def semantic_retriever_node(
    state: PipelineState,
    embedding_port: EmbeddingPort,
    vector_store: VectorStorePort,
) -> dict:
    profile = state.get("structured_profile")
    if not profile:
        return {"error": "semantic_retriever: no structured_profile available"}

    profile_text = " ".join(str(v) for v in profile.values() if v)
    vector = await embedding_port.generate_embedding(profile_text)
    results: list[SimilarityResult] = await vector_store.search_similar_jobs(
        query_vector=vector, top_k=5
    )

    max_score = max((r.similarity_score for r in results), default=0.0)
    retry_count = state.get("retry_count", 0)

    if max_score < _CONFIDENCE_THRESHOLD and retry_count < _MAX_RETRIES:
        return {"retry_count": retry_count + 1}

    context_jobs = [
        {"similarity_score": r.similarity_score, **r.metadata}
        for r in results
    ]
    return {"context_jobs": context_jobs, "error": None}


async def scorer_node(state: PipelineState, llm: BaseLLM) -> dict:
    profile = state.get("structured_profile", {})
    job = state.get("structured_job", {})
    context = state.get("context_jobs", [])

    prompt = _SCORING_PROMPT.format(
        profile=json.dumps(profile, ensure_ascii=False),
        job=json.dumps(job, ensure_ascii=False),
        context=json.dumps(context[:3], ensure_ascii=False),
    )
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "scorer")

    if parsed is None:
        return {"error": "scorer: LLM did not return valid JSON", "raw_scores": None}

    required = {"skills", "experience", "location", "salary"}
    if not required.issubset(parsed.keys()):
        return {"error": f"scorer: missing keys in response: {required - parsed.keys()}", "raw_scores": None}

    return {"raw_scores": parsed, "error": None}


async def reporter_node(state: PipelineState, llm: BaseLLM) -> dict:
    raw = state.get("raw_scores", {}) or {}
    profile = state.get("structured_profile", {})
    job = state.get("structured_job", {})

    skills = float(raw.get("skills", 0.0))
    experience = float(raw.get("experience", 0.0))
    location = float(raw.get("location", 0.0))
    salary = float(raw.get("salary", 0.0))

    prompt = _EXPLANATION_PROMPT.format(
        skills=skills, experience=experience, location=location, salary=salary,
        profile=json.dumps(profile, ensure_ascii=False),
        job=json.dumps(job, ensure_ascii=False),
    )
    explanation = str(await llm.ainvoke(prompt)).strip()

    overall = round((skills * 0.4 + experience * 0.3 + location * 0.2 + salary * 0.1), 3)

    try:
        score = MatchScore(
            overall=overall,
            skills_score=skills,
            experience_score=experience,
            location_score=location,
            salary_score=salary,
            explanation=explanation,
        )
    except (ValueError, TypeError) as exc:
        return {"error": f"reporter: invalid scores — {exc}", "match_score": None}

    return {"match_score": score, "error": None}
```

- [ ] **Step 4 — Lancer les tests**

```bash
poetry run pytest tests/infrastructure/ai/test_pipeline_nodes.py -v
```

Résultat attendu : tous les tests `PASSED`.

- [ ] **Step 5 — Lancer la suite complète**

```bash
poetry run pytest -q
```

- [ ] **Step 6 — Commit**

```bash
git add app/infrastructure/ai/pipeline/nodes.py tests/infrastructure/ai/test_pipeline_nodes.py
git commit -m "feat(ai): add semantic_retriever, scorer, reporter pipeline nodes"
```

---

## Task 6 — Assemblage du DAG LangGraph

**Files:**
- Create: `app/infrastructure/ai/pipeline/graph.py`
- Create: `tests/infrastructure/ai/test_langgraph_pipeline.py`

**Contexte :** C'est ici qu'on assemble les nœuds en un graphe exécutable. LangGraph utilise `StateGraph` — tu lui dis quels nœuds existent, dans quel ordre, et quelles conditions déterminent les transitions. Le nœud `semantic_retriever` a une condition spéciale : si `retry_count` a augmenté, il reboucle sur lui-même.

- [ ] **Step 1 — Écrire le test d'intégration du pipeline (tout mocké)**

Créer `tests/infrastructure/ai/test_langgraph_pipeline.py` :

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore
from app.application.ai_analysis.ports import SimilarityResult
from app.infrastructure.ai.pipeline.graph import LangGraphMatchingPipeline


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_embedding():
    emb = AsyncMock()
    emb.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return emb


@pytest.fixture
def mock_vector_store():
    vs = AsyncMock()
    vs.search_similar_jobs = AsyncMock(return_value=[
        SimilarityResult(id=uuid4(), similarity_score=0.8, metadata={"title": "Python Dev"})
    ])
    return vs


@pytest.mark.asyncio
async def test_pipeline_run_returns_match_score(mock_llm, mock_embedding, mock_vector_store):
    """GIVEN all nodes succeed with mocked LLM and vector store
    WHEN pipeline.run() is called
    THEN a MatchScore is returned
    """
    mock_llm.ainvoke.side_effect = [
        '{"skills": ["Python"], "experience_years": 5, "locations": ["Geneva"], "salary_range": null}',
        '{"required_skills": ["Python"], "seniority": "Senior", "location": "Remote", "salary_range": null}',
        '{"skills": 0.9, "experience": 0.7, "location": 1.0, "salary": 0.8}',
        "Strong Python skills. Some experience gap.",
    ]

    pipeline = LangGraphMatchingPipeline(
        llm=mock_llm,
        embedding_port=mock_embedding,
        vector_store=mock_vector_store,
        candidate_text="Python dev, 5 years, Geneva",
        job_text="Senior Python Engineer, remote",
    )

    score = await pipeline.run(
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        tier=AnalysisQualityTier.FAST,
        analysis_id=uuid4(),
    )

    assert isinstance(score, MatchScore)
    assert 0.0 <= score.overall <= 1.0
    assert len(score.explanation) > 0


@pytest.mark.asyncio
async def test_pipeline_raises_when_profile_extraction_fails(mock_llm, mock_embedding, mock_vector_store):
    """GIVEN the LLM returns non-JSON on profile extraction
    WHEN pipeline.run() is called
    THEN RuntimeError is raised with informative message
    """
    mock_llm.ainvoke.side_effect = ["Not valid JSON at all"]

    pipeline = LangGraphMatchingPipeline(
        llm=mock_llm,
        embedding_port=mock_embedding,
        vector_store=mock_vector_store,
        candidate_text="Python dev",
        job_text="Python job",
    )

    with pytest.raises(RuntimeError, match="profile_extractor"):
        await pipeline.run(
            candidate_id=uuid4(),
            job_posting_id=uuid4(),
            tier=AnalysisQualityTier.FAST,
            analysis_id=uuid4(),
        )
```

- [ ] **Step 2 — Lancer les tests pour confirmer qu'ils échouent**

```bash
poetry run pytest tests/infrastructure/ai/test_langgraph_pipeline.py -v
```

Résultat attendu : `ImportError`.

- [ ] **Step 3 — Créer `app/infrastructure/ai/pipeline/graph.py`**

```python
import logging
from functools import partial
from uuid import UUID

from langgraph.graph import StateGraph, END

from app.application.ai_analysis.ports import AIAnalysisPipelinePort, VectorStorePort
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.ai.pipeline.nodes import (
    job_extractor_node,
    profile_extractor_node,
    reporter_node,
    scorer_node,
    semantic_retriever_node,
)
from app.infrastructure.ai.pipeline.state import PipelineState, make_initial_state

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _should_retry_retriever(state: PipelineState) -> str:
    """Conditional edge: if retry_count changed, loop back; otherwise proceed."""
    if state.get("error"):
        return "error"
    if state.get("retry_count", 0) > 0 and state.get("retry_count", 0) <= _MAX_RETRIES:
        prev_retry = state.get("_prev_retry_count", 0)
        if state["retry_count"] > prev_retry:
            return "retry"
    return "scorer"


class LangGraphMatchingPipeline(AIAnalysisPipelinePort):
    """Implements AIAnalysisPipelinePort using a 5-node LangGraph DAG."""

    def __init__(
        self,
        llm,
        embedding_port: EmbeddingPort,
        vector_store: VectorStorePort,
        candidate_text: str,
        job_text: str,
    ) -> None:
        self._llm = llm
        self._embedding_port = embedding_port
        self._vector_store = vector_store
        self._candidate_text = candidate_text
        self._job_text = job_text
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(PipelineState)

        graph.add_node("profile_extractor", partial(profile_extractor_node, llm=self._llm))
        graph.add_node("job_extractor", partial(job_extractor_node, llm=self._llm))
        graph.add_node(
            "semantic_retriever",
            partial(semantic_retriever_node, embedding_port=self._embedding_port, vector_store=self._vector_store),
        )
        graph.add_node("scorer", partial(scorer_node, llm=self._llm))
        graph.add_node("reporter", partial(reporter_node, llm=self._llm))

        graph.set_entry_point("profile_extractor")
        graph.add_edge("profile_extractor", "job_extractor")
        graph.add_edge("job_extractor", "semantic_retriever")
        graph.add_conditional_edges(
            "semantic_retriever",
            _should_retry_retriever,
            {"retry": "semantic_retriever", "scorer": "scorer", "error": END},
        )
        graph.add_edge("scorer", "reporter")
        graph.add_edge("reporter", END)

        return graph.compile()

    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore:
        initial_state = make_initial_state(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            tier=tier,
            analysis_id=analysis_id,
            candidate_text=self._candidate_text,
            job_text=self._job_text,
        )
        initial_state["_prev_retry_count"] = 0

        final_state: PipelineState = await self._graph.ainvoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(f"Pipeline failed: {final_state['error']}")

        score = final_state.get("match_score")
        if score is None:
            raise RuntimeError("Pipeline completed without producing a MatchScore")

        logger.info(
            "Pipeline completed: analysis_id=%s overall=%.3f",
            analysis_id,
            score.overall,
        )
        return score
```

- [ ] **Step 4 — Lancer les tests**

```bash
poetry run pytest tests/infrastructure/ai/test_langgraph_pipeline.py -v
```

Résultat attendu : 2 tests `PASSED`.

- [ ] **Step 5 — Lancer la suite complète**

```bash
poetry run pytest -q
```

- [ ] **Step 6 — Commit**

```bash
git add app/infrastructure/ai/pipeline/graph.py tests/infrastructure/ai/test_langgraph_pipeline.py
git commit -m "feat(ai): implement LangGraphMatchingPipeline with 5-node DAG"
```

---

## Task 7 — Langfuse callback

**Files:**
- Create: `app/infrastructure/ai/langfuse_callback.py`
- Modify: `app/infrastructure/ai/pipeline/graph.py`

**Contexte :** Langfuse reçoit un callback à chaque appel LLM et à chaque transition de nœud. On lui passe une clé publique et une clé secrète (récupérées depuis l'UI Langfuse sur `http://localhost:3001`). Le callback est passé à LangGraph via `config={"callbacks": [handler]}` — LangGraph + LangChain propagent automatiquement ce callback à tous les appels LLM internes. Si Langfuse n'est pas configuré (clés vides), le callback est un no-op.

- [ ] **Step 1 — Créer `app/infrastructure/ai/langfuse_callback.py`**

```python
import logging
import os

logger = logging.getLogger(__name__)


def get_langfuse_callback():
    """Returns a Langfuse callback handler if configured, else None.

    Requires LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    to be set in the environment. Returns None silently if not configured
    so the pipeline works without Langfuse in local dev.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")

    if not public_key or not secret_key:
        logger.debug("Langfuse not configured — tracing disabled")
        return None

    try:
        from langfuse.callback import CallbackHandler
        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("Langfuse tracing enabled at %s", host)
        return handler
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse callback: %s", exc)
        return None
```

- [ ] **Step 2 — Intégrer le callback dans `LangGraphMatchingPipeline.run()`**

Dans `app/infrastructure/ai/pipeline/graph.py`, modifier la méthode `run()` :

```python
from app.infrastructure.ai.langfuse_callback import get_langfuse_callback

    async def run(self, ...) -> MatchScore:
        initial_state = make_initial_state(...)
        initial_state["_prev_retry_count"] = 0

        callbacks = []
        langfuse_handler = get_langfuse_callback()
        if langfuse_handler:
            callbacks.append(langfuse_handler)

        config = {"callbacks": callbacks} if callbacks else {}

        final_state: PipelineState = await self._graph.ainvoke(initial_state, config=config)

        # ... reste inchangé
```

- [ ] **Step 3 — Écrire un test pour le callback**

Créer `tests/infrastructure/ai/test_langfuse_callback.py` :

```python
import pytest
from unittest.mock import patch


def test_get_langfuse_callback_returns_none_when_not_configured(monkeypatch):
    """GIVEN LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not set
    WHEN get_langfuse_callback is called
    THEN None is returned (no crash)
    """
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    from app.infrastructure.ai.langfuse_callback import get_langfuse_callback
    result = get_langfuse_callback()

    assert result is None
```

- [ ] **Step 4 — Lancer le test**

```bash
poetry run pytest tests/infrastructure/ai/test_langfuse_callback.py -v
```

Résultat attendu : 1 test `PASSED`.

- [ ] **Step 5 — Lancer la suite complète**

```bash
poetry run pytest -q
```

- [ ] **Step 6 — Commit**

```bash
git add app/infrastructure/ai/langfuse_callback.py app/infrastructure/ai/pipeline/graph.py tests/infrastructure/ai/test_langfuse_callback.py
git commit -m "feat(ai): add Langfuse callback handler for DAG tracing"
```

---

## Task 8 — AIAnalysisRepository : port SQLAlchemy + fakes

**Files:**
- Create: `app/infrastructure/persistence/repositories/ai_analysis_sqlalchemy.py`
- Create: `tests/fakes/ai_analysis/in_memory_ai_analysis_repo.py`
- Create: `tests/fakes/ai_analysis/fake_pipeline_port.py`
- Test: `tests/infrastructure/persistence/test_ai_analysis_repository.py`

**Contexte :** Le repository traduit entre le domaine (`AIAnalysis` entity) et la base de données (`AIAnalysisModel` ORM). Les fakes sont des implémentations en mémoire utilisées dans les tests des use cases (JOB-40) — elles implémentent le même port mais sans DB.

- [ ] **Step 1 — Écrire le test du repository**

Créer `tests/infrastructure/persistence/test_ai_analysis_repository.py` :

```python
import pytest
from uuid import uuid4
from datetime import datetime, UTC

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.infrastructure.persistence.repositories.ai_analysis_sqlalchemy import SQLAlchemyAIAnalysisRepository


@pytest.mark.asyncio
async def test_save_and_find_by_id(db_session):
    """GIVEN a new AIAnalysis entity
    WHEN saved and retrieved by id
    THEN the retrieved entity matches the original
    """
    repo = SQLAlchemyAIAnalysisRepository(session=db_session)
    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )

    await repo.save(analysis)
    retrieved = await repo.find_by_id(analysis.id)

    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert retrieved.status == AnalysisStatus.PENDING


@pytest.mark.asyncio
async def test_find_by_candidate_and_job(db_session):
    """GIVEN an analysis saved for candidate/job pair
    WHEN find_by_candidate_and_job is called
    THEN the analysis is returned
    """
    repo = SQLAlchemyAIAnalysisRepository(session=db_session)
    candidate_id = uuid4()
    job_posting_id = uuid4()

    analysis = AIAnalysis(
        id=uuid4(),
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        status=AnalysisStatus.PENDING,
        match_score=None,
        quality_tier=AnalysisQualityTier.BALANCED,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )
    await repo.save(analysis)

    found = await repo.find_by_candidate_and_job(candidate_id, job_posting_id)
    assert found is not None
    assert found.candidate_id == candidate_id
```

- [ ] **Step 2 — Lancer le test pour confirmer qu'il échoue**

```bash
poetry run pytest tests/infrastructure/persistence/test_ai_analysis_repository.py -v
```

Résultat attendu : `ImportError`.

- [ ] **Step 3 — Créer `app/infrastructure/persistence/repositories/ai_analysis_sqlalchemy.py`**

```python
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import AIAnalysisRepository
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.persistence.models.ai_analysis import AIAnalysisModel


def _to_domain(m: AIAnalysisModel) -> AIAnalysis:
    score = None
    if m.overall_score is not None:
        score = MatchScore(
            overall=m.overall_score,
            skills_score=m.skills_score or 0.0,
            experience_score=m.experience_score or 0.0,
            location_score=m.location_score or 0.0,
            salary_score=m.salary_score or 0.0,
            explanation=m.explanation or "",
        )
    return AIAnalysis(
        id=m.id,
        candidate_id=m.candidate_id,
        job_posting_id=m.job_posting_id,
        status=AnalysisStatus(m.status),
        match_score=score,
        quality_tier=AnalysisQualityTier(m.quality_tier) if m.quality_tier else None,
        tokens_consumed=m.tokens_consumed,
        created_at=m.created_at,
        completed_at=m.completed_at,
        failure_reason=m.failure_reason,
    )


def _score_kwargs(analysis: AIAnalysis) -> dict:
    if analysis.match_score is None:
        return {}
    s = analysis.match_score
    return {
        "overall_score": s.overall,
        "skills_score": s.skills_score,
        "experience_score": s.experience_score,
        "location_score": s.location_score,
        "salary_score": s.salary_score,
        "explanation": s.explanation,
    }


class SQLAlchemyAIAnalysisRepository(AIAnalysisRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, analysis: AIAnalysis) -> None:
        values = {
            "id": analysis.id,
            "candidate_id": analysis.candidate_id,
            "job_posting_id": analysis.job_posting_id,
            "status": analysis.status.value,
            "quality_tier": analysis.quality_tier.value if analysis.quality_tier else "balanced",
            "tokens_consumed": analysis.tokens_consumed,
            "failure_reason": analysis.failure_reason,
            "completed_at": analysis.completed_at,
            **_score_kwargs(analysis),
        }
        stmt = (
            insert(AIAnalysisModel)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_ai_analyses_candidate_job",
                set_={k: v for k, v in values.items() if k not in ("id", "candidate_id", "job_posting_id")},
            )
        )
        await self._session.execute(stmt)

    async def find_by_id(self, id: UUID) -> AIAnalysis | None:
        result = await self._session.execute(
            select(AIAnalysisModel).where(AIAnalysisModel.id == id)
        )
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_candidate_and_job(
        self, candidate_id: UUID, job_posting_id: UUID
    ) -> AIAnalysis | None:
        result = await self._session.execute(
            select(AIAnalysisModel)
            .where(AIAnalysisModel.candidate_id == candidate_id)
            .where(AIAnalysisModel.job_posting_id == job_posting_id)
        )
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_candidate(
        self, candidate_id: UUID, limit: int = 20
    ) -> list[AIAnalysis]:
        result = await self._session.execute(
            select(AIAnalysisModel)
            .where(AIAnalysisModel.candidate_id == candidate_id)
            .limit(limit)
        )
        return [_to_domain(m) for m in result.scalars().all()]
```

- [ ] **Step 4 — Créer `tests/fakes/ai_analysis/in_memory_ai_analysis_repo.py`**

```python
from uuid import UUID

from app.application.ai_analysis.ports import AIAnalysisRepository
from app.domain.ai_analysis.entities import AIAnalysis


class InMemoryAIAnalysisRepository(AIAnalysisRepository):
    """In-memory repository for use in application-layer tests (JOB-40)."""

    def __init__(self) -> None:
        self._store: dict[UUID, AIAnalysis] = {}

    async def save(self, analysis: AIAnalysis) -> None:
        self._store[analysis.id] = analysis

    async def find_by_id(self, id: UUID) -> AIAnalysis | None:
        return self._store.get(id)

    async def find_by_candidate_and_job(
        self, candidate_id: UUID, job_posting_id: UUID
    ) -> AIAnalysis | None:
        return next(
            (a for a in self._store.values()
             if a.candidate_id == candidate_id and a.job_posting_id == job_posting_id),
            None,
        )

    async def find_by_candidate(
        self, candidate_id: UUID, limit: int = 20
    ) -> list[AIAnalysis]:
        return [a for a in self._store.values() if a.candidate_id == candidate_id][:limit]
```

- [ ] **Step 5 — Créer `tests/fakes/ai_analysis/fake_pipeline_port.py`**

```python
from uuid import UUID

from app.application.ai_analysis.ports import AIAnalysisPipelinePort
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


class FakeAIPipelinePort(AIAnalysisPipelinePort):
    """Returns a configurable MatchScore without running any LLM."""

    def __init__(self, default_score: MatchScore | None = None) -> None:
        self._score = default_score or MatchScore(
            overall=0.75,
            skills_score=0.8,
            experience_score=0.7,
            location_score=0.9,
            salary_score=0.6,
            explanation="Fake pipeline response.",
        )
        self.calls: list[dict] = []

    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore:
        self.calls.append({
            "candidate_id": candidate_id,
            "job_posting_id": job_posting_id,
            "tier": tier,
            "analysis_id": analysis_id,
        })
        return self._score


class FailingFakeAIPipelinePort(AIAnalysisPipelinePort):
    """Always raises — use to test error handling in ComputeMatchScoreUseCase."""

    def __init__(self, message: str = "Fake pipeline failure") -> None:
        self._message = message

    async def run(self, *args, **kwargs) -> MatchScore:
        raise RuntimeError(self._message)
```

- [ ] **Step 6 — Lancer les tests**

```bash
poetry run pytest tests/infrastructure/persistence/test_ai_analysis_repository.py -v
```

Résultat attendu : 2 tests `PASSED`.

- [ ] **Step 7 — Lancer la suite complète**

```bash
poetry run pytest -q
```

- [ ] **Step 8 — Commit**

```bash
git add \
  app/infrastructure/persistence/repositories/ai_analysis_sqlalchemy.py \
  tests/infrastructure/persistence/test_ai_analysis_repository.py \
  tests/fakes/ai_analysis/in_memory_ai_analysis_repo.py \
  tests/fakes/ai_analysis/fake_pipeline_port.py
git commit -m "feat(ai): add AIAnalysisRepository SQLAlchemy implementation and test fakes"
```

---

## Vérification finale

- [ ] **Suite complète de tests**

```bash
poetry run pytest -q
```

Résultat attendu : tous les tests passent (250+ passed, 1 skipped).

- [ ] **Vérifier que le DAG compile sans erreur**

```bash
poetry run python -c "
from unittest.mock import AsyncMock
from app.infrastructure.ai.pipeline.graph import LangGraphMatchingPipeline
p = LangGraphMatchingPipeline(
    llm=AsyncMock(),
    embedding_port=AsyncMock(),
    vector_store=AsyncMock(),
    candidate_text='test',
    job_text='test',
)
print('DAG compiled OK — nodes:', list(p._graph.nodes.keys()))
"
```

Résultat attendu : `DAG compiled OK — nodes: ['profile_extractor', 'job_extractor', 'semantic_retriever', 'scorer', 'reporter']`

- [ ] **Démarrer Langfuse et vérifier l'UI**

```bash
docker-compose -f docker-compose.dev.yml up langfuse -d
# Attendre ~20s
open http://localhost:3001
```

Résultat attendu : page de login Langfuse. Créer un compte admin, puis récupérer les clés API dans Settings → API Keys → mettre dans `.env` (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).

---

## Récapitulatif des commits

| # | Message | Fichiers clés |
|---|---|---|
| 1 | `feat(ai): add langgraph, langchain, langfuse dependencies` | `pyproject.toml`, `docker-compose.dev.yml` |
| 2 | `feat(ai): add AIAnalysisPipelinePort and AIAnalysisRepository ports` | `application/ai_analysis/ports.py` |
| 3 | `feat(ai): add PipelineState TypedDict for LangGraph DAG` | `pipeline/state.py` |
| 4 | `feat(ai): add profile_extractor and job_extractor pipeline nodes` | `pipeline/nodes.py` |
| 5 | `feat(ai): add semantic_retriever, scorer, reporter pipeline nodes` | `pipeline/nodes.py` |
| 6 | `feat(ai): implement LangGraphMatchingPipeline with 5-node DAG` | `pipeline/graph.py` |
| 7 | `feat(ai): add Langfuse callback handler for DAG tracing` | `langfuse_callback.py` |
| 8 | `feat(ai): add AIAnalysisRepository SQLAlchemy implementation and test fakes` | `repositories/ai_analysis_sqlalchemy.py`, fakes |

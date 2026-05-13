# Ollama Docker & Environment Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Intégrer Ollama (inférence LLM locale) dans l'environnement de développement Docker, câbler ses variables d'environnement dans la config applicative, et fournir un script de bootstrap des modèles — de sorte que `docker compose up` seul démarre un environnement AI entièrement fonctionnel.

**Architecture:** Ollama tourne comme service Docker dans `docker-compose.dev.yml`, exposé sur le port 11434 du réseau `backend`. L'application FastAPI pointe vers `http://ollama:11434` dans Docker et vers `http://localhost:11434` hors Docker (dev local pur). Un script shell `scripts/ollama-pull-models.sh` télécharge les modèles nécessaires au premier démarrage.

**Tech Stack:** Docker Compose, `ollama/ollama:latest`, `nomic-embed-text` (embeddings), `mistral:7b` (LLM défaut), variables d'environnement `.env` / `.env.example`.

---

## Périmètre

Ce plan couvre **uniquement** :
1. Service Docker Ollama dans `docker-compose.dev.yml`
2. Variables d'environnement AI dans `.env` / `.env.example` / `config.py`
3. Script de pull des modèles
4. `app` container qui attend qu'Ollama soit healthy avant de démarrer
5. Documentation de setup dans `CLAUDE.md`

Hors périmètre (couverts dans JOB-38) : LangGraph pipeline, MCP servers, Langfuse.

---

## Fichiers créés / modifiés

| Fichier | Action | Responsabilité |
|---|---|---|
| `docker-compose.dev.yml` | Modifier | Ajouter service `ollama` + healthcheck, dépendance `app → ollama` |
| `scripts/ollama-pull-models.sh` | Créer | Pull des modèles au premier démarrage |
| `.env.example` | Modifier | Ajouter toutes les variables AI avec valeurs par défaut documentées |
| `.env` | Modifier | Ajouter les variables AI réelles (non committées) |
| `app/core/config.py` | Modifier | Lire les variables AI depuis `os.getenv()` au lieu de valeurs hardcodées |

---

## Task 1 — Service Ollama dans docker-compose.dev.yml

**Files:**
- Modify: `docker-compose.dev.yml`

**Contexte pédagogique :** Un service Docker avec `healthcheck` permet à Docker Compose de savoir quand le container est *vraiment* prêt (pas juste démarré). `condition: service_healthy` dans `depends_on` garantit que l'app n'essaie pas de contacter Ollama avant qu'il soit opérationnel.

- [ ] **Step 1 — Ajouter le service `ollama`**

Ouvrir `docker-compose.dev.yml` et ajouter le service `ollama` après le service `minio` :

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: ollama-container-dev
    ports:
      - ${OLLAMA_PORT:-11434}:11434
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 8
      start_period: 30s
```

- [ ] **Step 2 — Ajouter le volume `ollama-data`**

Dans la section `volumes:` (en bas du fichier), ajouter :

```yaml
volumes:
  timescale-data:
  minio-data:
  ollama-data:    # ← ajouter cette ligne
```

- [ ] **Step 3 — Ajouter la dépendance `app → ollama`**

Dans le service `app`, la section `depends_on` doit inclure `ollama` :

```yaml
    depends_on:
      db:
        condition: service_healthy
      minio:
        condition: service_started
      ollama:
        condition: service_healthy
```

- [ ] **Step 4 — Vérifier que le fichier est syntaxiquement valide**

```bash
docker compose -f docker-compose.dev.yml config --quiet
```

Résultat attendu : aucune erreur, pas de sortie.

- [ ] **Step 5 — Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat(infra): add Ollama service to docker-compose.dev with healthcheck"
```

---

## Task 2 — Script de bootstrap des modèles

**Files:**
- Create: `scripts/ollama-pull-models.sh`

**Contexte pédagogique :** Les modèles Ollama (~4-8 GB chacun) ne sont pas inclus dans l'image Docker — ils doivent être téléchargés avec `ollama pull`. Ce script est idempotent : il vérifie si le modèle est déjà présent avant de le télécharger, ce qui évite des pulls inutiles à chaque `docker compose up`.

- [ ] **Step 1 — Créer le script**

Créer `scripts/ollama-pull-models.sh` avec ce contenu :

```bash
#!/usr/bin/env bash
# Pull required Ollama models for JobAI.
# Idempotent: skips models already present.
# Usage:
#   ./scripts/ollama-pull-models.sh                    # uses http://localhost:11434
#   OLLAMA_BASE_URL=http://ollama:11434 ./scripts/ollama-pull-models.sh

set -euo pipefail

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

MODELS=(
  "nomic-embed-text"   # embeddings — 274 MB
  "mistral:7b"         # LLM FAST tier — 4.1 GB
)

echo "→ Ollama base URL: ${OLLAMA_BASE_URL}"

wait_for_ollama() {
  echo "→ Waiting for Ollama to be ready..."
  for i in $(seq 1 30); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" > /dev/null 2>&1; then
      echo "✓ Ollama is ready."
      return 0
    fi
    echo "  attempt ${i}/30 — retrying in 5s"
    sleep 5
  done
  echo "✗ Ollama did not become ready in time." >&2
  exit 1
}

is_model_present() {
  local model="$1"
  curl -sf "${OLLAMA_BASE_URL}/api/tags" \
    | grep -q "\"name\":\"${model}" 2>/dev/null
}

pull_model() {
  local model="$1"
  if is_model_present "${model}"; then
    echo "✓ Model '${model}' already present — skipping."
  else
    echo "→ Pulling model '${model}'..."
    curl -sf "${OLLAMA_BASE_URL}/api/pull" \
      -d "{\"name\":\"${model}\"}" \
      | grep -E '"status"' || true
    echo "✓ Model '${model}' pulled."
  fi
}

wait_for_ollama

for model in "${MODELS[@]}"; do
  pull_model "${model}"
done

echo ""
echo "✓ All models ready."
```

- [ ] **Step 2 — Rendre le script exécutable**

```bash
chmod +x scripts/ollama-pull-models.sh
```

- [ ] **Step 3 — Tester le script en dry-run (sans Ollama actif)**

```bash
OLLAMA_BASE_URL=http://localhost:11434 bash -n scripts/ollama-pull-models.sh
```

Résultat attendu : aucune erreur de syntaxe bash.

- [ ] **Step 4 — Commit**

```bash
git add scripts/ollama-pull-models.sh
git commit -m "feat(infra): add ollama-pull-models bootstrap script"
```

---

## Task 3 — Variables d'environnement AI dans `.env.example` et `.env`

**Files:**
- Modify: `.env.example`
- Modify: `.env`

**Contexte pédagogique :** `.env.example` est commité dans git et sert de documentation pour les variables disponibles. `.env` est dans `.gitignore` et contient les vraies valeurs. Les valeurs par défaut dans `.env.example` doivent être utilisables telles quelles en développement local.

- [ ] **Step 1 — Mettre à jour `.env.example`**

Ajouter la section suivante à la fin de `.env.example` :

```bash
# =============================================
# AI PROVIDERS — Ollama (local inference)
# =============================================
# Ollama service URL.
# In Docker: http://ollama:11434
# Local dev (no Docker): http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434

# Model used for generating vector embeddings (274 MB)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Model used for LLM completions (default: FAST tier)
# Options: mistral:7b (fast), mistral-nemo:12b (balanced), mistral:22b (precise)
OLLAMA_LLM_MODEL=mistral:7b

# HTTP timeout in seconds for Ollama API calls (LLM can be slow on CPU)
OLLAMA_TIMEOUT=120.0

# AI provider selection: "ollama" (default, local) or "openai" (cloud)
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama

# OpenAI fallback (leave empty to stay fully local)
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4o-mini

# Ollama Docker port (exposed to host)
OLLAMA_PORT=11434
```

- [ ] **Step 2 — Mettre à jour `.env` (valeurs réelles Docker)**

Ajouter la même section à `.env`, avec `OLLAMA_BASE_URL` pointant vers le service Docker :

```bash
# =============================================
# AI PROVIDERS — Ollama
# =============================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=mistral:7b
OLLAMA_TIMEOUT=120.0
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4o-mini
OLLAMA_PORT=11434
```

- [ ] **Step 3 — Vérifier que `.env` n'est pas dans git**

```bash
git check-ignore -v .env
```

Résultat attendu : `.gitignore:.env` (le fichier est ignoré).

- [ ] **Step 4 — Commit**

```bash
git add .env.example
git commit -m "feat(config): add Ollama environment variables to .env.example"
```

---

## Task 4 — Lire les variables AI depuis `os.getenv()` dans `config.py`

**Files:**
- Modify: `app/core/config.py`

**Contexte pédagogique :** Actuellement, les champs AI dans `Settings` ont des valeurs hardcodées comme `"http://localhost:11434"`. Ça marche en dev local mais ignore la variable `.env` — dans Docker, Ollama est à `http://ollama:11434` et le container app ne pourra pas le joindre. En lisant depuis `os.getenv()`, la même variable `.env` contrôle les deux environnements.

- [ ] **Step 1 — Écrire un test qui vérifie que la config lit les env vars**

Créer `tests/unit/test_config.py` :

```python
import os
import importlib

import pytest


def test_settings_reads_ollama_base_url_from_env(monkeypatch):
    """GIVEN OLLAMA_BASE_URL is set in the environment
    WHEN Settings is instantiated
    THEN the value is read from the environment, not hardcoded
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-ollama:9999")

    # Re-import config to pick up the patched env var
    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_BASE_URL == "http://custom-ollama:9999"


def test_settings_reads_ollama_llm_model_from_env(monkeypatch):
    """GIVEN OLLAMA_LLM_MODEL is set in the environment
    WHEN Settings is instantiated
    THEN the correct model name is used
    """
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "mistral-nemo:12b")

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_LLM_MODEL == "mistral-nemo:12b"


def test_settings_ollama_timeout_defaults_to_120(monkeypatch):
    """GIVEN OLLAMA_TIMEOUT is NOT set in the environment
    WHEN Settings is instantiated
    THEN the default of 120.0 seconds is used
    """
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.OLLAMA_TIMEOUT == 120.0


def test_settings_embedding_provider_defaults_to_ollama(monkeypatch):
    """GIVEN EMBEDDING_PROVIDER is NOT set in the environment
    WHEN Settings is instantiated
    THEN the default 'ollama' is used
    """
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    import app.core.config as config_module
    importlib.reload(config_module)

    assert config_module.Settings.EMBEDDING_PROVIDER == "ollama"
```

- [ ] **Step 2 — Créer `tests/unit/__init__.py`**

```bash
touch tests/unit/__init__.py
```

- [ ] **Step 3 — Lancer le test pour confirmer qu'il échoue**

```bash
poetry run pytest tests/unit/test_config.py -v
```

Résultat attendu : `FAILED` — les champs lisent des valeurs hardcodées, pas `os.getenv()`.

- [ ] **Step 4 — Mettre à jour `app/core/config.py`**

Remplacer la section AI providers par des appels `os.getenv()` :

```python
  # ==========================================
  # AI PROVIDERS CONFIGURATION
  # ==========================================
  EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")
  LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

  # Ollama — pointe vers le service Docker "ollama" en prod, localhost en dev pur
  OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
  OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
  OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "mistral:7b")
  OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "120.0"))

  # OpenAI fallback (optionnel)
  OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY") or None
  OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
  OPENAI_LLM_MODEL: str = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
```

- [ ] **Step 5 — Lancer le test pour confirmer qu'il passe**

```bash
poetry run pytest tests/unit/test_config.py -v
```

Résultat attendu : 4 tests `PASSED`.

- [ ] **Step 6 — Lancer la suite complète pour vérifier aucune régression**

```bash
poetry run pytest -q
```

Résultat attendu : `238 passed, 1 skipped` (ou plus si d'autres tests ont été ajoutés).

- [ ] **Step 7 — Commit**

```bash
git add app/core/config.py tests/unit/__init__.py tests/unit/test_config.py
git commit -m "feat(config): read Ollama settings from environment variables"
```

---

## Task 5 — Variable d'environnement Ollama dans le container `app`

**Files:**
- Modify: `docker-compose.dev.yml`

**Contexte pédagogique :** Le service `app` charge `.env` via `env_file`, donc `OLLAMA_BASE_URL=http://ollama:11434` sera lu automatiquement. Mais il faut aussi passer `OLLAMA_BASE_URL` explicitement dans `environment:` du service `app` pour le cas où quelqu'un ne définit pas la variable dans `.env` — la valeur Docker prend le dessus sur le défaut `localhost`.

- [ ] **Step 1 — Ajouter les variables AI dans `environment:` du service `app`**

Dans `docker-compose.dev.yml`, dans la section `environment:` du service `app`, ajouter :

```yaml
    environment:
      - PORT=${API_PORT:-5001}
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
      - TF_CPP_MIN_LOG_LEVEL=2
      - PYTHON_VERSION=3.13
      - RUNNING_IN_DOCKER=1
      - RUN_INTEGRATION_TESTS=1 pytest -q
      - OLLAMA_BASE_URL=http://ollama:11434      # ← ajouter
      - OLLAMA_LLM_MODEL=${OLLAMA_LLM_MODEL:-mistral:7b}   # ← ajouter
      - OLLAMA_EMBEDDING_MODEL=${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}  # ← ajouter
      - OLLAMA_TIMEOUT=${OLLAMA_TIMEOUT:-120.0}  # ← ajouter
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-ollama}   # ← ajouter
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}     # ← ajouter
```

- [ ] **Step 2 — Valider la syntaxe du fichier**

```bash
docker compose -f docker-compose.dev.yml config --quiet
```

Résultat attendu : aucune erreur.

- [ ] **Step 3 — Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat(infra): pass Ollama env vars to app container explicitly"
```

---

## Task 6 — Documentation dans CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Contexte pédagogique :** `CLAUDE.md` est le fichier de référence pour les développeurs (et pour toi-même dans les prochaines sessions). Les commandes de setup Ollama doivent y figurer pour qu'on n'ait pas à les reconstruire à chaque nouvelle session.

- [ ] **Step 1 — Ajouter la section Ollama dans CLAUDE.md**

Dans `CLAUDE.md`, après la section `## Commands`, ajouter :

```markdown
## 🤖 Ollama — Local AI Inference

### Démarrage avec Docker (recommandé)

```bash
# Démarrer tous les services y compris Ollama
docker compose -f docker-compose.dev.yml up -d

# Attendre qu'Ollama soit healthy (~30s)
docker compose -f docker-compose.dev.yml ps

# Télécharger les modèles requis (une seule fois, ~4.4 GB)
./scripts/ollama-pull-models.sh
```

### Développement local sans Docker

```bash
# Installer Ollama : https://ollama.com
brew install ollama          # macOS

# Démarrer le serveur
ollama serve

# Télécharger les modèles
ollama pull nomic-embed-text   # embeddings (274 MB)
ollama pull mistral:7b         # LLM FAST tier (4.1 GB)
```

### Modèles utilisés

| Modèle | Usage | Taille | Tier |
|---|---|---|---|
| `nomic-embed-text` | Embeddings vectoriels | 274 MB | tous |
| `mistral:7b` | LLM completions | 4.1 GB | FAST |
| `mistral-nemo:12b` | LLM completions | 7.1 GB | BALANCED (optionnel) |

### Variables d'environnement clés

| Variable | Défaut (local) | Valeur Docker |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` |
| `OLLAMA_LLM_MODEL` | `mistral:7b` | `mistral:7b` |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | `nomic-embed-text` |
| `OLLAMA_TIMEOUT` | `120.0` | `120.0` |

### Vérifier qu'Ollama fonctionne

```bash
# Health check
curl http://localhost:11434/api/tags

# Test d'embedding rapide
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "hello world"}'

# Test LLM rapide
curl http://localhost:11434/api/generate \
  -d '{"model": "mistral:7b", "prompt": "Say hello", "stream": false}'
```
```

- [ ] **Step 2 — Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Ollama setup guide to CLAUDE.md"
```

---

## Vérification finale

- [ ] **Vérifier que la suite de tests passe entièrement**

```bash
poetry run pytest -q
```

Résultat attendu : tous les tests passent (238+ passed, 1 skipped).

- [ ] **Vérifier la config Docker synthétique**

```bash
docker compose -f docker-compose.dev.yml config | grep -A5 "ollama"
```

Résultat attendu : service `ollama` visible avec healthcheck et volume.

- [ ] **Smoke test Docker (optionnel, si Docker Desktop disponible)**

```bash
docker compose -f docker-compose.dev.yml up ollama -d
sleep 30
./scripts/ollama-pull-models.sh
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

Résultat attendu : JSON avec la liste des modèles téléchargés.

---

## Récapitulatif des commits

| # | Message | Fichiers |
|---|---|---|
| 1 | `feat(infra): add Ollama service to docker-compose.dev with healthcheck` | `docker-compose.dev.yml` |
| 2 | `feat(infra): add ollama-pull-models bootstrap script` | `scripts/ollama-pull-models.sh` |
| 3 | `feat(config): add Ollama environment variables to .env.example` | `.env.example` |
| 4 | `feat(config): read Ollama settings from environment variables` | `app/core/config.py`, `tests/unit/` |
| 5 | `feat(infra): pass Ollama env vars to app container explicitly` | `docker-compose.dev.yml` |
| 6 | `docs: add Ollama setup guide to CLAUDE.md` | `CLAUDE.md` |

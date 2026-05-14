# JobAI Backend — Production Runbook

> **Usage :** Ce document est la référence opérationnelle pour toute mise en production (MEP).
> Lire en entier avant de commencer. Exécuter les étapes dans l'ordre.

---

## Table des matières

1. [Prérequis](#1-prérequis)
2. [Infrastructure à provisionner](#2-infrastructure-à-provisionner)
3. [Secrets & variables d'environnement](#3-secrets--variables-denvironnement)
4. [CI/CD — GitHub Actions](#4-cicd--github-actions)
5. [Déploiement initial (première MEP)](#5-déploiement-initial-première-mep)
6. [Déploiements suivants (MEP standard)](#6-déploiements-suivants-mep-standard)
7. [Migrations de base de données](#7-migrations-de-base-de-données)
8. [Modèles Ollama](#8-modèles-ollama)
9. [Vérifications post-déploiement](#9-vérifications-post-déploiement)
10. [Rollback](#10-rollback)
11. [Checklist MEP](#11-checklist-mep)
12. [Bugs connus à corriger avant la prod](#12-bugs-connus-à-corriger-avant-la-prod)

---

## 1. Prérequis

### Outils requis sur le serveur de production

```bash
docker --version        # >= 24.0
docker compose version  # >= 2.20 (plugin v2, pas docker-compose v1)
curl --version
git --version
```

### Accès requis

| Ressource | Droits nécessaires |
|---|---|
| GitHub Container Registry (GHCR) | `read:packages` |
| Serveur prod | SSH avec clé privée |
| Stripe Dashboard | Clés live + création webhook |
| LinkedIn Developer Portal | App OAuth créée + redirect URI whitelist |
| AWS S3 (ou équivalent) | `s3:PutObject`, `s3:DeleteObject`, `s3:GetObject` sur le bucket |

---

## 2. Infrastructure à provisionner

### 2.1 PostgreSQL avec extensions

La base de données **doit** supporter les extensions suivantes (activées automatiquement par `scripts/init-extensions.sql`) :

| Extension | Usage |
|---|---|
| `vector` (pgvector) | Stockage des embeddings vectoriels |
| `vectorscale` | Recherche vectorielle haute performance |
| `timescaledb` | Compression time-series |

**Options recommandées :**
- **Supabase** — pgvector natif, gratuit pour commencer
- **Neon** — pgvector natif, serverless
- **AWS RDS** — activer `pgvector` via `CREATE EXTENSION`; TimescaleDB **non supporté** sur RDS → utiliser une instance EC2 ou Timescale Cloud

**URL de connexion attendue :**
```
postgresql+asyncpg://<user>:<password>@<host>:5432/<dbname>
```

### 2.2 Stockage objet (S3 ou MinIO)

Créer le bucket suivant **avant** le premier déploiement :

| Bucket | Variable | Usage |
|---|---|---|
| `jobai-cvs` | `S3_BUCKET_CVS` | Upload de CVs candidats |

**Configuration minimale AWS S3 :**
- Versioning : activé
- Chiffrement : SSE-S3 ou SSE-KMS
- Accès public : bloqué (les URLs sont signées côté serveur)

**Si MinIO (self-hosted) :**
```bash
# Créer le bucket au premier démarrage
mc alias set prod http://<host>:9000 <access_key> <secret_key>
mc mb prod/jobai-cvs
```

### 2.3 Ollama (LLM local) — optionnel

Ollama tourne en container Docker sur le serveur. Si le serveur n'a pas de GPU, envisager de passer sur OpenAI (`LLM_PROVIDER=openai`).

**Ressources minimales recommandées avec Ollama :**
- CPU : 8 cores
- RAM : 16 GB (mistral:7b tient en RAM)
- Disque : 20 GB libres pour les modèles

**Alternative cloud :** Passer `EMBEDDING_PROVIDER=openai` et `LLM_PROVIDER=openai` avec `OPENAI_API_KEY`.

---

## 3. Secrets & variables d'environnement

### 3.1 Variables critiques (⚠️ jamais committer)

| Variable | Comment l'obtenir | Exemple de valeur |
|---|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` | `a3f8c2d1...` |
| `JWT_SECRET_KEY` | Même commande | `b9e1f4a7...` |
| `STRIPE_SECRET_KEY` | Dashboard Stripe → Developers → API keys → Live secret key | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Dashboard Stripe → Webhooks → Endpoint → Signing secret | `whsec_...` |
| `LINKEDIN_CLIENT_ID` | LinkedIn Developer Portal → App credentials | `77q4d...` |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn Developer Portal → App credentials | `WPL_AP...` |
| `S3_ACCESS_KEY` | AWS IAM → Access keys | `AKIA...` |
| `S3_SECRET_KEY` | AWS IAM → Access keys | `wJalrX...` |
| `OPENAI_API_KEY` | platform.openai.com → API keys (si utilisé) | `sk-...` |

### 3.2 Fichier `.env` de production complet

```bash
# =============================================
# APP
# =============================================
ENVIRONMENT=production
DEBUG=False
API_PORT=5001
FRONTEND_ORIGIN=https://app.jobai.io   # ← adapter au vrai domaine

# =============================================
# AUTH
# =============================================
SECRET_KEY=<générer>
JWT_SECRET_KEY=<générer>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# =============================================
# DATABASE
# =============================================
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<db>

# =============================================
# STRIPE
# =============================================
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_LOOKUP_KEY=jobai_pro_monthly
STRIPE_ENTERPRISE_PRICE_LOOKUP_KEY=jobai_enterprise_monthly

# =============================================
# LINKEDIN OAUTH
# =============================================
LINKEDIN_CLIENT_ID=<id>
LINKEDIN_CLIENT_SECRET=<secret>
LINKEDIN_REDIRECT_URI=https://api.jobai.io/api/v1/auth/linkedin/callback
# LINKEDIN_PROXIES=http://user:pass@proxy1:port,http://user:pass@proxy2:port

# =============================================
# STORAGE S3
# =============================================
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=<aws_access_key>
S3_SECRET_KEY=<aws_secret_key>
S3_BUCKET_CVS=jobai-cvs
S3_REGION=eu-west-1
S3_PUBLIC_BASE_URL=https://jobai-cvs.s3.eu-west-1.amazonaws.com

# =============================================
# AI PROVIDERS — Ollama (local)
# =============================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=mistral:7b
OLLAMA_TIMEOUT=120.0
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama

# Si OpenAI à la place :
# EMBEDDING_PROVIDER=openai
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# OPENAI_LLM_MODEL=gpt-4o-mini

# =============================================
# DOCKER INTERNAL
# =============================================
RUNNING_IN_DOCKER=1
OLLAMA_PORT=11434
```

### 3.3 Secrets GitHub (CI/CD)

Configurer dans **Settings → Secrets and variables → Actions** :

| Secret | Valeur |
|---|---|
| `DEPLOY_HOST` | IP ou hostname du serveur prod |
| `DEPLOY_USER` | Utilisateur SSH (ex: `ubuntu`, `deploy`) |
| `DEPLOY_SSH_KEY` | Clé privée SSH (contenu complet, avec `-----BEGIN...`) |
| `GHCR_TOKEN` | GitHub Personal Access Token avec scope `read:packages` |
| `COMPOSE_PROD` | Contenu complet de `docker-compose.prod.yml` |
| `ENV_PROD` | Contenu complet du fichier `.env` de production |

---

## 4. CI/CD — GitHub Actions

### 4.1 Pipeline actuel

```
push/PR → backend-ci.yml
              ├── Tests (poetry run pytest -q)
              ├── Build image Docker → ghcr.io/.../jobai-backend:sha-<hash>
              └── Si main → push :latest

main passé → deploy.yml
              ├── SSH sur serveur prod
              ├── Injecte docker-compose.prod.yml + .env
              ├── docker compose pull
              ├── docker compose up -d
              └── scripts/smoke.sh (optionnel)
```

### 4.2 Garanties CI/CD actives

Le pipeline CI/CD applique maintenant ces garanties minimales :

- PostgreSQL CI utilise `pgvector/pgvector:pg16`, donc l'extension `vector` est disponible pendant les tests.
- `poetry run pytest -q` passe avant tout build Docker.
- L'image Docker est construite sur les PRs pour détecter les erreurs de packaging avant merge.
- Les images GHCR `sha-<hash>` et `latest` sont poussées uniquement depuis `main`.
- Les déploiements production sont sérialisés avec `concurrency`.
- Le déploiement exécute `poetry run alembic upgrade head` avant `docker compose up -d`.
- Le déploiement exécute `scripts/smoke.sh` et échoue si `/health` ne répond pas.

### 4.3 Jenkins optionnel

`Jenkinsfile` fournit un pipeline miroir pour les environnements qui exigent Jenkins :

```
Prepare PostgreSQL pgvector → poetry install → poetry run pytest -q → docker build
```

GitHub Actions reste la source de vérité. Jenkins ne doit être activé que si l'équipe veut un runner self-hosted ou une
intégration avec une chaîne de déploiement existante.

---

## 5. Déploiement initial (première MEP)

Exécuter **dans l'ordre** sur le serveur de production.

### Étape 1 — Préparer le serveur

```bash
mkdir -p ~/jobai-backend
cd ~/jobai-backend
```

### Étape 2 — Créer `docker-compose.prod.yml`

Créer le fichier (à adapter selon l'infrastructure) :

```yaml
services:
  app:
    image: ghcr.io/<org>/jobai-backend/jobai-backend:latest
    container_name: jobai-api-prod
    ports:
      - "5001:5001"
    env_file:
      - .env
    environment:
      - RUNNING_IN_DOCKER=1
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      ollama:
        condition: service_started
    networks:
      - backend
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: ollama-prod
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 15s
      timeout: 10s
      retries: 8
      start_period: 60s

networks:
  backend:
    driver: bridge

volumes:
  ollama-data:
```

> **Note :** MinIO et pgAdmin sont exclus — utiliser S3 managé et un accès DB direct en prod.

### Étape 3 — Créer le fichier `.env`

```bash
# Coller le contenu de la section 3.2, avec les vraies valeurs
nano .env
```

### Étape 4 — S'authentifier au registre Docker (GHCR)

```bash
echo "<GHCR_TOKEN>" | docker login ghcr.io -u <github_username> --password-stdin
```

### Étape 5 — Puller l'image

```bash
docker compose -f docker-compose.prod.yml pull
```

### Étape 6 — Lancer les migrations

```bash
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic upgrade head
```

Résultat attendu : `INFO  [alembic.runtime.migration] Running upgrade ... -> ..., ...`

Vérifier que toutes les 12 migrations sont appliquées :
```bash
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic current
```

### Étape 7 — Démarrer les services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Étape 8 — Télécharger les modèles Ollama

```bash
# Attendre qu'Ollama soit healthy (~60s)
docker compose -f docker-compose.prod.yml ps

# Lancer le script de pull (une seule fois, ~4.4 GB)
OLLAMA_BASE_URL=http://localhost:11434 ./scripts/ollama-pull-models.sh
```

> Si le script n'est pas sur le serveur, lancer directement :
> ```bash
> docker exec ollama-prod ollama pull nomic-embed-text
> docker exec ollama-prod ollama pull mistral:7b
> ```

### Étape 9 — Vérifications

Voir la section [9 — Vérifications post-déploiement](#9-vérifications-post-déploiement).

### Étape 10 — Configurer le webhook Stripe

1. Aller sur [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks)
2. Ajouter un endpoint : `https://api.jobai.io/api/v1/stripe/webhook`
3. Événements à écouter :
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copier le **Signing secret** → mettre à jour `STRIPE_WEBHOOK_SECRET` dans `.env`
5. Redémarrer l'app : `docker compose -f docker-compose.prod.yml restart app`

### Étape 11 — Synchroniser les prix Stripe

```bash
curl -X POST https://api.jobai.io/api/v1/stripe/sync-prices \
  -H "Authorization: Bearer <admin_token>"
```

---

## 6. Déploiements suivants (MEP standard)

Le CI/CD gère automatiquement les déploiements sur `main`. En cas de déploiement manuel :

```bash
cd ~/jobai-backend

# 1. Puller la nouvelle image
docker compose -f docker-compose.prod.yml pull

# 2. Lancer les migrations (si nouvelles migrations)
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic upgrade head

# 3. Redémarrer l'app avec la nouvelle image
docker compose -f docker-compose.prod.yml up -d --no-deps app
```

---

## 7. Migrations de base de données

### Migrations actuelles (12 au total)

| # | Revision | Description |
|---|---|---|
| 1 | `16cb4c36c81d` | Création table `users` |
| 2 | `abcdef123456` | Suppression colonne `is_superuser` |
| 3 | `8f0c147e01db` | Table `subscriptions` (Stripe) |
| 4 | `0cf3f33ef9af` | Table `billing_prices` |
| 5 | `8d920d93bdc7` | Contraintes billing_prices |
| 6 | `7b5a7a039fe1` | Contraintes billing_prices (suite) |
| 7 | `d6c0ac4f6d35` | Table `job_postings` |
| 8 | `cf91135dcbb2` | Champs LinkedIn sur `users` |
| 9 | `9cf37244a7c6` | Table `candidate_profiles` |
| 10 | `568ce812c1e5` | Table `search_agents` |
| 11 | `cc9efd2af8eb` | Champ `easy_apply_only` sur `search_agents` |
| 12 | `aac3238ce036` | Tables vector embeddings + AI analysis (pgvector) |

### Commandes utiles

```bash
# Voir la migration courante
poetry run alembic current

# Voir l'historique
poetry run alembic history --verbose

# Monter à la dernière migration
poetry run alembic upgrade head

# Revenir d'une migration en arrière (rollback)
poetry run alembic downgrade -1

# Générer une nouvelle migration
poetry run alembic revision --autogenerate -m "description"
```

### Rollback de migration

```bash
# Revenir à une révision spécifique
poetry run alembic downgrade <revision_id>

# Exemple — revenir avant les tables AI
poetry run alembic downgrade cc9efd2af8eb
```

---

## 8. Modèles Ollama

### Modèles requis

| Modèle | Variable | Taille | Rôle |
|---|---|---|---|
| `nomic-embed-text` | `OLLAMA_EMBEDDING_MODEL` | 274 MB | Génération d'embeddings vectoriels |
| `mistral:7b` | `OLLAMA_LLM_MODEL` | 4.1 GB | Complétion LLM (analyse, scoring) |

### Pull initial

```bash
# Via le script (recommandé)
OLLAMA_BASE_URL=http://localhost:11434 ./scripts/ollama-pull-models.sh

# Ou directement dans le container
docker exec ollama-prod ollama pull nomic-embed-text
docker exec ollama-prod ollama pull mistral:7b
```

### Vérifier les modèles présents

```bash
curl http://localhost:11434/api/tags | python3 -m json.tool
```

### Changer de modèle LLM

Pour utiliser un modèle plus puissant (serveur avec plus de RAM) :

```bash
# Dans .env
OLLAMA_LLM_MODEL=mistral-nemo:12b   # 7.1 GB, BALANCED
# ou
OLLAMA_LLM_MODEL=mistral:22b        # 13 GB, PRECISE

# Puis pull + restart
docker exec ollama-prod ollama pull mistral-nemo:12b
docker compose -f docker-compose.prod.yml restart app
```

---

## 9. Vérifications post-déploiement

Exécuter ces commandes après chaque déploiement.

### Health check de base

```bash
curl https://api.jobai.io/health
# Attendu : {"status":"ok"}
```

### Vérification de l'API

```bash
# Créer un utilisateur test
curl -X POST https://api.jobai.io/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"Test1234!","full_name":"Smoke Test"}'
# Attendu : 201 avec {"id":"...","email":"smoke@test.com",...}
```

### Vérification Ollama (depuis le serveur)

```bash
# Modèles disponibles
curl http://localhost:11434/api/tags

# Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
# Attendu : {"embedding":[...]} (vecteur de 768 dimensions)

# Test LLM
curl http://localhost:11434/api/generate \
  -d '{"model": "mistral:7b", "prompt": "Reply with OK only.", "stream": false}'
# Attendu : {"response":"OK",...}
```

### Vérification base de données

```bash
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic current
# Attendu : <revision_id> (head)
```

### Logs en cas d'erreur

```bash
# Logs app
docker compose -f docker-compose.prod.yml logs app --tail=100

# Logs Ollama
docker compose -f docker-compose.prod.yml logs ollama --tail=50

# Suivre les logs en temps réel
docker compose -f docker-compose.prod.yml logs -f app
```

---

## 10. Rollback

### Rollback image (retour à la version précédente)

```bash
cd ~/jobai-backend

# Identifier l'image précédente
docker images ghcr.io/<org>/jobai-backend/jobai-backend

# Mettre à jour docker-compose.prod.yml avec le tag précédent
# image: ghcr.io/<org>/jobai-backend/jobai-backend:sha-<previous_sha>

# Rollback migrations si nécessaire
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic downgrade -1

# Redémarrer avec l'ancienne image
docker compose -f docker-compose.prod.yml up -d --no-deps app
```

### Rollback migration uniquement

```bash
# Revenir d'une migration
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic downgrade -1

# Vérifier
docker compose -f docker-compose.prod.yml run --rm app \
  poetry run alembic current
```

---

## 11. Checklist MEP

### Avant le déploiement

- [ ] Tous les tests passent sur la PR (`poetry run pytest -q`)
- [ ] PR mergée sur `main`
- [ ] Variables d'environnement à jour dans le secret GitHub `ENV_PROD`
- [ ] Nouvelles migrations ajoutées ? → noter la révision cible
- [ ] Breaking changes DB ? → planifier une fenêtre de maintenance

### Pendant le déploiement

- [ ] `alembic upgrade head` exécuté sans erreur
- [ ] `docker compose up -d` sans erreur
- [ ] Tous les containers `Up` dans `docker ps`
- [ ] Ollama `healthy` dans `docker ps`

### Après le déploiement

- [ ] `GET /health` → `{"status":"ok"}`
- [ ] Test création utilisateur → 201
- [ ] Test embedding Ollama → vecteur retourné
- [ ] Test LLM Ollama → réponse texte
- [ ] Logs app : pas d'erreurs `ERROR` ou `CRITICAL`
- [ ] Webhook Stripe fonctionnel (test depuis le dashboard)

---

## 12. Bugs connus à corriger avant la prod

Ces problèmes existent dans le code actuel et doivent être résolus avant une MEP en production.

| # | Fichier | Bug | Impact | Fix |
|---|---|---|---|---|
| 1 | `.github/workflows/backend-ci.yml` | `refs/haeads/main` → typo | L'image Docker n'est jamais pushée sur `main` | Corriger en `refs/heads/main` |
| 2 | `.github/workflows/deploy.yml` | Pas de step `alembic upgrade head` | Les migrations ne sont pas appliquées automatiquement | Ajouter le step avant `docker compose up` |
| 3 | `app/main.py` | `allow_origins=["*"]` | CORS trop permissif | Remplacer par `[settings.FRONTEND_ORIGIN]` |
| 4 | `docker-compose.dev.yml` | `RUN_INTEGRATION_TESTS=1 pytest -q` | Valeur de variable malformée (contient des espaces) | Corriger en `RUN_INTEGRATION_TESTS=1` |
| 5 | `scripts/smoke.sh` | Fichier inexistant | Le step smoke test du deploy.yml échoue silencieusement | Créer le script |

### Fix rapide #1 — Typo CI

```bash
# Dans .github/workflows/backend-ci.yml
# Remplacer :
if: github.ref == 'refs/haeads/main'
# Par :
if: github.ref == 'refs/heads/main'
```

### Fix rapide #3 — CORS

```python
# Dans app/main.py, remplacer :
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
# Par :
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_ORIGIN], ...)
```

### Fix rapide #5 — Script smoke.sh minimal

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${API_BASE_URL:-http://localhost:5001}"
response=$(curl -sf "${BASE_URL}/health")
echo "${response}" | grep -q '"ok"' || { echo "Health check failed: ${response}" >&2; exit 1; }
echo "✓ Health check passed."
```

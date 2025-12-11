# Contributing to JobAI

Merci de contribuer au projet **JobAI Platform**.
Ce document définit les bonnes pratiques, le workflow de développement et les règles d’architecture à respecter.

---

## 🎯 Objectifs
- Garantir une qualité constante du code.
- Maintenir une architecture propre (Hexagonale + DDD).
- Encourager un développement basé sur TDD.
- Assurer une contribution simple, claire et reproductible.

---

## 🧪 Test-Driven Development (TDD) — Règle obligatoire

Chaque fonctionnalité doit être développée selon :
1. **RED** — écrire les tests avant le code.
2. **GREEN** — implémentation minimale pour passer les tests.
3. **REFACTOR** — améliorer la structure sans changer le comportement.

Aucune PR n’est acceptée **sans tests associés**.

---

## 🧱 Règles d’architecture

### ❗ Domain (interdit)
- Pas de SQLAlchemy
- Pas de FastAPI
- Pas de Pydantic
- Pas d'imports depuis infrastructure ou presentation

### ✔ Application
- Use cases minimalistes
- Ports/interfaces obligatoires
- Aucune logique métier ici

### ✔ Infrastructure
- Repositories SQLAlchemy
- Clients API externes
- Implémente les ports définis dans application

### ✔ Presentation
- Routes FastAPI
- DTOs / schemas
- Mapping HTTP → Use Case

---

## 🔀 Workflow Git

### Naming des branches
- feature/<context>/<feature-name>
- fix/<description>
- refactor/<module>

### Commits conventionnels
- feat: add SearchAgent use case
- fix: correct SQLAlchemy mapping
- refactor: extract domain logic
- test: add coverage for matching algorithm
- docs: update onboarding instructions

---

## 📋 Checklist Pull Request

### Architecture
- [ ] Pas de dépendance Domain → infra
- [ ] Ports correctement définis
- [ ] Use cases simples, lisibles
- [ ] Routes sans logique métier

### Qualité
- [ ] Code clair, nommage cohérent
- [ ] Typage strict (mypy-friendly)
- [ ] Pas de duplication (DRY)
- [ ] Simplicité (KISS)

### Tests
- [ ] Tests unitaires pour Domain
- [ ] Tests pour Use Cases
- [ ] Cas limites et erreurs

---

## 🛠 Outils recommandés
- **pytest**
- **ruff** (linting)
- **black** (format)
- **mypy** (typing)
- **docker-compose** pour services externes
- **GitHub Copilot Workspace** pour refactor assisté

---

## 💬 Communication
Les discussions autour des features, bugs ou améliorations se font via :
- Issues GitHub
- Discussions du repo
- Pull requests

Merci pour votre contribution ! 🚀


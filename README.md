# JobAI Platform — Architecture, DDD, TDD & Engineering Guidelines

## 🎯 Objectifs du projet
JobAI est une plateforme d’automatisation intelligente pour la recherche d’emploi, la génération d’analyses IA, le matching candidat–offre, et la gestion d’agents autonomes.

Ce README définit :
- L’architecture cible (Hexagonal + DDD)
- Les principes de qualité (KISS, DRY, SOLID, YAGNI)
- Les règles de développement (TDD FIRST)
- La structure des dossiers
- Le fonctionnement global attendu

## 🧱 Architecture Hexagonale (Ports & Adapters)
### **1. Domain (cœur métier)**
- Entités
- Value Objects
- Domain Services
- Règles métier pures
- **Aucune dépendance vers FastAPI, SQLAlchemy ou Pydantic**

### **2. Application (use cases)**
- Orchestration des opérations métier
- Ports / interfaces
- Communication entre Domain et Infrastructure
- **Aucune logique de persistance**

### **3. Infrastructure**
- Repositories SQLAlchemy
- Intégrations externes (Google, Stripe, LangChain, Pinecone…)
- Adapters techniques
- Implémente les ports définis en Application

### **4. Presentation**
- FastAPI (routes, contrôleurs)
- DTOs / Schemas Pydantic
- Webhooks
- Mapping HTTP → Use Cases

---

## 🧩 Domain-Driven Design (DDD)

### **Ubiquitous Language**
Le vocabulaire métier du projet inclut :

- Candidate
- JobPosting
- SearchAgent
- Application (candidature)
- SkillMatch
- AI Analysis
- BusinessAccount
- Review / Rating

### **Bounded Contexts**
- Users / Auth
- Job Search
- AI Analysis & Scoring
- Business Integrations (Google, Stripe…)

---

## 🧪 Méthodologie TDD (obligatoire)

Chaque fonctionnalité doit suivre :

1. **RED** — Écrire les tests en premier
2. **GREEN** — Implémentation minimale pour faire passer les tests
3. **REFACTOR** — Nettoyage, optimisation, extraction d’abstractions

Tous les tests doivent être verts avant tout commit/PR.

---

## 📁 Structure du projet

```bash
app/
├── domain/
│   └── <bounded context>/
│       ├── entities.py
│       ├── value_objects.py
│       └── domain_services.py
├── application/
│   └── <bounded context>/
│       ├── use_cases.py
│       └── ports.py
├── infrastructure/
│   ├── persistence/
│   │   ├── models/
│   │   └── repositories/
│   └── external/
├── presentation/
│   ├── api/
│   │   └── v1/
│   └── schemas/
tests/
└── <bounded context>/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/
```

## 🧰 Qualité
KISS\
→ Préférer les solutions simples et propres.

DRY\
→ Ne jamais dupliquer la logique métier.

SOLID\
→ Respect strict du DIP (Dependency Inversion Principle).\
→ Domaine = dépendances vers rien.\
→ Application = dépendances uniquement vers Domain.\
→ Infrastructure = dépend de tout, mais ne pollue rien.\

YAGNI\
→ Ne pas développer avant que ce soit réellement nécessaire.

## 🔄 Flux d’exécution
```bash
HTTP Request
   ↓
Presentation Layer (FastAPI Controller)
    ↓ DTO → Use Case
Application Layer (Use Case)
    ↓ Port|interfaces → Domain Service
Infrastructure Layer (Repository / API Client)
    ↓
Domain Layer (Entity / Value Object)
   ↑
Use Case → DTO → HTTP Response

```

## 🚀 Lancer le projet
```
poetry install
cp .env.example .env
docker-compose up -d
```

## Migration DB
```bash
poetry run alembic upgrade head
```

## 🧪 Tests
```
pytest -q
```

## 📝 Contribution (résumé)

- Écrire les tests avant le code
- Suivre l’architecture hexagonale strictement
- Routes minimalistes
- Domain indépendant
- Use cases comme orchestrateurs
- Repositories = implémentations propres et interchangeables

## Checklist PR

- Tests inclus
- Respect des couches
- Pas de duplication
- Documentation mise à jour si nécessaire
- Domain sans dépendances techniques

## 📎 Ressources utiles

- Architecture Hexagonale (Ports & Adapters)
- Domain-Driven Design Essentials
- Testing Pyramid
- Clean Architecture (Uncle Bob)
- LangChain & LLM patterns (pour SearchAgent & AI Analysis)

## 💬 Contact
Pour toute question : ouvrir une issue.

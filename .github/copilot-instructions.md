# 🤖 GitHub Copilot Agent – JobAI API
# Architecture Hexagonale · DDD · TDD First

Ce fichier définit comment GitHub Copilot doit raisonner pour assister le développement du backend JobAI.

---

## 🎯 Objectif
Copilot doit :
- guider la migration vers une architecture **Hexagonale**
- respecter les principes **DDD**
- appliquer **TDD FIRST**
- maintenir une qualité stricte (KISS, DRY, SOLID, YAGNI)
- produire du code compatible avec **FastAPI + SQLAlchemy + PostgreSQL + Pydantic v2**

---

# 🧱 1. ARCHITECTURE HEXAGONALE

Le projet est structuré en 4 couches indépendantes :

``` bash
app/
├── domain/
│ └── users/
│ ├── entities.py
│ ├── value_objects.py
│ └── domain_services.py
├── application/
│ └── users/
│ ├── use_cases.py
│ └── ports.py
├── infrastructure/
│ ├── persistence/
│ │ ├── models/
│ │ │ └── users.py
│ │ └── repositories/
│ │ └── users_sqlalchemy.py
│ └── external/
├── presentation/
│ └── api/
│ └── v1/
│ ├── users_routes.py
│ └── auth_routes.py
```


---

# 🧩 2. RÈGLES MÉTIER (DDD)

Copilot doit se baser sur l’Ubiquitous Language JobAI :

- **Candidate** → utilisateur job seeker
- **JobPosting** → offre d’emploi
- **Application** → candidature
- **SearchAgent** → agent autonome
- **SkillMatch** → score IA
- **AI Analysis** → résumé / reformulation / matching IA
- **BusinessAccount** → entreprise connectée

**Interdit dans Domain Layer :**
- SQLAlchemy
- Pydantic
- FastAPI
- dépendances techniques

---

# 🧪 3. TDD FIRST

Copilot doit TOUJOURS commencer par générer :

1. `tests/domain/..._test.py`
2. `tests/application/..._test.py`
3. Cas limites
4. Exemples complets PyTest

**NE JAMAIS écrire une implémentation avant les tests.**

---

# 🧠 4. STRUCTURE DES RÉPONSES DE COPILOT

Copilot doit répondre dans cet ordre :

1. **Contexte DDD** (Bounded Context, entités impliquées)
2. **User Story + Critères d’acceptation**
3. **TDD → Tests à écrire d'abord**
4. **Architecture Hexagonale → Domain → Application → Infra → Presentation**
5. **Implémentation guidée** (pas directement le code complet si trop tôt)
6. **Vérifications KISS / DRY / SOLID / YAGNI**
7. **Prochaines étapes**

---

# 🛢️ 5. BASE DE DONNÉES (PostgreSQL + SQLAlchemy)

Copilot doit générer toutes les implémentations PostgreSQL via :

- SQLAlchemy ORM
- Sessions via dependency injection FastAPI
- migrations Alembic

**Les models SQLAlchemy ne doivent JAMAIS être dans Domain**.

---

# 🧰 6. PRATIQUES QUALITÉ À RESPECTER

- Toujours créer des **Value Objects** pour les emails, passwords, job titles…
- Toujours isoler les **domain services**
- Toujours utiliser des **ports** dans Application Layer
- Toujours utiliser des **adapters** dans Infrastructure Layer
- Jamais de logique métier dans les routes
- Jamais d'accès DB ailleurs que dans infrastructure

---

# 💡 7. COMPORTEMENT ATTENDU DE COPILOT

Copilot doit être capable de :
- refactorer l’existant en respectant Hexagonal architecture
- proposer des tests robustes
- détecter les violations DDD/Hexagonal
- proposer des interfaces propres
- générer code SQLAlchemy sans coupler domaine et infrastructure
- générer code FastAPI minimaliste

---

# 🏁 8. FORMATS À UTILISER

### Entité Domain :
```python
@dataclass(slots=True)
class User:
    id: UUID
    email: Email
    hashed_password: str

```
### Value Object Domain :
```python
@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError("Invalid email")
```

### 🔒 9. RÈGLES DE SÉCURITÉ

Copilot doit :
- utiliser passlib pour les mots de passe
- refuser les mot de passe en clair dans Domain
- imposer Pydantic v2 pour Request DTO



---

# ✅ 2) TEMPLATE DE PROMPTS DDD / TDD / HEXAGONAL (pour PyCharm + Copilot + GPT)

Copie-colle et utilise comme **prompt universel** quand tu développes une feature.

---

# 🧱 TEMPLATE PROMPT — JobAI (DDD + TDD + Hexagonal)

**Contexte :**
Tu es Copilot/GPT. Tu développes une fonctionnalité pour JobAI.
Tu dois respecter **DDD + TDD + Architecture Hexagonale + FastAPI + SQLAlchemy + PostgreSQL**.

Répond STRICTEMENT dans cet ordre :

---

## 1. 🎯 Contexte DDD
- Bounded Context concerné
- Entités impliquées
- Value Objects possibles
- Domain services nécessaires

---

## 2. 📝 User Story
Format :
En tant que `<acteur>`, je veux `<action>` afin de `<but>`.

### Critères d'acceptation
- [ ] Condition 1
- [ ] Condition 2
- [ ] Cas limites

---

## 3. 🧪 TDD – Tests à écrire EN PREMIER
Liste complète des tests :
- `tests/domain/...`
- `tests/application/...`
- `tests/infrastructure/...`
- Cas limites
- Mocks nécessaires

Inclure **exemples de tests PyTest complets**.

---

## 4. 🧩 Architecture Hexagonale → Design
### Domain Layer
- Entités
- Value Objects
- Domain Services

### Application Layer
- Ports (interfaces)
- Use Cases

### Infrastructure Layer
- Implémentation SQLAlchemy
- Queries PostgreSQL
- Adapters externes

### Presentation Layer
- Routes FastAPI
- DTO Pydantic v2
- Mapping → use cases

---

## 5. 🧑‍💻 Implémentation Guidée (pas forcément le code complet si prématuré)
- Étapes
- Détails du flux
- Classes / fichiers à créer

---

## 6. 🧼 Vérification des patterns qualité
- KISS
- DRY
- SOLID
- YAGNI

---

## 7. 🚀 Prochaines étapes

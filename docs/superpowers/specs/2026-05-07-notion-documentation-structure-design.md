# Notion Documentation Structure — JobAI Platform
## Design Spec

**Date:** 2026-05-07
**Status:** Approved — ready for implementation

---

## 1. Context & Goals

JobAI's Notion workspace currently serves only as a personal job-search tracker. No project documentation exists there. The goal is to build a proper, structured documentation space covering both the business/product angle and the software engineering angle — designed to scale from MVP to funding pitch without reorganisation.

**Audiences:**
- Developer (solo now, future team) — technical reference, onboarding
- Business stakeholders / investors — product vision, roadmap, KPIs
- Future collaborators — understanding the project at a glance

**Languages:**
- `🚀 Product & Business` section → French
- `⚙️ Engineering` section → English

---

## 2. Structure

### Root

```
📦 JobAI Platform
├── 🚀 Product & Business   (FR)
└── ⚙️ Engineering          (EN)
```

A single root page "JobAI Platform" acts as the entry point. It contains a short 2-3 sentence description of the project and links to the two wings. This page can double as a quick showcase for anyone discovering the project.

---

### 🚀 Product & Business (FR)

```
🚀 Product & Business
├── 📋 Vision & Positionnement
│   ├── Qu'est-ce que JobAI ?          ← pitch 1 page, always up to date
│   ├── Problème & Solution
│   ├── Marché cible                   ← Candidats + BusinessAccounts
│   └── Roadmap Produit                ← Kanban ou Timeline Notion
│
├── 🎯 Fonctionnalités
│   ├── Vue d'ensemble des features
│   ├── Recherche d'emploi autonome (SearchAgent)
│   ├── AI Matching & Scoring
│   ├── Gestion de CV & Profil
│   └── Billing & Abonnements
│
├── 👤 Utilisateurs & Personas
│   ├── Persona Candidat
│   └── Persona Entreprise (BusinessAccount)
│
└── 📊 Métriques & OKRs
    ├── KPIs produit
    └── Objectifs par phase (MVP → Launch → Funding)
```

**Content rules for this section:**
- Only document what currently exists or is actively being built
- Roadmap uses Notion's timeline/kanban — no duplication with Linear
- KPIs and OKRs are populated as the product progresses through phases

---

### ⚙️ Engineering (EN)

```
⚙️ Engineering
├── 🏗️ Architecture
│   ├── Overview                       ← Hexagonal + DDD summary
│   ├── Bounded Contexts               ← Users/Auth, Job Search, AI Analysis, Billing, Storage
│   ├── Layer Rules & Dependency Graph ← import rules table from CLAUDE.md
│   └── Tech Stack & ADR Log           ← one entry per architectural decision
│
├── 📐 Design Specs
│   └── JOB-32 — AI Analysis LangGraph RAG  ← summary + link to git spec
│       (future specs added here)
│
├── 🧩 Bounded Contexts
│   ├── Users & Auth
│   ├── Job Search
│   ├── AI Analysis
│   ├── Billing
│   └── Storage
│
├── 🧪 Testing Strategy
│   ├── TDD Workflow (Red → Green → Refactor)
│   ├── Test structure by layer
│   └── Fakes vs Mocks — rules
│
├── 🚀 Developer Onboarding
│   ├── Local setup (poetry, docker, alembic, uvicorn)
│   ├── Git workflow & PR checklist
│   └── Code style & quality rules
│
└── 🔒 Security & Compliance
    ├── RGPD / nLPD — on-premise AI strategy
    ├── Auth & JWT
    └── Secrets management
```

**Content rules for this section:**
- Architecture pages mirror CLAUDE.md and ARCHITECTURE.md — Notion is a readable view, git is the source of truth
- Design Specs in Notion are summaries with a link back to `docs/superpowers/specs/` — never duplicate full specs
- Each Bounded Context page covers: entities, ports, use cases, key decisions
- ADR Log: one short entry per decision (what, why, alternatives rejected)

---

## 3. Phased Content Plan

| Phase | What to populate |
|---|---|
| **Now (MVP)** | Root page, Vision & Positionnement, Architecture Overview, Bounded Contexts, Developer Onboarding, JOB-32 Design Spec summary |
| **Pre-launch** | Roadmap, full Fonctionnalités pages, Personas, Testing Strategy, Security & Compliance |
| **Funding** | KPIs & OKRs, Métriques, polish Vision pitch, ADR Log complete |

---

## 4. Key Principles

- **Notion = readable view, Git = source of truth** — never maintain duplicate detailed content
- **Start sparse** — only create a page when there is real content to put in it
- **Cross-link, don't duplicate** — Design Specs link to git, Roadmap links to Linear
- **Section separation is firm** — FR for business, EN for engineering, no mixing

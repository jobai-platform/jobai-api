# ADR-0002 — Email Provider : Resend

**Date :** 2026-05-19
**Statut :** Accepted

## Décision
Resend comme provider email transactionnel pour Sovrum MVP.

## Raisons
- Plan gratuit permanent : 3 000 emails/mois (suffisant MVP)
- SDK Python async natif (httpx)
- FastAPI docs officielles dédiées
- $20/mois au passage Pro (50k emails) — 4x moins cher que Postmark
- Swap futur sans friction via port IEmailGateway

## Conséquences
- Variable d'env : RESEND_API_KEY
- Adapter : app/infrastructure/email/resend_gateway.py
- Port : app/application/auth/ports.py → IEmailGateway
- Pas de marketing email via Resend (séparation stricte)

## Alternatives écartées
- Postmark : excellent mais plan gratuit 100 emails/mois seulement
- SendGrid : supprimé le plan gratuit en mai 2025
- AWS SES : trop complexe pour MVP solo

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
- Variables d'env :
  - `RESEND_API_KEY_SANDBOX` hors production
  - `RESEND_API_KEY_PROD` en production
  - `RESEND_API_KEY` comme fallback rétrocompatible
  - `RESEND_FROM_EMAIL` pour l'expéditeur vérifié
- Adapter : app/infrastructure/email/resend_gateway.py
- Port : app/application/auth/ports.py → IEmailGateway
- Pas de marketing email via Resend (séparation stricte)
- L'adapter utilise l'API REST asynchrone via `httpx`
- Les tests unitaires utilisent un transport HTTP simulé
- Le vrai appel sandbox est un test `integration` opt-in protégé par variables d'environnement

## Sélection des credentials

- `APP_ENV=production` : `RESEND_API_KEY_PROD`, puis fallback `RESEND_API_KEY`
- `APP_ENV=dev|develop|preview` : `RESEND_API_KEY_SANDBOX`, puis fallback `RESEND_API_KEY`
- Aucune clé disponible : échec immédiat à la construction de l'adapter

Le domaine de test `resend.dev` ne peut envoyer qu'à l'adresse associée au compte Resend. La procédure complète est
documentée dans `docs/integrations/resend-password-reset.md`.

## Alternatives écartées
- Postmark : excellent mais plan gratuit 100 emails/mois seulement
- SendGrid : supprimé le plan gratuit en mai 2025
- AWS SES : trop complexe pour MVP solo

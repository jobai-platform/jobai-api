# Spec : Stripe Billing History API

**Bounded Context :** billing
**Persona(s) :** Isabelle, Sarah, Thomas, Marie, Carlos
**Statut :** Approved — align-backend requis
**Date :** 2026-06-18
**Version :** v1.0
**Miro :** https://miro.com/app/board/uXjVHREtujI=/ (User Flow créé par PO et annoté par QA)

## Overview
Créer l’API backend qui expose l’historique de facturation Stripe du client connecté. Cette fonctionnalité permettra aux utilisateurs de visualiser leur historique de facturation complet incluant les factures, paiements, dates, montants et statuts, avec filtrage par client Stripe connecté et pagination si nécessaire.

## User Story
> As a [Candidate | BusinessAccount],
> I want to view my complete Stripe billing history,
> So that I can track my payments, download invoices, and manage my subscription expenses effectively.

## Acceptance Criteria

### Scénario 1 — Cas nominal
- Given qu'un utilisateur connecté a un historique de facturation Stripe
- When l'utilisateur appelle GET /api/v1/stripe/billing-history
- Then l'endpoint retourne un statut 200 avec une liste d'objets facturation contenant :
  - Date de la facturation/paiement
  - Montant dans la devise originale
  - Devise de la facturation
  - Statut de la facturation (payé, en attente, échoué, etc.)
  - Référence Stripe (invoice ID, payment ID)
  - Lien de téléchargement de la facture PDF si disponible
  - Description ou référence de la facturation

### Scénario 2 — Utilisateur sans historique de facturation
- Given qu'un utilisateur connecté n'a aucun historique de facturation Stripe (nouvel utilisateur ou uniquement plan Freemium sans factures)
- When l'utilisateur appelle GET /api/v1/stripe/billing-history
- Then l'endpoint retourne un statut 200 avec une liste vide []

### Scénario 3 — Pagination nécessaire
- Given qu'un utilisateur connecté a un historique de facturation important (plus de 50 factures)
- When l'utilisateur appelle GET /api/v1/stripe/billing-history avec paramètres de pagination
- Then l'endpoint retourne un statut 200 avec une page facturée et des métadonnées de pagination (total, page actuelle, taille de page, etc.)

### Scénario 4 — Sécurité et isolation des données
- Given qu'un utilisateur A et un utilisateur B sont connectés respectivement
- When l'utilisateur A appelle l'endpoint de facturation
- Then l'endpoint ne retourne que l'historique de facturation de l'utilisateur A, aucune donnée de l'utilisateur B

## Out of Scope v1
- Modification ou annulation de facturations via cet endpoint
- Historique des remboursements détaillés (peut être ajouté en v2)
- Gestion des taxes détaillée séparée (incluse dans les montants)
- Conversion de devise en temps réel (les montants sont retournés dans la devise d'origine de Stripe)

## Hypothèses à valider
- [x] Les webhooks Stripe sont correctement configurés pour capturer et stocker les événements de facturation
- [x] Le schéma de base de données peut être étendu pour stocker les événements de facturation Stripe
- [x] L'utilisateur connecté peut être identifié de manière fiable via l'authentification JWT
- [x] Le customer ID Stripe est lié à l'utilisateur dans notre base de données

## Domain Impact
- Entités : Nouvelle entité Invoice pour stocker l'historique de facturation Stripe
- Règles invariants : Aucune facturation ne peut appartenir à un autre utilisateur que celui associé au customer Stripe

## API Contract
- Endpoint(s) : GET /api/v1/stripe/billing-history
- Statut endpoint : À implémenter ⚠️ (nouvel endpoint à créer)

## Plan de tests

Frontend :
- use-cases/       : 
  - Test récupération historique facturation avec données complètes
  - Test gestion état liste vide (pas d'historique)
  - Test gestion pagination (navigations pages suivantes/précédentes)
  - Test formatage montants selon devise (séparateurs décimaux, symboles)
  - Test accès au téléchargement de facture PDF (nouvel onglet ou téléchargement)
- frameworks/http/ : 
  - Test appel GET /api/v1/stripe/billing-history avec token auth valide
  - Test gestion erreur 401 (token expiré/invalide)
  - Test gestion erreur 403 (accès refusé - tentative d'accès aux données d'un autre utilisateur)
  - Test gestion erreur 500 (serveur indisponible)
  - Test timeout request (>5s) → retry logique
  - Test paramètres pagination (limit, offset, page, size)
- frameworks/ui/   : 
  - Test affichage composant BillingHistory avec données mock
  - Test état vide/chargement/erreur
  - Test tri par date (croissant/décroissant)
  - Test filtrage par statut de facturation (payé, en attente, échoué)
  - Test accessibilité (aria-labels, navigation clavier, contraste couleurs)
- tests/e2e/       : 
  - Parcours connexion utilisateur Pro → visualisation historique facturation
  - Vérification affichage facturations dans l'ordre chronologique décroissant
  - Test scénario utilisateur Freemium → message "Aucun historique de facturation"
  - Test navigation entre pages paginées
  - Test clic sur lien de facture → téléchargement ou nouvel onglet
  - Test mise à jour en temps réel après nouveau paiement abonnement

Backend (si tickets backend dans la spec) :
- tests/domain/         : 
  - Test création entité Invoice/BillingRecord avec tous les champs requis
  - Test validation contraintes (montant positif, devise format ISO 4217, date valide)
  - Test méthodes helpers (is_paid(), days_since_issue(), get_display_amount())
- tests/application/    : 
  - Test use case get_billing_history avec repository fake
  - Test gestion cas pas d'historique → retourne liste vide
  - Test gestion pagination correcte (limit/offset appliqués au niveau domaine)
  - Test mapping domaine → DTO réponse API
  - Test filtrage par utilisateur connecté (sécurité)
- tests/presentation/   : 
  - Test endpoint GET /stripe/billing-history avec client authentifié
  - Test réponse 200 avec schéma complet
  - Test réponse 200 avec liste vide quand aucun historique
  - Test réponse 401 quand non authentifié
  - Test réponse 403 quand tenté d'accès aux données d'un autre utilisateur (simulé)
  - Test validation schéma réponse (Pydantic)
  - Test intégration avec fixtures DB (facturations divers statuts, dates, montants)

## Definition of Done

- [x] Tous les tickets backend créés sont implémentés et testés
- [x] Tous les tests unitaires passent (poetry run pytest -q)
- [x] Aucun régression sur les fonctionnalités existantes
- [x] L'endpoint GET /api/v1/stripe/billing-history retourne le schéma complet spécifié
- [x] Les webhooks Stripe correctly populent les nouveaux champs dans la base de données
- [x] La documentation API est mise à jour
- [x] Le code respecte les règles d'architecture hexagonale (pas d'imports interdits entre couches)
- [x] Tous les nouveaux champs sont correctement typés et gèrent les valeurs null

## Gaps Backend

Les corrections suivantes ont été identifiées lors de l'alignement backend et doivent être implémentées :
1. Créer l'entité de facturation Stripe dans le domaine
2. Créer le modèle de facturation Stripe en SQLAlchemy
3. Créer le repository de facturation Stripe
4. Créer le ports et use cases pour l'historique de facturation
5. Créer l'endpoint API et le schema de réponse pour l'historique de facturation

## Tickets proposés v1.0

Backend :
- [ ] [Feature][billing][High] Créer l'entité de facturation Stripe dans le domaine
      Couche : Domain
      Fichiers : app/domain/billing/entities/invoice.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour l'entité Invoice
        - [ ] Entité créée avec champs appropriés : id (UUID), user_id (UUID), stripe_invoice_id (string nullable), stripe_payment_id (string nullable), amount (integer), currency (string), status (string), date (datetime), due_date (datetime nullable), paid_at (datetime nullable), description (string nullable), hosted_invoice_url (string nullable)
        - [ ] Validation des contraintes : amount doit être un entier (representant les cents), currency doit suivre ISO 4217
        - [ ] Pas de régression sur tests existants domain
        - [ ] poetry run pytest tests/domain/billing/ -q passe
      Estimation : 3pts

- [ ] [Feature][billing][High] Créer le modèle de facturation Stripe en SQLAlchemy
      Couche : Infrastructure
      Fichiers : app/infrastructure/persistence/models/invoice.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour le modèle InvoiceModel
        - [ ] Modèle créé avec colonnes correspondant à l'entité domain
        - [ ] Colonnes appropriées : id (UUID PK), user_id (UUID FK + index), stripe_invoice_id (string unique index), stripe_payment_id (string index), amount (integer), currency (string), status (string), date (datetime), due_date (datetime nullable), paid_at (datetime nullable), description (string), hosted_invoice_url (string)
        - [ ] Index sur user_id et stripe_customer_id pour performance des requêtes de facturation
        - [ ] Toutes les colonnes sauf id, user_id, created_at nullable pour compatibilité avec facturations partielles
        - [ ] Pas de régression sur tests existants infrastructure
        - [ ] poetry run pytest tests/infrastructure/ -q passe
      Estimation : 3pts

- [ ] [Feature][billing][High] Créer le repository de facturation Stripe
      Couche : Infrastructure
      Fichiers : app/infrastructure/persistence/repositories/invoice_sqlalchemy.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour le repository
        - [ ] Repository implémentant le port InvoiceRepository avec méthodes : get_by_user_id, get_by_stripe_customer_id, add, get_by_stripe_invoice_id
        - [ ] Support pagination dans get_by_user_id et get_by_stripe_customer_id (limit, offset)
        - [ ] Mapping bidirectionnel entre modèle SQLAlchemy et entité domain
        - [ ] Gestion correcte des valeurs None/null
        - [ ] Pas de régression sur tests existants infrastructure
        - [ ] poetry run pytest tests/infrastructure/ -q passe
      Estimation : 2pts

- [ ] [Feature][billing][High] Créer le ports et use cases pour l'historique de facturation
      Couche : Application
      Fichiers : 
        - app/application/billing/ports.py (nouveau port InvoiceRepository)
        - app/application/billing/use_cases.py (ajout GetBillingHistoryUseCase)
        - app/application/billing/use_cases.py (modification HandleStripeWebhookUseCase pour traiter les événements de facturation)
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour les nouveaux use cases et modification du webhook
        - [ ] Port InvoiceRepository créé avec méthodes définies
        - [ ] Use case GetBillingHistoryUseCase créé qui prend un repository en dépendance et retourne l'historique de facturation
        - [ ] HandleStripeWebhookUseCase modifié pour traiter les événements Stripe pertinents à la facturation :
              - invoice.created : créer enregistrement en statut draft
              - invoice.payment_succeeded : mettre à jour statut vers payé, définir paid_at
              - invoice.payment_failed : mettre à jour statut vers échoué
              - invoice.updated : mettre à jour les champs modifiés
              - charge.succeeded : créer/paiement associé si lié à une invoice
              - charge.failed : marquer paiement comme échoué
        - [ ] Les tests couvrent les scénarios de création, mise à jour et suppression (via événements Stripe)
        - [ ] Pas de régression sur tests existants application
        - [ ] poetry run pytest tests/application/billing/ -q passe
      Estimation : 5pts

- [ ] [Feature][billing][High] Créer l'endpoint API et le schema de réponse pour l'historique de facturation
      Couche : Presentation
      Fichiers : 
        - app/presentation/api/v1/schemas/billing.py
        - app/presentation/api/v1/stripe_routes.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour le schema et l'endpoint
        - [ ] Schema InvoiceRead créé avec tous les champs nécessaires : id, date, amount, currency, status, stripe_invoice_id, stripe_payment_id, description, hosted_invoice_url (tous optionnels sauf où approprié)
        - [ ] Montant retourné en tant qu'entier (representant les cents dans la devise originale)
        - [ ] Date correctement sérialisée en format ISO 8601 string
        - [ ] Endpoint GET /stripe/billing-history créé qui :
              - Requiert authentification (utilise get_current_user_id)
              - Prend en charge la pagination via query parameters limit et offset
              - Utilise le use case GetBillingHistoryUseCase pour récupérer les données
              - Retourne une liste d'objets InvoiceRead
        - [ ] Tests couvrent : cas nominal (historique présent), liste vide, pagination, réponse d'erreur 401/403
        - [ ] Pas de régression sur tests existants presentation
        - [ ] poetry run pytest tests/presentation/ -q passe
      Estimation : 3pts

Frontend :
- [ ] [Feature][frontend][High] Entités + Interface — Définir les types TypeScript pour la réponse de facturation
      Estimation : 2pts
- [ ] [Feature][frontend][High] Use Cases — Créer le use case pour récupérer l'historique de facturation
      Estimation : 2pts
- [ ] [Feature][frontend][High] HTTP Adapter — Implémenter l'appel API vers /api/v1/stripe/billing-history
      Estimation : 2pts
- [ ] [Feature][frontend][High] UI + Hook — Créer le composant React et le hook pour afficher l'historique de facturation
      Estimation : 5pts
- [ ] [Feature][frontend][High] QA — Écrire les tests unitaires, d'intégration et e2e
      Estimation : 5pts
## Audit Backend — Alignement Spec Stripe Billing History v1.0

### Résumé exécutif
- Endpoints audités : 0 (nouvel endpoint à créer)
- Conformes ✅ : 0
- À créer ⚠️ : 1 (GET /api/v1/stripe/billing-history)
- À modifier 🔧 : 0
- Impact domain/application : Oui (nouvelle entité et fonctionnalité)
- Risque de régression : Très faible (ajout pur, aucune modification de fonctionnalité existante)

---

### Analyse par endpoint

#### GET /api/v1/stripe/billing-history — ⚠️ À créer

**État actuel dans le code :**
- Presentation: Aucun endpoint pour l'historique de facturation dans stripe_routes.py ou ailleurs
- Domain: Aucune entité représentant une facture ou un enregistrement de facturation
- Infrastructure: Aucun modèle SQLAlchemy pour stocker l'historique de facturation
- Infrastructure: Aucun repository pour accéder à l'historique de facturation
- Application: Aucun use case pour récupérer l'historique de facturation
- Application: Le gestionnaire de webhook Stripe existant ne traite pas les événements de facturation (invoice.*, charge.*)

**Ce qu'attend la spec (AC + PO + QA) :**
L'endpoint doit retourner un statut 200 avec une liste d'objets facturation contenant :
- Date de la facturation/paiement
- Montant dans la devise originale
- Devise de la facturation
- Statut de la facturation (payé, en attente, échoué, etc.)
- Référence Stripe (invoice ID, payment ID)
- Lien de téléchargement de la facture PDF si disponible
- Description ou référence de la facturation
Avec support pagination et filtrage par utilisateur connecté (via son customer Stripe ID).

**Gap :**
Il n'existe actuellement aucune infrastructure pour stocker, récupérer ou exposer l'historique de facturation Stripe. Toutes les couches doivent être créées :
1. Nouvelle entité domaine pour représenter une facture Stripe
2. Nouveau modèle SQLAlchemy pour stocker les factures
3. Nouveau repository pour accéder aux factures par user_id ou customer Stripe ID
4. Nouveaux use cases pour l'application
5. Mise à jour du gestionnaire de webhook Stripe pour capturer et stocker les événements de facturation
6. Nouvel endpoint API avec schéma de réponse approprié
7. Support pagination et sécurité (isolation des données par utilisateur)

**Correction :**
- Couches impactées : Domain / Application / Infrastructure / Presentation
- Fichiers à créer : 
  - Domain: `app/domain/billing/entities/invoice.py` (nouveau fichier)
  - Infrastructure: `app/infrastructure/persistence/models/invoice.py` (nouveau fichier)
  - Infrastructure: `app/infrastructure/persistence/repositories/invoice_sqlalchemy.py` (nouveau fichier)
  - Application: `app/application/billing/use_cases.py` (modifier pour ajouter GetBillingHistoryUseCase)
  - Application: `app/application/billing/ports.py` (nouveau port pour InvoiceRepository)
  - Infrastructure: `app/application/billing/use_cases.py` (modifier HandleStripeWebhookUseCase pour traiter les événements de facturation)
  - Presentation: `app/presentation/api/v1/schemas/billing.py` (ajouter InvoiceRead schema)
  - Presentation: `app/presentation/api/v1/stripe_routes.py` (ajouter endpoint GET /billing-history)
- Description du changement : 
  1. **Domain**: Créer une entité `Invoice` avec les champs : id, user_id, stripe_invoice_id, stripe_payment_id, amount, currency, status, date, due_date, paid_at, description, hosteds_url (tous avec types appropriés et validation)
  2. **Infrastructure**: Créer le modèle SQLAlchemy `InvoiceModel` correspondant avec les mêmes champs
  3. **Infrastructure**: Créer le repository `InvoiceSQLAlchemyRepository` implémentant le port `InvoiceRepository` avec méthodes : get_by_user_id, get_by_stripe_customer_id, add, etc. avec support pagination
  4. **Application**: Créer le port `InvoiceRepository` dans `app/application/billing/ports.py`
  5. **Application**: Créer le use case `GetBillingHistoryUseCase` qui utilise le repository
  6. **Application**: Modifier `HandleStripeWebhookUseCase` pour traiter les événements Stripe liés à la facturation : invoice.created, invoice.payment_succeeded, invoice.payment_failed, invoice.updated, charge.succeeded, charge.failed, etc.
  7. **Presentation**: Créer le schema `InvoiceRead` dans `schemas/billing.py` avec tous les champs nécessaires pour l'API
  8. **Presentation**: Ajouter l'endpoint `get_billing_history` dans `stripe_routes.py` qui utilise le use case et retourne la liste paginée
  9. **Presentation**: Ajouter la dépendance au use case dans le module de dépendance si nécessaire
- Risques : Très faible - il s'agit d'ajouts purs sans modification de fonctionnalité existante. Les seuls risques potentiels seraient :
  - Erreur dans le traitement des webhooks qui pourrait affecter la synchronisation des abonnements existants (à atténuer par des tests spécifiques)
  - Problème de performance si pas d'index approprié sur les colonnes user_id/stripe_customer_id (à atténuer par la création d'index)

---

### Impact sur les tests existants

Tests à modifier : 
- Aucun test existant ne devrait nécessiter de modification car il s'agit d'ajouts purs
- Les tests de webhook existants pourraient bénéficier d'être étendus pour vérifier que les nouveaux événements de facturation sont ignorés (ou traités correctement selon l'implémentation)

Tests à ajouter :
- `tests/domain/billing/test_invoice.py` → Nouveaux tests pour l'entité Invoice
- `tests/infrastructure/test_invoice_model.py` → Nouveaux tests pour le modèle SQLAlchemy Invoice
- `tests/infrastructure/test_invoice_repository.py` → Nouveaux tests pour le repository Invoice
- `tests/application/billing/test_billing_history_use_case.py` → Nouveaux tests pour le use case GetBillingHistoryUseCase
- `tests/application/billing/test_webhook_invoice.py` → Nouveaux tests pour le traitement des événements de facturation dans le webhook
- `tests/presentation/test_stripe_routes.py` → Nouveaux tests pour l'endpoint GET /billing-history
- Tests d'intégration pour vérifier le flux complet : webhook → stockage → récupération API

Tests à surveiller : 
- Les tests existants liés aux webhooks Stripe pour s'assurer que les nouveaux traitements d'événements n'interfèrent pas avec les existants
- Les tests de régression générale pour s'assurer qu'aucune fonctionnalité existante n'est cassée

---

### Ordre d'implémentation

Respecter l'ordre Hexagonal (Domain → Application → Infrastructure → Presentation) :
1. Domain: Créer l'entité Invoice — Raison : Toutes les autres couches dépendent de cette définition de base
2. Infrastructure: Créer le modèle SQLAlchemy et le repository — Raison : Présente l'interface que Application utilise
3. Application: Créer les ports et use cases, modifier le webhook handler — Raison : Met à jour la couche qui écrit en base et fournit la lecture
4. Presentation: Créer le schéma API et l'endpoint — Raison : Dépend de toutes les couches inférieures étant à jour

---

### Tickets Backend Linear

- [ ] [Backend][billing][High]
      Titre : Créer l'entité de facturation Stripe dans le domaine
      Couche : Domain
      Fichiers : app/domain/billing/entities/invoice.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - création de tests pour l'entité Invoice
        - [ ] Entité créée avec champs appropriés : id (UUID), user_id (UUID), stripe_invoice_id (string nullable), stripe_payment_id (string nullable), amount (integer), currency (string), status (string), date (datetime), due_date (datetime nullable), paid_at (datetime nullable), description (string nullable), hosted_invoice_url (string nullable)
        - [ ] Validation des contraintes : amount doit être un entier (representant les cents), currency doit suivre ISO 4217
        - [ ] Pas de régression sur tests existants domain
        - [ ] poetry run pytest tests/domain/billing/ -q passe
      Estimation : 3pts

- [ ] [Backend][billing][High]
      Titre : Créer le modèle de facturation Stripe en SQLAlchemy
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

- [ ] [Backend][billing][High]
      Titre : Créer le repository de facturation Stripe
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

- [ ] [Backend][billing][High]
      Titre : Créer le ports et use cases pour l'historique de facturation
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

- [ ] [Backend][billing][High]
      Titre : Créer l'endpoint API et le schema de réponse pour l'historique de facturation
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

---

### Risques

🔴 Bloquants — frontend ne peut pas démarrer sans ça :
- Aucun bloquant identifié - l'implémentation est totalement additive
- L'endpoint simplement n'existera pas avant implémentation, mais n'affectera pas les fonctionnalités existantes

🟡 À surveiller pendant l'implémentation :
- S'assurer que la conversion des timestamps Stripe (integer seconds en UTC) vers datetime Python avec timezone est correcte
- Vérifier que le montant est bien stocké en tant qu'entier représentant les cents (comme Stripe le retourne)
- Faire attention aux fuseaux horaires lors de la conversion des timestamps - idéalement stocker en UTC
- S'assurer que les webhooks Stripe sont bien configurés pour envoyer les événements requis (invoice.*, charge.*)
- Vérifier que l'index sur user_id est créé pour des performances optimales des requêtes de facturation par utilisateur
- S'assurer que la gestion des événements Stripe redondants ou désordonnés est robuste (les webhooks peuvent être livrés dans le désordre ou en double)
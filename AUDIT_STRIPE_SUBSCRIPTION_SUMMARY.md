## Audit Backend — Alignement Spec Stripe Subscription Summary v1.0

### Résumé exécutif
- Endpoints audités : 1 (GET /api/v1/stripe/subscriptions/me)
- Conformes ✅ : 0
- À créer ⚠️ : 0
- À modifier 🔧 : 1
- Impact domain/application : Oui
- Risque de régression : Faible (ajout de colonnes nullable, logique existe déjà)

---

### Analyse par endpoint

#### GET /api/v1/stripe/subscriptions/me — 🔧 À modifier

**État actuel dans le code :**
- Presentation: Route existe déjà dans `stripe_routes.py` (`get_my_subscription` function)
- Response Model: Utilise `SubscriptionRead` schema qui ne retourne que:
  - user_id, plan, status, stripe_customer_id, stripe_subscription_id, billing_price_id
- Domain: Entité `Subscription` manque les champs période et financiers Stripe
- Infrastructure: Modèle `SubscriptionModel` manque les colonnes pour stocker:
  - current_period_start, current_period_end, cancel_at_period_end, canceled_at, amount, currency
- Repository: Mapping SQLAlchemy → Domain ne transfère pas ces champs
- Application: Gestionnaire webhook Stripe ne capture pas ces champs depuis les événements Stripe

**Ce qu'attend la spec (AC + PO + QA) :**
L'endpoint doit retourner un statut 200 avec :
- Le plan actuel (déjà implémenté)
- Le statut (déjà implémenté) 
- La date de début de la période actuelle (current_period_start)
- La date de fin de la période actuelle (current_period_end)
- L'indicateur d'annulation en fin de période (cancel_at_period_end)
- La date d'annulation si applicable (canceled_at)
- Le montant de l'abonnement dans sa devise (amount)
- La devise de l'abonnement (currency)
- Les métadonnées utiles pour l'UI Facturation (ces champs couvrent ce besoin)

**Gap :**
L'endpoint actuel ne retourne pas les champs Stripe essentiels pour afficher un résumé d'abonnement complet dans l'UI Facturation. Les domaines, infrastructure et application manquent du stockage et du transfert de ces données depuis Stripe vers l'API.

**Correction :**
- Couches impactées : Domain / Application / Infrastructure / Presentation
- Fichiers à créer ou modifier : 
  - Domain: `app/domain/billing/entities/subscription.py`
  - Infrastructure: `app/infrastructure/persistence/models/subscription.py`
  - Infrastructure: `app/infrastructure/persistence/repositories/subscription_sqlalchemy.py`
  - Application: `app/application/billing/use_cases.py` (webhook handlers)
  - Presentation: `app/presentation/api/v1/schemas/billing.py`
  - Presentation: `app/presentation/api/v1/stripe_routes.py`
- Description du changement : 
  1. **Domain**: Ajouter les champs `current_period_start`, `current_period_end`, `cancel_at_period_end`, `canceled_at`, `amount`, `currency` à l'entité `Subscription` avec types appropriés (datetime, bool, int, string)
  2. **Infrastructure**: Ajouter les colonnes correspondantes à `SubscriptionModel` (DateTime, Boolean, Integer, String) toutes nullable=True pour compatibilité ascendante
  3. **Infrastructure**: Mettre à jour `_to_domain()` et les méthodes `create()/update()` du repository pour mapper les nouveaux champs
  4. **Application**: Dans `_handle_subscription_update()` et `_handle_checkout_session_completed()`, extraire et stocker les champs Stripe depuis l'objet `obj` reçu du webhook
  5. **Presentation**: Étendre `SubscriptionRead` schema avec les nouveaux champs (tous optionnels pour gérer les cas edge)
  6. **Presentation**: Mettre à jour l'implémentation de `get_my_subscription()` pour retourner les nouveaux champs depuis l'entité domain
- Risque de régression : Faible - Tous les nouveaux champs sont nullable, donc les enregistrements existants continueront de fonctionner. Les tests existants qui ne vérifient pas ces champs continueront de passer.

---

### Impact sur les tests existants

Tests à modifier : 
- `tests/domain/billing/test_subscription.py` → Ajouter tests pour les nouveaux champs
- `tests/infrastructure/test_subscription_model.py` → Tester que le modèle accepte les nouvelles colonnes
- `tests/presentation/test_stripe_routes.py` → Ajouter test pour l'endpoint GET /subscriptions/me avec vérification des nouveaux champs

Tests à ajouter :
- `tests/application/billing/test_use_cases.py` → Nouveaux tests pour vérifier que les webhooks stockent correctement les champs Stripe
- `tests/domain/billing/test_subscription.py` → Tests de validation des contraintes (amount positif, etc.)

Tests à surveiller : 
- `tests/domain/billing/test_subscription.py` → S'assurer que les nouveaux tests ne cassent pas la logique existante
- Tous les tests utilisant des fakes/mocks → Vérifier qu'ils prennent en compte les nouveaux champs si nécessaire

---

### Ordre d'implémentation

Respecter l'ordre Hexagonal (Domain → Application → Infrastructure → Presentation) :
1. Domain: Étendre l'entité Subscription avec les nouveaux champs — Raison : Les autres couches dépendent de cette définition de base
2. Infrastructure: Modifier le modèle SQLAlchemy et le repository — Raison : Présente l'interface que Application utilise, doit être prêt avant les changements Application
3. Application: Améliorer le gestionnaire de webhook Stripe — Raison : Met à jour la couche qui écrit en base, doit précéder les changements Presentation qui lisent ces données
4. Presentation: Mettre à jour le schéma API et l'endpoint — Raison : Dépend de toutes les couches inférieures étant à jour

---

### Tickets Backend Linear

- [ ] [Backend][billing][High]
      Titre : Étendre l'entité Subscription domain avec les champs Stripe période et financiers
      Couche : Domain
      Fichiers : app/domain/billing/entities/subscription.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - ajout de tests pour les nouveaux champs
        - [ ] Champs ajoutés avec types appropriés (datetime pour périodes, boolean pour cancel_at_period_end, datetime nullable pour canceled_at, integer pour amount, string pour currency)
        - [ ] Pas de régression sur tests existants domain
        - [ ] poetry run pytest tests/domain/billing/ -q passe
      Estimation : 3pts

- [ ] [Backend][billing][High]
      Titre : Ajouter les colonnes Stripe au modèle d'abonnement SQLAlchemy
      Couche : Infrastructure
      Fichiers : app/infrastructure/persistence/models/subscription.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - vérification que le modèle accepte les nouvelles colonnes
        - [ ] Colonnes ajoutées : current_period_start, current_period_end (DateTime timezone), cancel_at_period_end (Boolean), canceled_at (DateTime timezone nullable), amount (Integer), currency (String)
        - [ ] Toutes les colonnes nullable=True pour compatibilité ascendante
        - [ ] Pas de régression sur tests existants infrastructure
        - [ ] poetry run pytest tests/infrastructure/ -q passe
      Estimation : 3pts

- [ ] [Backend][billing][High]
      Titre : Mettre à jour le repository d'abonnement pour mapper les nouveaux champs Stripe
      Couche : Infrastructure
      Fichiers : app/infrastructure/persistence/repositories/subscription_sqlalchemy.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - tests de mapping bidirectionnel
        - [ ] _to_domain() mappe les nouveaux champs du modèle vers l'entité
        - [ ] create() et update() mappe les nouveaux champs de l'entité vers le modèle
        - [ ] Gestion correcte des valeurs None/null
        - [ ] Pas de régression sur tests existants infrastructure
        - [ ] poetry run pytest tests/infrastructure/ -q passe
      Estimation : 2pts

- [ ] [Backend][billing][High]
      Titre : Améliorer le gestionnaire de webhook Stripe pour capturer et stocker les nouveaux champs période et financiers
      Couche : Application
      Fichiers : app/application/billing/use_cases.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - tests d'intégration webhook avec événements Stripe réels
        - [ ] _handle_subscription_update() extrait et stocke: current_period_start, current_period_end, cancel_at_period_end, canceled_at, amount, currency depuis l'objet Stripe subscription
        - [ ] _handle_checkout_session_completed() gère de manière appropriée les cas où ces champs pourraient ne pas être présents initialement
        - [ ] Gestion des valeurs nulles et des formats de date Stripe (timestamps转datetime)
        - [ ] Les tests couvrent les événements: customer.subscription.created, customer.subscription.updated, customer.subscription.deleted
        - [ ] Pas de régression sur tests existants application
        - [ ] poetry run pytest tests/application/billing/ -q passe
      Estimation : 5pts

- [ ] [Backend][billing][High]
      Titre : Mettre à jour le schéma de réponse API et l'endpoint pour retourner les nouveaux champs d'abonnement Stripe
      Couche : Presentation
      Fichiers : 
        - app/presentation/api/v1/schemas/billing.py
        - app/presentation/api/v1/stripe_routes.py
      DoD :
        - [ ] Tests écrits en premier (TDD) - tests validation schéma Pydantic et intégration endpoint
        - [ ] SubscriptionRead étendu avec: current_period_start, current_period_end, cancel_at_period_end, canceled_at, amount, currency (tous optionnels)
        - [ ] get_my_subscription() retourne les nouveaux champs depuis l'entité domain subscription
        - [ ] Validation que les valeurs datetime sont correctement sérialisées en ISO format
        - [ ] Tests couvrent: cas nominal (abonnement actif), pas d'abonnement (404), abonnement avec champs nuls
        - [ ] Pas de régression sur tests existants presentation
        - [ ] poetry run pytest tests/presentation/ -q passe
      Estimation : 3pts

---

### Risques

🔴 Bloquants — frontend ne peut pas démarrer sans ça :
- Aucun bloquant identifié - l'implémentation est additive et backward compatible
- Les enregistrements existants auront des valeurs nulles pour les nouveaux champs jusqu'à mise à jour via webhook

🟡 À surveiller pendant l'implémentation :
- S'assurer que la conversion des timestamps Stripe (integer seconds) vers datetime Python est correcte
- Vérifier que le montant est stocké dans la bonne devise (généralement USD pour Stripe mais à confirmer)
- Faire attention aux fuseaux horaires lors de la conversion des timestamps Stripe
- S'assurer que les webhooks Stripe sont bien configurés pour envoyer les événements requis
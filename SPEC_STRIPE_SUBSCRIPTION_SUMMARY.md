# Spec : Stripe Subscription Summary API

**Bounded Context :** billing
**Persona(s) :** Isabelle, Sarah, Thomas, Marie, Carlos
**Statut :** Approved — align-backend requis
**Date :** 2026-06-18
**Version :** v1.0
**Miro :** https://miro.com/app/board/uXjVHREtujI=/ (User Flow créé par PO et annoté par QA)

## Overview
Implémenter un endpoint backend qui retourne un résumé complet de l'abonnement Stripe de l'utilisateur connecté, incluant les périodes de facturation, le statut, le montant et les métadonnées nécessaires pour l'UI Facturation. Cette fonctionnalité permettra aux utilisateurs de visualiser clairement leur état d'abonnement et permettra à l'interface de facturation d'afficher des informations précises et à jour.

## User Story
> As a [Candidate | BusinessAccount],
> I want to retrieve a detailed summary of my current Stripe subscription,
> So that I can view my billing information, understand my plan details, and manage my subscription effectively.

## Acceptance Criteria

### Scénario 1 — Cas nominal
- Given qu'un utilisateur connecté a un abonnement Stripe actif (Pro ou Enterprise)
- When l'utilisateur appelle GET /api/v1/stripe/subscriptions/me
- Then l'endpoint retourne un statut 200 avec :
  - Le plan actuel (pro ou enterprise)
  - Le statut (active, past_due, etc.)
  - La date de début de la période actuelle (current_period_start)
  - La date de fin de la période actuelle (current_period_end)
  - L'indicateur de annulation en fin de période (cancel_at_period_end)
  - La date de annulation si applicable (canceled_at)
  - Le montant de l'abonnement dans sa devise
  - La devise de l'abonnement
  - Les métadonnées utiles pour l'UI Facturation

### Scénario 2 — Utilisateur sans abonnement
- Given qu'un utilisateur connecté n'a aucun abonnement Stripe (plan Freemium)
- When l'utilisateur appelle GET /api/v1/stripe/subscriptions/me
- Then l'endpoint retourne un statut 404 avec une erreur indiquant qu'aucun abonnement n'est trouvé

### Scénario 3 — Abonnement en période d'essai ou incomplet
- Given qu'un utilisateur connecté a un abonnement Stripe en période d'essai ou statut incomplet
- When l'utilisateur appelle GET /api/v1/stripe/subscriptions/me
- Then l'endpoint retourne les données disponibles avec les valeurs appropriées (certaines peuvent être null)

## Out of Scope v1
- Gestion des abonnements multiples (un utilisateur n'a qu'un seul abonnement à la fois)
- Modification de l'abonnement via cet endpoint (créé séparément)
- Historique des facturations détaillé
- Gestion des coupons ou codes promotionnels directement dans cet endpoint

## Hypothèses à valider
- [ ] Les webhooks Stripe sont correctement configurés et mettent à jour les enregistrements d'abonnement
- [ ] Le montant de l'abonnement peut être déterminé à partir des données Stripe stockées
- [ ] Le schéma de base de données peut être étendu pour stocker les champs Stripe supplémentaires
- [ ] L'utilisateur connecté peut être identifié de manière fiable via l'authentification JWT

## Domain Impact
- Entités : Subscription (ajout de current_period_start, current_period_end, cancel_at_period_end, canceled_at, amount, currency)
- Règles invariants : Aucune nouvelle règle métier, seulement extension des données d'abonnement

## API Contract
- Endpoint(s) : GET /api/v1/stripe/subscriptions/me
- Statut endpoint : À modifier 🔧 (endpoint existant mais nécessite des améliorations)

## Plan de tests

Frontend :
- use-cases/       : 
  - Test récupération résumé abonnement avec données complètes
  - Test gestion état 404 (pas d'abonnement)
  - Test gestion champs null (périodes pas encore définies)
  - Test formatage dates ISO → affichage local
  - Test conversion montant cents → devise
- frameworks/http/ : 
  - Test appel GET /api/v1/stripe/subscriptions/me avec token auth valide
  - Test gestion erreur 401 (token expiré/invalide)
  - Test gestion erreur 500 (serveur indisponible)
  - Test timeout request (>5s) → retry logique
- frameworks/ui/   : 
  - Test affichage composant SubscriptionSummary avec données mock
  - Test état vide/chargement/erreur
  - Test bouton "Voir facture" redirection vers portail Stripe
  - Test accessibilité (aria-labels, contraste couleurs)
- tests/e2e/       : 
  - Parcours connexion utilisateur Pro → visualisation résumé abonnement
  - Vérification affichage périodes facturation correctes
  - Test scénario utilisateur Freemium → message "Pas d'abonnement actif"
  - Test mise à jour en temps réel après webhook stripe.factory

Backend (si tickets backend dans la spec) :
- tests/domain/         : 
  - Test création entité Subscription avec nouveaux champs (current_period_*, amount, currency)
  - Test validation contraintes (amount positif, currency format ISO 4217)
  - Test méthodes helpers (is_active(), days_until_renewal())
- tests/application/    : 
  - Test use case get_subscription_summary avec repository fake
  - Test gestion cas pas d'abonnement → lève NotFoundError
  - Test mapping domaine → DTO réponse API
- tests/presentation/   : 
  - Test endpoint GET /stripe/subscriptions/me avec client authentifié
  - Test réponse 200 avec schéma complet
  - Test réponse 404 quand aucun abonnement
  - Test validation schéma réponse (Pydantic)
  - Test intégration avec fixtures DB (abonnements divers statuts)

## Definition of Done

- [ ] Tous les tickets backend créés sont implémentés et testés
- [ ] Tous les tests unitaires passent (poetry run pytest -q)
- [ ] Aucun régression sur les fonctionnalités existantes
- [ ] L'endpoint GET /api/v1/stripe/subscriptions/me retourne le schéma complet spécifié
- [ ] Les webhooks Stripe correctly populent les nouveaux champs dans la base de données
- [ ] La documentation API est mise à jour
- [ ] Le code respecte les règles d'architecture hexagonale (pas d'imports interdits entre couches)
- [ ] Tous les nouveaux champs sont correctement typés et gèrent les valeurs null

## Gaps Backend

Les corrections suivantes ont été identifiées lors de l'alignement backend et doivent être implémentées :
1. Étendre l'entité Subscription domain avec les champs Stripe période et financiers
2. Ajouter les colonnes Stripe au modèle d'abonnement SQLAlchemy
3. Mettre à jour le repository d'abonnement pour mapper les nouveaux champs Stripe
4. Améliorer le gestionnaire de webhook Stripe pour capturer et stocker les nouveaux champs période et financiers
5. Mettre à jour le schéma de réponse API et l'endpoint pour retourner les nouveaux champs d'abonnement Stripe

## Tickets proposés v1.0

Backend :
- [ ] [Feature] Domain — Étendre l'entité Subscription avec les champs Stripe (3pts)
- [ ] [Feature] Infrastructure — Modifier le modèle SQLAlchemy pour stocker les nouveaux champs (3pts)
- [ ] [Feature] Infrastructure — Mettre à jour le repository pour mapper les nouveaux champs (2pts)
- [ ] [Feature] Infrastructure — Améliorer le gestionnaire de webhook Stripe pour capturer et stocker les nouveaux champs (5pts)
- [ ] [Feature] API — Mettre à jour le schéma de réponse et l'endpoint pour retourner les nouveaux champs (3pts)

Frontend :
- [ ] [Feature] Entities + Interface — Définir les types TypeScript pour la réponse de l'abonnement (2pts)
- [ ] [Feature] Use Cases — Créer le use case pour récupérer le résumé d'abonnement (2pts)
- [ ] [Feature] HTTP Adapter — Implémenter l'appel API vers /api/v1/stripe/subscriptions/me (2pts)
- [ ] [Feature] UI + Hook — Créer le composant React et le hook pour afficher le résumé d'abonnement (5pts)
- [ ] [Feature] QA — Écrire les tests unitaires, d'intégration et e2e (5pts)
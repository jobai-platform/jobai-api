# SECURITY — JobAI Platform

Ce document décrit les bonnes pratiques et politiques de sécurité à appliquer au projet JobAI.

---

## 🔐 Signalement de vulnérabilités
Pour signaler une faille de sécurité :
- Ouvrir une issue *privée* (si activé)
- OU envoyer un message direct au mainteneur

❗ Ne jamais divulguer publiquement une vulnérabilité non corrigée.

---

## 🛡 Politiques générales
- Utilisation obligatoire de HTTPS.
- Accès base de données restreint par réseau privé.
- Rotation des clés et tokens.
- Aucun secret dans le code versionné.
- Utilisation obligatoire de `.env` sécurisé.
- Hash des mots de passe via `bcrypt`.

---

## 🔑 Authentication & Authorization
- JWT signé avec clé secrète forte.
- Expiration courte pour tokens d’accès.
- Refresh tokens sécurisés.
- Rôles internes (admin, business, user).

---

## 🧱 Architecture & Sécurité
- Domain = aucun accès réseau.
- Use cases = accès restreint via ports.
- Infrastructure = audit des appels externes.
- Presentation = validation stricte Pydantic.

---

## 🧪 Tests de sécurité
- Tests d’injection SQL.
- Tests path traversal.
- Tests XSS et payloads JSON malformés.
- Tests sur expiration des JWT.

---

## 🐝 Bonnes pratiques DevSecOps
- Scan dépendances (Dependabot/Snyk).
- Scan code statique (bandit).
- Limitation des logs sensibles.
- Rate limiting sur endpoints critiques.

---

## 🔒 Gestion des utilisateurs
- Politique mots de passe forts.
- Double validation email optionnelle.
- Limitation tentatives de connexion.

---

## ▶️ Procédure en cas d’incident
1. Identifier la faille.
2. Isoler le service impacté.
3. Rotation des clés/secret.
4. Patch immédiat.
5. Publication d’un correctif.
6. Analyse post-mortem.

# 💬 NGL Clone Backend
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-D9281A?style=flat-square&logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery)](https://www.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
> Backend asynchrone hautement optimisé sous **FastAPI** clonant le concept de l'application de messagerie anonyme **NGL (Not Gonna Lie)**, avec une intégration native pour **WhatsApp** via **Evolution API (version Go)**.

Ce projet met en œuvre une architecture stricte en 4 couches (Router → Service → Repository → Cache) avec un rendu de cartes-images dynamique (Playwright) envoyé en arrière-plan (Celery) aux groupes WhatsApp associés.

---

## 🚀 Fonctionnalités Clés

1. **Messagerie Anonyme intégrée à WhatsApp** : Les utilisateurs externes peuvent envoyer des messages anonymes à des fils de discussion ("Threads") spécifiques associés à des groupes WhatsApp.
2. **Rendu Visuel Premium** : Les messages envoyés génèrent une carte visuelle stylisée sous forme d'image PNG via Playwright à partir d'un template HTML/CSS ([v1_template.html](./app/integrations/whatsapp/templates/v1_template.html)) avant d'être transmis sur WhatsApp.
3. **Commandes WhatsApp interactives** : Administration des fils de discussion directement depuis WhatsApp par les administrateurs de groupes (ex: `/map_group`, `/lock`, `/unlock`, `/sync-thread`).
4. **Architecture Logicielle Stricte** :
   - **Router** : Couche HTTP de présentation.
   - **Service** : Logique métier asynchrone (Cache-First).
   - **Repository** : Requêtes SQL optimisées avec SQLAlchemy 2 (asynchrone).
   - **Cache** : Gestion robuste des clés et invalidation via Redis.
5. **Gestion de Files d'Attente (Celery)** : Exécution asynchrone des tâches lourdes (rendu d'image Playwright et envois réseau WhatsApp).
6. **Sécurité et Sessions** : Authentification par double cookie JWT (`_SECURE_TOKEN` et `_SID_REFRESH`).
7. **Pagination par Curseur** : Pagination optimisée (Cursor-based) pour la lecture performante des messages.

---

## 🛠️ Stack Technique

* **Langage** : Python 3.12 (Local) / 3.11 (Docker)
* **Framework Web** : FastAPI & Uvicorn (avec uvloop pour des performances maximales sous Unix)
* **Base de données** : PostgreSQL (pilote asynchrone `asyncpg`) & SQLAlchemy 2 (asynchrone) + Alembic
* **Gestion du cache & Broker** : Redis
* **Tâches en arrière-plan** : Celery
* **Intégration WhatsApp** : Evolution API (Go version)
* **Moteur de rendu d'images** : Playwright (Chromium headless) & Jinja2
* **Hashing** : Argon2-cffi

---

## 🎨 Écosystème du Projet

Ce repository contient **le backend uniquement**. L'écosystème complet du projet NGL Clone se compose de plusieurs repositories :

### 🔗 Repositories Connexes

| Repository                                                                           | Description | Stack                                            |
|:-------------------------------------------------------------------------------------| :--- |:-------------------------------------------------|
| **ngl-clone-backend** (ce repo)                                                      | API backend, logique métier, intégration WhatsApp | FastAPI, PostgreSQL, Redis, Celery               |
| **[ngl-clone-frontend](https://github.com/IAI-OpenSource/ngl-clone-frontend/)**      | Client web, compositeur de messages anonymes et interface utilisateur | React 19, Tailwind CSS v4, Zustand...            |
| **[ngl-clone-docs](#)**                                                              | [À COMPLÉTER : Documentation partagée, spécifications API, guides d'installation] | Markdown, [À COMPLÉTER : outil de documentation] |

### 🚀 Démarrer l'ensemble du projet

Pour mettre en place l'écosystème complet :

1. **Clone le repository backend** (celui-ci) et configurez-le selon la section [Démarrage et Installation](#-démarrage-et-installation)
2. **Clone le repository frontend** : [À COMPLÉTER : lien vers le repo frontend]
3. **Configurez les variables d'environnement** dans chaque repository ([.env.example](./.env.example) pour le backend)
4. **Lancez les services** selon les instructions de chaque repository

> [!NOTE]
> Consultez la documentation partagée du projet : [À COMPLÉTER : lien vers le repo docs] pour les guides d'intégration complets et les architectures.

---

## 📁 Structure du Projet

```
app/
├── main.py                   # Point d'entrée de l'API FastAPI principale
├── webhook_app.py            # Point d'entrée pour la réception asynchrone des Webhooks WhatsApp
├── core/
│   ├── config.py             # Chargement & validation des variables d'environnement
│   └── logging_config.py     # Configuration des logs rotatifs
├── db/
│   ├── session.py            # Session de base de données asynchrone
│   ├── models/               # Modèles SQLAlchemy (User, Message, Thread, Member, etc.)
│   └── mixins/               # Mixins SQLAlchemy (gestion automatique des messages d'erreur)
├── repositories/             # Requêtes SQL pures (retournent CrudResult)
├── services/                 # Logique métier & cache-first (retournent ServiceResult)
├── cache/                    # Gestion Redis par entité (Cachers)
├── routers/                  # Points d'entrée de l'API HTTP (Routers V1)
├── auth/                     # Authentification, Cookies, Rôles
├── integrations/
│   └── whatsapp/             # Wrapper Evolution API, Générateur de cartes (Playwright), Webhooks, Commandes
└── worker/
    ├── celery_app.py          # Configuration Celery
    └── tasks/                 # Tâches Celery (envoi de message, synchronisation de membres)
```

---

## ⚙️ Configuration (.env)

Créez un fichier `.env` en vous basant sur le fichier [.env.example](./.env.example). Voici les variables principales à renseigner :

| Variable | Description | Exemple / Défaut |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Environnement de l'application | `LOCAL` / `PRODUCTION` |
| `SECRET_KEY` | Clé secrète pour la signature des tokens JWT | *Une clé cryptographique forte* |
| `API_PORT` | Port d'écoute de l'API backend | `8000` |
| `DATABASE_USER` | Utilisateur PostgreSQL | `admin` |
| `DATABASE_PASSWORD` | Mot de passe PostgreSQL | `password` |
| `DATABASE_NAME` | Nom de la base de données | `app_db` |
| `BD_OUTPUT_PORT` | Port exposé pour PostgreSQL sur la machine hôte | `5433` |
| `REDIS_URL` | URL de connexion à Redis | `redis://redis:6379/0` |
| `EVO_URL` | URL du serveur de l'Evolution API | `http://evolution-api:8080` |
| `GLOBAL_API_KEY` | Clé d'API globale d'Evolution API | *Clé secrète d'Evolution API* |
| `ACTIVE_INSTANCE_API_KEY` | Clé d'API de l'instance WhatsApp active | *Clé d'instance* |

---

## 🚀 Démarrage et Installation

### Option 1 : Via Docker (Recommandé)

Le projet intègre un orchestrateur multi-conteneurs complet :

1. Assurez-vous d'avoir configuré le fichier `.env`.
2. Lancez tous les services en arrière-plan :
   ```bash
   make start_docker
   ```
3. Exécutez les migrations de base de données :
   ```bash
   make migrate-up
   ```

Pour arrêter les services :
```bash
make stop_docker
```

### Option 2 : Installation Locale (Développement)

1. Créez un environnement virtuel Python et installez les dépendances :
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Installez les navigateurs nécessaires pour Playwright :
   ```bash
   playwright install chromium
   ```
3. Assurez-vous que PostgreSQL et Redis sont lancés localement ou accessibles.
4. Lancez le serveur FastAPI principal :
   ```bash
   python app/main.py
   ```
5. Dans un autre terminal, lancez le récepteur de webhooks WhatsApp :
   ```bash
   uvicorn app.webhook_app:app --host 0.0.0.0 --port 8001
   ```
6. Démarrez le worker Celery :
   ```bash
   celery -A app.worker.celery_app worker --loglevel=info
   ```

---

## 🤖 Commandes du Bot WhatsApp

Lorsqu'un bot WhatsApp configuré rejoint un groupe, il répond aux commandes suivantes envoyées par les membres ou les administrateurs du groupe :

> [!IMPORTANT]
> Les commandes avec restriction `Admin uniquement` requièrent que l'expéditeur soit administrateur du groupe WhatsApp ou membre ayant un rôle Admin défini dans le système.

| Commande | Admin ? | Description |
| :--- | :--- | :--- |
| `/map_group` | **Oui** | Associe le groupe WhatsApp à un thread NGL (crée ou lie le thread). |
| `/lock` | **Oui** | Verrouille le fil. Empêche l'envoi de nouveaux messages anonymes. |
| `/unlock` | **Oui** | Déverrouille le fil de discussion pour autoriser à nouveau les messages anonymes. |
| `/edit-name <nom>` | **Oui** | Modifie le nom affiché du fil de discussion. |
| `/edit-desc <description>` | **Oui** | Modifie la description du fil. |
| `/edit-slug <nouveau-slug>`| **Oui** | Met à jour le slug personnalisé du thread (URL d'accès). |
| `/sync-thread` | Non | Synchronise la liste des membres actifs du groupe WhatsApp avec la base de données. |
| `/ngl` | Non | Affiche le statut actuel du fil de discussion lié au groupe. |
| `/help` | Non | Affiche la liste des commandes disponibles. |
| `/docs` | Non | Affiche un résumé rapide ou des instructions de configuration. |

---

## 📐 Règles d'Architecture du Projet

Le projet adhère à une charte de développement stricte documentée dans [AGENTS.md](./AGENTS.md). 

> [!WARNING]
> **Interdiction absolue** de :
> 1. Retourner des dictionnaires bruts depuis les services. Utilisez `ServiceResult.service_success()` ou `ServiceResult.service_failure()`.
> 2. Construire `ApiBaseResponse` directement dans les contrôleurs/routers. Appelez `.to_HTTP_api_base_response(reponse=response)`.
> 3. Utiliser `db.commit()` ou `db.rollback()` dans la couche Service. Les transactions sont gérées au niveau Repository/Session.
> 4. Ignorer le filtrage des suppressions logiques : chaque requête de lecture `select()` doit inclure `.where(Entity.deleted_at == None)`.

Les commentaires et les messages d'erreur utilisateur sont rédigés en **Français** afin de maintenir la cohérence de la codebase.

---

## 📚 En savoir plus (Documentation Complète)

Consultez les guides détaillés situés dans le dossier `/docs` :
* 🧱 [Aperçu de l'Architecture & Flux](./docs/architecture_overview_fr.md)
* 💾 [Gestion de la Base de Données & Modèles](./docs/database_and_models_fr.md)
* ⚡ [Système de Cache Redis & Clés](./docs/caching_system_fr.md)
* 🔄 [Repositories, Services et Propagation de Résultats](./docs/repositories_and_services_fr.md)
* ❌ [Gestion des Erreurs Logiciels](./docs/results_and_errors_fr.md)
* 🛡️ [Sécurité, JWT et Dual-Cookie](./docs/auth_and_security_fr.md)

---

## 🤝 Contribution

Les contributions sont bienvenues et vivement encouragées ! Ce projet bénéficie de votre expertise et de vos idées pour s'améliorer.

### Comment contribuer ?

1. **Fork le repository** sur GitHub
2. **Créez une branche** pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalité`)
3. **Validez vos changements** en suivant la charte de développement définie dans [AGENTS.md](./AGENTS.md) :
   - Respectez la structure en 4 couches (Router → Service → Repository → Cache)
   - Utilisez `ServiceResult` et `CrudResult` pour les retours
   - Filtrez les suppressions logiques avec `.where(Entity.deleted_at == None)`
   - Rédigez les commentaires et messages d'erreur en **Français**
4. **Testez** vos modifications (le projet n'a pas de suite de tests automatisée, testez manuellement)
5. **Committez** avec un message explicite en Français : `git commit -m "Description claire de votre changement"`
6. **Poussez** vers votre fork : `git push origin feature/ma-fonctionnalité`
7. **Ouvrez une Pull Request** sur le repository principal avec une description détaillée

### Directives de contribution

- **Documentation** : Si vous ajoutez une nouvelle fonctionnalité, mettez à jour la documentation pertinente dans `/docs`
- **Convention de code** : Consultez [AGENTS.md](./AGENTS.md) pour les conventions de nommage, d'imports et de structure
- **Environnement** : En cas de doute, testez vos changements dans Docker pour garantir la compatibilité
- **Questions ?** : Créez une [Issue](../../issues) pour en discuter avant de vous lancer

### Signaler un bug

Si vous découvrez un bug, veuillez créer une [Issue](../../issues) en incluant :
- Une description claire du problème
- Les étapes pour le reproduire
- Le comportement attendu vs. celui observé
- Votre configuration d'environnement (OS, Python version, etc.)

---

## 📜 Licence

Ce projet est licencié sous la Licence MIT. Consultez le fichier [LICENSE](./LICENSE) pour plus de détails.

---

## 📧 Contact et Support

Pour toute question ou support :
- Créez une [Issue](../../issues) sur GitHub
- Consultez la [documentation complète](./docs/architecture_overview_fr.md)
- Référez-vous aux [guidelines de développement](./AGENTS.md)

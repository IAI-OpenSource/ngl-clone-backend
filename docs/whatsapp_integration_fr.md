# Intégration WhatsApp - Evolution API (Go)

Ce document décrit l'intégration de l'API Evolution Go pour la messagerie WhatsApp dans le projet.

---

> **📄 Documentation Available in English**
> An English version of this document is available: [whatsapp_integration_en.md](./whatsapp_integration_en.md)

---

## 1. Aperçu

L'intégration WhatsApp utilise **Evolution API (version Go)** comme backend pour envoyer et recevoir des messages WhatsApp. Le client est implémenté dans `app/integrations/evolution_client.py` et offre une API asynchrone et typée pour interagir avec l'API Evolution.

### 1.1 Caractéristiques principales

- **Client Singleton** : Gestion centralisée de l'instance Evolution Go
- **Typage strict** : Utilisation de Pydantic pour les DTOs et réponses
- **Support complet** : Messages texte, médias, groupes, webhooks
- **Gestion des erreurs** : Exceptions spécifiques pour chaque cas d'erreur
- **Anti-ban** : Délai configurable entre les envois de messages

### 1.2 Différences avec la version Node.js

- Pas de nom d'instance dans les paths (single-instance par processus)
- Routes simplifiées : `/send/text`, `/send/media`, `/instance/status`, `/group/join`
- Format de réponse : `{ "data": {...}, "message": "success" }`
- Authentification : Header `apikey` (identique à Node.js)

---

## 2. Configuration

### 2.1 Variables d'environnement

Les variables suivantes doivent être configurées dans votre fichier `.env` :

```env
# Configuration Evolution Go
EVOLUTION_API_BASE_URL=http://localhost:8080
EVOLUTION_API_KEY=your-api-key-here
EVOLUTION_SEND_DELAY=1.5
EVOLUTION_TIMEOUT=30.0
```

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `EVOLUTION_API_BASE_URL` | URL du serveur Evolution Go | `http://localhost:8080` |
| `EVOLUTION_API_KEY` | Clé API pour l'authentification | *Requise* |
| `EVOLUTION_SEND_DELAY` | Délai (en secondes) entre les envois | `1.5` |
| `EVOLUTION_TIMEOUT` | Timeout HTTP (en secondes) | `30.0` |

### 2.2 Dépendances Python

Le client nécessite les packages suivants (à ajouter à `requirements.txt`) :

```
httpx>=0.27
pydantic>=2
```

---

## 3. Architecture du Client

### 3.1 Structure du package

```
app/integrations/
├── __init__.py          # Classes de base pour les services d'intégration
└── evolution_client.py  # Client Evolution Go
```

### 3.2 Classes principales

#### 3.2.1 `EvolutionAPIClient`

Client principal implémentant le pattern Singleton pour une gestion centralisée.

**Fonctionnalités** :
- Gestion du cycle de vie (initialisation, fermeture)
- Requêtes HTTP asynchrones vers Evolution Go
- Parsing des réponses et gestion des erreurs
- Méthodes utilitaires pour les JIDs WhatsApp

#### 3.2.2 Modèles de données (DTOs)

Tous les modèles héritent de `pydantic.BaseModel` pour une validation et une sérialisation typées :

- `WAInstanceStatus` : Statut de connexion de l'instance
- `WAMessageInfo` : Informations sur un message envoyé
- `WASentMessage` : Réponse complète après envoi
- `WAParticipant` : Participant d'un groupe
- `WAGroupInfo` : Métadonnées d'un groupe
- `WAWebhookConfig` : Configuration du webhook
- `WAGroupParticipantUpdate` : Payload des mises à jour de groupe

#### 3.2.3 Enums

- `WAMediaType` : Types de médias supportés (IMAGE, VIDEO, AUDIO, DOCUMENT, STICKER)
- `WAParticipantRole` : Rôles dans un groupe (MEMBER, ADMIN, SUPERADMIN)
- `WAWebhookEvent` : Événements webhook disponibles

#### 3.2.4 Exceptions

Hiérarchie d'exceptions pour une gestion fine des erreurs :

- `EvolutionError` : Exception de base
- `EvolutionAuthError` : Erreur d'authentification (401/403)
- `EvolutionNotFoundError` : Ressource introuvable (404)
- `EvolutionConnectionError` : Problème de connexion
- `EvolutionInstanceError` : Instance dans un état invalide
- `EvolutionRateLimitError` : Rate limit atteint (429)
- `EvolutionNotInitializedError` : Singleton non initialisé

---

## 4. Utilisation

### 4.1 Initialisation (FastAPI Lifespan)

L'initialisation doit être effectuée au démarrage de l'application, idéalement dans le lifespan de FastAPI :

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.integrations.evolution_client import EvolutionAPIClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialisation du client
    async with EvolutionAPIClient.initialize(
        base_url="http://localhost:8080",
        api_key="votre-cle-api",
        timeout=30.0,
        send_delay=1.5,
    ) as client:
        # Vérification que l'instance est prête
        if not await client.is_ready():
            raise RuntimeError("Instance WhatsApp non connectée")
        yield
    
    # Fermeture propre (appelée automatiquement)
    await EvolutionAPIClient.teardown()

app = FastAPI(lifespan=lifespan)
```

### 4.2 Accès au client

Une fois initialisé, le client peut être utilisé de plusieurs manières :

#### Méthode 1 : Singleton direct

```python
from app.integrations.evolution_client import EvolutionAPIClient

# N'importe où dans votre code
client = EvolutionAPIClient.get_instance()
await client.send_text("120363xxx@g.us", "Bonjour !")
```

#### Méthode 2 : Injection FastAPI

```python
from fastapi import Depends
from typing import Annotated
from app.integrations.evolution_client import EvolutionAPIClient

WAClient = Annotated[EvolutionAPIClient, Depends(EvolutionAPIClient.as_dependency)]

@app.post("/messages")
async def send_message(client: WAClient, text: str):
    return await client.send_text("120363xxx@g.us", text)
```

#### Méthode 3 : Context manager (scripts, tests)

```python
import asyncio
from app.integrations.evolution_client import EvolutionAPIClient

async def main():
    async with EvolutionAPIClient(
        base_url="http://localhost:8080",
        api_key="votre-cle-api"
    ) as client:
        participants = await client.get_group_participants("120363xxx@g.us")
        print(f"Nombre de participants : {len(participants)}")

asyncio.run(main())
```

---

## 5. Fonctionnalités API

### 5.1 Gestion de l'instance

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `get_status()` | Récupère le statut de connexion | `GET /instance/status` |
| `is_ready()` | Vérifie si l'instance est connectée et loggée | - |
| `connect()` | Démarre la connexion (retourne QR code) | `GET /instance/connect` |
| `logout()` | Déconnecte l'instance | `POST /instance/logout` |
| `get_qr_code()` | Récupère le QR code pour re-scan | `GET /instance/qrcode` |

**Exemple** :
```python
status = await client.get_status()
print(f"Connecté : {status.connected}, Loggé : {status.logged_in}")

if await client.is_ready():
    await client.send_text("1234567890@s.whatsapp.net", "Hello!")
```

### 5.2 Gestion des groupes

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `get_group_info(jid)` | Récupère les infos d'un groupe | `GET /group/info` |
| `get_group_participants(jid)` | Liste les participants | `GET /group/participants` |
| `get_group_with_participants(jid)` | Infos + participants en parallèle | - |
| `list_groups()` | Liste tous les groupes | `GET /group/list` |
| `join_group(code)` | Rejoint un groupe via code | `POST /group/join` |
| `get_group_invite_link(jid, reset)` | Génère un lien d'invitation | `POST /group/invitelink` |

**Exemple** :
```python
# Récupérer les informations d'un groupe
group = await client.get_group_with_participants("120363xxx@g.us")
print(f"Groupe : {group.subject} ({len(group.participants)} membres)")

# Rejoindre un groupe
invite_code = EvolutionAPIClient.extract_invite_code("https://chat.whatsapp.com/AbCdEfGhIjKl")
await client.join_group(invite_code)

# Générer un lien d'invitation
group_jid = "120363xxx@g.us"
invite_link = await client.get_group_invite_link(group_jid, reset=True)
```

### 5.3 Messages texte

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `send_text(number, text, ...)` | Envoie un message texte | `POST /send/text` |
| `send_text_with_mentions(...)` | Envoie avec mentions | `POST /send/text` |
| `batch_send_text(targets, ...)` | Envoie en batch | - |

**Exemple** :
```python
# Message simple
await client.send_text("1234567890@s.whatsapp.net", "Bonjour !")

# Message avec mention
await client.send_text(
    "120363xxx@g.us",
    "Salut @tous !",
    mention_all=True
)

# Message avec mentions spécifiques
await client.send_text(
    "120363xxx@g.us",
    "Bonjour !",
    mention_jids=["1234567890@s.whatsapp.net", "9876543210@s.whatsapp.net"]
)

# Envoi en batch
results = await client.batch_send_text([
    ("1234567890@s.whatsapp.net", "Message 1"),
    ("9876543210@s.whatsapp.net", "Message 2"),
])
```

### 5.4 Messages médias

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `send_media(number, url, type, ...)` | Envoie un média | `POST /send/media` |
| `send_image(number, url, ...)` | Envoie une image | `POST /send/media` |
| `send_video(number, url, ...)` | Envoie une vidéo | `POST /send/media` |
| `send_audio(number, url, ...)` | Envoie un audio | `POST /send/media` |
| `send_document(number, url, filename, ...)` | Envoie un document | `POST /send/media` |

**Exemple** :
```python
# Envoyer une image
await client.send_image(
    "120363xxx@g.us",
    "https://example.com/image.jpg",
    caption="Voici une image"
)

# Envoyer un document
await client.send_document(
    "120363xxx@g.us",
    "https://example.com/document.pdf",
    filename="rapport.pdf",
    caption="Rapport annuel"
)

# Envoyer via base64
await client.send_media(
    "1234567890@s.whatsapp.net",
    base64_image_data,
    WAMediaType.IMAGE,
    caption="Image en base64"
)
```

### 5.5 Réactions

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `send_reaction(number, message_id, reaction, ...)` | Ajoute une réaction | `POST /send/reaction` |

**Exemple** :
```python
# Ajouter une réaction
sent = await client.send_text("120363xxx@g.us", "Super !")
await client.send_reaction("120363xxx@g.us", sent.message_id, "❤️")

# Retirer une réaction
await client.send_reaction("120363xxx@g.us", sent.message_id, "")
```

### 5.6 Webhooks

| Méthode | Description | Endpoint |
|---------|-------------|----------|
| `configure_webhook(url, events, enabled)` | Configure le webhook | `POST /webhook/set` |
| `get_webhook_config()` | Récupère la config active | `GET /webhook/find` |

**Exemple** :
```python
# Configurer le webhook
from app.integrations.evolution_client import WAWebhookEvent

await client.configure_webhook(
    url="https://votre-domaine.com/webhooks/wa",
    events=[
        WAWebhookEvent.MESSAGE,
        WAWebhookEvent.CONNECTION,
        WAWebhookEvent.GROUP,
    ],
    enabled=True
)

# Récupérer la configuration
config = await client.get_webhook_config()
```

### 5.7 Méthodes utilitaires

| Méthode | Description |
|---------|-------------|
| `jid_to_phone(jid)` | Extrait le numéro d'un JID |
| `phone_to_jid(phone)` | Convertit un numéro en JID |
| `is_group_jid(jid)` | Vérifie si c'est un groupe |
| `extract_invite_code(url)` | Extrait le code d'invitation |
| `parse_participant_update(payload)` | Parse un payload webhook |

**Exemple** :
```python
# Conversion de JID
jid = "1234567890@s.whatsapp.net"
phone = EvolutionAPIClient.jid_to_phone(jid)  # "1234567890"
new_jid = EvolutionAPIClient.phone_to_jid("+1234567890")  # "1234567890@s.whatsapp.net"

# Vérification de groupe
is_group = EvolutionAPIClient.is_group_jid("120363xxx@g.us")  # True

# Extraction de code
code = EvolutionAPIClient.extract_invite_code("https://chat.whatsapp.com/AbCdEfGhIjKl")
```

---

## 6. Gestion des erreurs

### 6.1 Exceptions

Toutes les exceptions héritent de `EvolutionError` et peuvent être capturées spécifiquement :

```python
from app.integrations.evolution_client import (
    EvolutionError,
    EvolutionAuthError,
    EvolutionNotFoundError,
    EvolutionConnectionError,
    EvolutionRateLimitError,
)

try:
    await client.send_text("1234567890@s.whatsapp.net", "Hello")
except EvolutionAuthError as e:
    print(f"Erreur d'authentification : {e}")
except EvolutionNotFoundError as e:
    print(f"Ressource introuvable : {e}")
except EvolutionConnectionError as e:
    print(f"Problème de connexion : {e}")
except EvolutionRateLimitError as e:
    print(f"Rate limit atteint : {e}")
except EvolutionError as e:
    print(f"Erreur générale : {e} (code: {e.status_code})")
```

### 6.2 Props des exceptions

Toutes les exceptions ont les propriétés suivantes :

- `message` : Message d'erreur
- `status_code` : Code HTTP (si applicable)
- `payload` : Données brutes de la réponse (si applicable)

---

## 7. Bonnes pratiques

### 7.1 Initialisation

- **Toujours** initialiser le client dans le lifespan de FastAPI
- **Toujours** vérifier `is_ready()` avant d'envoyer des messages
- **Toujours** appeler `teardown()` à la fermeture de l'application

### 7.2 Envoi de messages

- Utiliser le paramètre `delay` pour respecter les limites de l'API
- Éviter les boucles d'envoi sans délai entre les messages
- Utiliser `batch_send_text()` pour les envois multiples

### 7.3 Gestion des groupes

- Utiliser `get_group_with_participants()` pour récupérer infos + membres en une seule appelée
- Mettre à jour régulièrement la liste des participants via les webhooks
- Utiliser `parse_participant_update()` pour traiter les webhooks de groupe

### 7.4 Webhooks

- Configurer le webhook avec tous les événements nécessaires
- Sécuriser l'endpoint de webhook avec une vérification de signature
- Utiliser les DTOs fournis pour parser les payloads

---

## 8. Exemples complets

### 8.1 Service d'envoi de messages

```python
from app.integrations.evolution_client import EvolutionAPIClient, EvolutionError

class MessageService:
    def __init__(self):
        self._client = EvolutionAPIClient.get_instance()
    
    async def send_welcome_message(self, phone: str) -> bool:
        try:
            jid = EvolutionAPIClient.phone_to_jid(phone)
            await self._client.send_text(
                jid,
                "Bienvenue ! Merci de vous être inscrit."
            )
            return True
        except EvolutionError as e:
            print(f"Échec envoi message : {e}")
            return False
```

### 8.2 Synchronisation des membres de groupe

```python
from app.integrations.evolution_client import EvolutionAPIClient
from app.repositories.member_repository import MemberRepository

class GroupSyncService:
    def __init__(self, db_session):
        self._client = EvolutionAPIClient.get_instance()
        self._member_repo = MemberRepository(db_session)
    
    async def sync_group_members(self, group_jid: str) -> list[str]:
        """Synchronise les membres d'un groupe avec la base de données."""
        participants = await self._client.get_group_participants(group_jid)
        
        synced_jids = []
        for participant in participants:
            phone = participant.phone_number
            await self._member_repo.upsert_member(phone, participant.name)
            synced_jids.append(participant.jid)
        
        return synced_jids
```

### 8.3 Handler de webhook

```python
from fastapi import APIRouter, Request
from app.integrations.evolution_client import EvolutionAPIClient, WAWebhookEvent

router = APIRouter(prefix="/webhooks")

@router.post("/wa")
async def handle_wa_webhook(request: Request):
    body = await request.json()
    event = body.get("event")
    data = body.get("data", {})
    
    if event == WAWebhookEvent.MESSAGE.value:
        # Traiter un nouveau message
        pass
    elif event == WAWebhookEvent.GROUP.value:
        # Traiter une mise à jour de groupe
        update = EvolutionAPIClient.parse_participant_update(data)
        if update.is_add:
            print(f"Nouveau membre dans {update.id} : {update.participants}")
        elif update.is_remove:
            print(f"Membre quitté {update.id} : {update.participants}")
    
    return {"status": "ok"}
```

---

## 9. Références

- **Documentation officielle Evolution Go** : [https://docs.evolutionfoundation.com.br/evolution-go](https://docs.evolutionfoundation.com.br/evolution-go)
- **Code source du client** : [app/integrations/evolution_client.py](../app/integrations/evolution_client.py)
- **Package Pydantic** : [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **Package httpx** : [https://www.python-httpx.org/](https://www.python-httpx.org/)

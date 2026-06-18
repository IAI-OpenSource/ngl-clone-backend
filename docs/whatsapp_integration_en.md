# WhatsApp Integration - Evolution API (Go)

This document describes the integration of Evolution Go API for WhatsApp messaging in the project.

---

> **📄 Documentation Disponible en Français**
> A French version of this document is available: [whatsapp_integration_fr.md](./whatsapp_integration_fr.md)

---

## 1. Overview

The WhatsApp integration uses **Evolution API (Go version)** as the backend for sending and receiving WhatsApp messages. The client is implemented in `app/integrations/evolution_client.py` and provides an async, fully-typed API to interact with Evolution API.

### 1.1 Key Features

- **Singleton Client**: Centralized management of Evolution Go instance
- **Strong Typing**: Uses Pydantic for DTOs and responses
- **Full Support**: Text messages, media, groups, webhooks
- **Error Management**: Specific exceptions for each error case
- **Anti-ban**: Configurable delay between message sends

### 1.2 Differences from Node.js version

- No instance name in paths (single-instance per process)
- Simplified routes: `/send/text`, `/send/media`, `/instance/status`, `/group/join`
- Response format: `{ "data": {...}, "message": "success" }`
- Authentication: `apikey` header (same as Node.js)

---

## 2. Configuration

### 2.1 Environment Variables

The following variables should be configured in your `.env` file:

```env
# Evolution Go Configuration
EVOLUTION_API_BASE_URL=http://localhost:8080
EVOLUTION_API_KEY=your-api-key-here
EVOLUTION_SEND_DELAY=1.5
EVOLUTION_TIMEOUT=30.0
```

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `EVOLUTION_API_BASE_URL` | Evolution Go server URL | `http://localhost:8080` |
| `EVOLUTION_API_KEY` | API key for authentication | *Required* |
| `EVOLUTION_SEND_DELAY` | Delay (seconds) between sends | `1.5` |
| `EVOLUTION_TIMEOUT` | HTTP timeout (seconds) | `30.0` |

### 2.2 Python Dependencies

The client requires the following packages (add to `requirements.txt`):

```
httpx>=0.27
pydantic>=2
```

---

## 3. Client Architecture

### 3.1 Package Structure

```
app/integrations/
├── __init__.py          # Base classes for integration services
└── evolution_client.py  # Evolution Go client
```

### 3.2 Main Classes

#### 3.2.1 `EvolutionAPIClient`

Main client implementing the Singleton pattern for centralized management.

**Features**:
- Lifecycle management (initialization, shutdown)
- Async HTTP requests to Evolution Go
- Response parsing and error handling
- Utility methods for WhatsApp JIDs

#### 3.2.2 Data Models (DTOs)

All models inherit from `pydantic.BaseModel` for typed validation and serialization:

- `WAInstanceStatus`: Instance connection status
- `WAMessageInfo`: Information about a sent message
- `WASentMessage`: Complete response after sending
- `WAParticipant`: Group participant
- `WAGroupInfo`: Group metadata
- `WAWebhookConfig`: Webhook configuration
- `WAGroupParticipantUpdate`: Group update payload

#### 3.2.3 Enums

- `WAMediaType`: Supported media types (IMAGE, VIDEO, AUDIO, DOCUMENT, STICKER)
- `WAParticipantRole`: Group roles (MEMBER, ADMIN, SUPERADMIN)
- `WAWebhookEvent`: Available webhook events

#### 3.2.4 Exceptions

Exception hierarchy for fine-grained error handling:

- `EvolutionError`: Base exception
- `EvolutionAuthError`: Authentication error (401/403)
- `EvolutionNotFoundError`: Resource not found (404)
- `EvolutionConnectionError`: Connection problem
- `EvolutionInstanceError`: Invalid instance state
- `EvolutionRateLimitError`: Rate limit reached (429)
- `EvolutionNotInitializedError`: Singleton not initialized

---

## 4. Usage

### 4.1 Initialization (FastAPI Lifespan)

Initialization should be done at application startup, ideally in FastAPI lifespan:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.integrations.evolution_client import EvolutionAPIClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize client
    async with EvolutionAPIClient.initialize(
        base_url="http://localhost:8080",
        api_key="your-api-key",
        timeout=30.0,
        send_delay=1.5,
    ) as client:
        # Verify instance is ready
        if not await client.is_ready():
            raise RuntimeError("WhatsApp instance not connected")
        yield
    
    # Clean shutdown (called automatically)
    await EvolutionAPIClient.teardown()

app = FastAPI(lifespan=lifespan)
```

### 4.2 Accessing the Client

Once initialized, the client can be used in several ways:

#### Method 1: Singleton Direct

```python
from app.integrations.evolution_client import EvolutionAPIClient

# Anywhere in your code
client = EvolutionAPIClient.get_instance()
await client.send_text("120363xxx@g.us", "Hello!")
```

#### Method 2: FastAPI Dependency Injection

```python
from fastapi import Depends
from typing import Annotated
from app.integrations.evolution_client import EvolutionAPIClient

WAClient = Annotated[EvolutionAPIClient, Depends(EvolutionAPIClient.as_dependency)]

@app.post("/messages")
async def send_message(client: WAClient, text: str):
    return await client.send_text("120363xxx@g.us", text)
```

#### Method 3: Context Manager (scripts, tests)

```python
import asyncio
from app.integrations.evolution_client import EvolutionAPIClient

async def main():
    async with EvolutionAPIClient(
        base_url="http://localhost:8080",
        api_key="your-api-key"
    ) as client:
        participants = await client.get_group_participants("120363xxx@g.us")
        print(f"Number of participants: {len(participants)}")

asyncio.run(main())
```

---

## 5. API Features

### 5.1 Instance Management

| Method | Description | Endpoint |
|--------|-------------|----------|
| `get_status()` | Get connection status | `GET /instance/status` |
| `is_ready()` | Check if instance is connected and logged in | - |
| `connect()` | Start connection (returns QR code) | `GET /instance/connect` |
| `logout()` | Disconnect instance | `POST /instance/logout` |
| `get_qr_code()` | Get QR code for re-scan | `GET /instance/qrcode` |

**Example**:
```python
status = await client.get_status()
print(f"Connected: {status.connected}, Logged in: {status.logged_in}")

if await client.is_ready():
    await client.send_text("1234567890@s.whatsapp.net", "Hello!")
```

### 5.2 Group Management

| Method | Description | Endpoint |
|--------|-------------|----------|
| `get_group_info(jid)` | Get group info | `GET /group/info` |
| `get_group_participants(jid)` | List participants | `GET /group/participants` |
| `get_group_with_participants(jid)` | Info + participants in parallel | - |
| `list_groups()` | List all groups | `GET /group/list` |
| `join_group(code)` | Join group via invite code | `POST /group/join` |
| `get_group_invite_link(jid, reset)` | Generate invite link | `POST /group/invitelink` |

**Example**:
```python
# Get group information
group = await client.get_group_with_participants("120363xxx@g.us")
print(f"Group: {group.subject} ({len(group.participants)} members)")

# Join a group
invite_code = EvolutionAPIClient.extract_invite_code("https://chat.whatsapp.com/AbCdEfGhIjKl")
await client.join_group(invite_code)

# Generate invite link
group_jid = "120363xxx@g.us"
invite_link = await client.get_group_invite_link(group_jid, reset=True)
```

### 5.3 Text Messages

| Method | Description | Endpoint |
|--------|-------------|----------|
| `send_text(number, text, ...)` | Send text message | `POST /send/text` |
| `send_text_with_mentions(...)` | Send with mentions | `POST /send/text` |
| `batch_send_text(targets, ...)` | Batch send | - |

**Example**:
```python
# Simple message
await client.send_text("1234567890@s.whatsapp.net", "Hello!")

# Message with mention all
await client.send_text(
    "120363xxx@g.us",
    "Hi everyone!",
    mention_all=True
)

# Message with specific mentions
await client.send_text(
    "120363xxx@g.us",
    "Hello!",
    mention_jids=["1234567890@s.whatsapp.net", "9876543210@s.whatsapp.net"]
)

# Batch send
results = await client.batch_send_text([
    ("1234567890@s.whatsapp.net", "Message 1"),
    ("9876543210@s.whatsapp.net", "Message 2"),
])
```

### 5.4 Media Messages

| Method | Description | Endpoint |
|--------|-------------|----------|
| `send_media(number, url, type, ...)` | Send media | `POST /send/media` |
| `send_image(number, url, ...)` | Send image | `POST /send/media` |
| `send_video(number, url, ...)` | Send video | `POST /send/media` |
| `send_audio(number, url, ...)` | Send audio | `POST /send/media` |
| `send_document(number, url, filename, ...)` | Send document | `POST /send/media` |

**Example**:
```python
# Send image
await client.send_image(
    "120363xxx@g.us",
    "https://example.com/image.jpg",
    caption="Here's an image"
)

# Send document
await client.send_document(
    "120363xxx@g.us",
    "https://example.com/document.pdf",
    filename="report.pdf",
    caption="Annual report"
)

# Send via base64
await client.send_media(
    "1234567890@s.whatsapp.net",
    base64_image_data,
    WAMediaType.IMAGE,
    caption="Base64 image"
)
```

### 5.5 Reactions

| Method | Description | Endpoint |
|--------|-------------|----------|
| `send_reaction(number, message_id, reaction, ...)` | Add reaction | `POST /send/reaction` |

**Example**:
```python
# Add reaction
sent = await client.send_text("120363xxx@g.us", "Great!")
await client.send_reaction("120363xxx@g.us", sent.message_id, "❤️")

# Remove reaction
await client.send_reaction("120363xxx@g.us", sent.message_id, "")
```

### 5.6 Webhooks

| Method | Description | Endpoint |
|--------|-------------|----------|
| `configure_webhook(url, events, enabled)` | Configure webhook | `POST /webhook/set` |
| `get_webhook_config()` | Get active config | `GET /webhook/find` |

**Example**:
```python
# Configure webhook
from app.integrations.evolution_client import WAWebhookEvent

await client.configure_webhook(
    url="https://your-domain.com/webhooks/wa",
    events=[
        WAWebhookEvent.MESSAGE,
        WAWebhookEvent.CONNECTION,
        WAWebhookEvent.GROUP,
    ],
    enabled=True
)

# Get configuration
config = await client.get_webhook_config()
```

### 5.7 Utility Methods

| Method | Description |
|--------|-------------|
| `jid_to_phone(jid)` | Extract phone from JID |
| `phone_to_jid(phone)` | Convert phone to JID |
| `is_group_jid(jid)` | Check if it's a group |
| `extract_invite_code(url)` | Extract invite code |
| `parse_participant_update(payload)` | Parse webhook payload |

**Example**:
```python
# JID conversion
jid = "1234567890@s.whatsapp.net"
phone = EvolutionAPIClient.jid_to_phone(jid)  # "1234567890"
new_jid = EvolutionAPIClient.phone_to_jid("+1234567890")  # "1234567890@s.whatsapp.net"

# Group check
is_group = EvolutionAPIClient.is_group_jid("120363xxx@g.us")  # True

# Extract code
code = EvolutionAPIClient.extract_invite_code("https://chat.whatsapp.com/AbCdEfGhIjKl")
```

---

## 6. Error Handling

### 6.1 Exceptions

All exceptions inherit from `EvolutionError` and can be caught specifically:

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
    print(f"Authentication error: {e}")
except EvolutionNotFoundError as e:
    print(f"Not found error: {e}")
except EvolutionConnectionError as e:
    print(f"Connection error: {e}")
except EvolutionRateLimitError as e:
    print(f"Rate limit error: {e}")
except EvolutionError as e:
    print(f"General error: {e} (code: {e.status_code})")
```

### 6.2 Exception Properties

All exceptions have the following properties:

- `message`: Error message
- `status_code`: HTTP status code (if applicable)
- `payload`: Raw response data (if applicable)

---

## 7. Best Practices

### 7.1 Initialization

- **Always** initialize client in FastAPI lifespan
- **Always** check `is_ready()` before sending messages
- **Always** call `teardown()` on application shutdown

### 7.2 Sending Messages

- Use `delay` parameter to respect API limits
- Avoid sending loops without delay between messages
- Use `batch_send_text()` for multiple sends

### 7.3 Group Management

- Use `get_group_with_participants()` to get info + members in one call
- Regularly update participant list via webhooks
- Use `parse_participant_update()` to handle group webhooks

### 7.4 Webhooks

- Configure webhook with all necessary events
- Secure webhook endpoint with signature verification
- Use provided DTOs to parse payloads

---

## 8. Complete Examples

### 8.1 Message Service

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
                "Welcome! Thank you for signing up."
            )
            return True
        except EvolutionError as e:
            print(f"Failed to send message: {e}")
            return False
```

### 8.2 Group Member Sync

```python
from app.integrations.evolution_client import EvolutionAPIClient
from app.repositories.member_repository import MemberRepository

class GroupSyncService:
    def __init__(self, db_session):
        self._client = EvolutionAPIClient.get_instance()
        self._member_repo = MemberRepository(db_session)
    
    async def sync_group_members(self, group_jid: str) -> list[str]:
        """Sync group members with database."""
        participants = await self._client.get_group_participants(group_jid)
        
        synced_jids = []
        for participant in participants:
            phone = participant.phone_number
            await self._member_repo.upsert_member(phone, participant.name)
            synced_jids.append(participant.jid)
        
        return synced_jids
```

### 8.3 Webhook Handler

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
        # Handle new message
        pass
    elif event == WAWebhookEvent.GROUP.value:
        # Handle group update
        update = EvolutionAPIClient.parse_participant_update(data)
        if update.is_add:
            print(f"New member in {update.id}: {update.participants}")
        elif update.is_remove:
            print(f"Member left {update.id}: {update.participants}")
    
    return {"status": "ok"}
```

---

## 9. References

- **Official Evolution Go Documentation**: [https://docs.evolutionfoundation.com.br/evolution-go](https://docs.evolutionfoundation.com.br/evolution-go)
- **Client Source Code**: [app/integrations/evolution_client.py](../app/integrations/evolution_client.py)
- **Pydantic Package**: [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **httpx Package**: [https://www.python-httpx.org/](https://www.python-httpx.org/)

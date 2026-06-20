"""
evolution_client.py
Wrapper async + fully typed pour Evolution Go (version Go de l'Evolution API).

Différences majeures vs la version Node.js :
  - Pas de nom d'instance dans les paths (single-instance par process)
  - Routes : /send/text, /send/media, /instance/status, /group/join...
  - Réponse : { "data": {...}, "message": "success" }
  - Auth : header `apikey` (identique)

Dépendances : httpx>=0.27, pydantic>=2
Doc officielle : https://docs.evolutionfoundation.com.br/evolution-go
"""
from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, ClassVar, Self

import httpx
from pydantic import BaseModel, Field

from app.core.config import (
    EVO_GLOBAL_API_URL,
    EVO_ACTIVE_INSTANCE_API_KEY,
)

logger = logging.getLogger(__name__)


# Exceptions
# ══════════════════════════════════════════════════════════════════════════════


class EvolutionError(Exception):
    """Exception de base pour toutes les erreurs Evolution Go."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status_code}, msg={self})"


class EvolutionAuthError(EvolutionError):
    """API key invalide ou absente (HTTP 401/403)."""


class EvolutionNotFoundError(EvolutionError):
    """Ressource introuvable — instance, groupe, etc. (HTTP 404)."""


class EvolutionConnectionError(EvolutionError):
    """Impossible de joindre le serveur Evolution Go."""


class EvolutionInstanceError(EvolutionError):
    """Instance WhatsApp déconnectée ou dans un état invalide."""


class EvolutionRateLimitError(EvolutionError):
    """Trop de requêtes (HTTP 429)."""


class EvolutionNotInitializedError(EvolutionError):
    """Singleton non initialisé — appeler EvolutionAPIClient.initialize() d'abord."""


# Enums
# ══════════════════════════════════════════════════════════════════════════════


class WAMediaType(str, Enum):
    """Types de média supportés par POST /send/media."""
    IMAGE    = "image"
    VIDEO    = "video"
    AUDIO    = "audio"
    DOCUMENT = "document"
    STICKER  = "sticker"


class WAParticipantRole(str, Enum):
    MEMBER     = "member"
    ADMIN      = "admin"
    SUPERADMIN = "superadmin"


class WAWebhookEvent(str, Enum):
    """Événements Evolution Go disponibles pour le webhook."""
    # Messagerie
    MESSAGE      = "MESSAGE"
    SEND_MESSAGE = "SEND_MESSAGE"
    # Connexion
    CONNECTION   = "CONNECTION"
    # Groupes  (routés vers l'abonnement GROUP si MESSAGE absent)
    GROUP        = "GROUP"
    # Livraison / lecture
    READ_RECEIPT = "READ_RECEIPT"
    # Newsletter (routé vers NEWSLETTER si MESSAGE absent)
    NEWSLETTER   = "NEWSLETTER"


# ══════════════════════════════════════════════════════════════════════════════
# Modèles (DTOs)  — format réponse Evolution Go : { "data": {...}, "message": "success" }
# ══════════════════════════════════════════════════════════════════════════════


class WAInstanceStatus(BaseModel):
    """Réponse de GET /instance/status."""
    connected: bool  = Field(alias="Connected")
    logged_in: bool  = Field(alias="LoggedIn")
    name:      str   = Field(alias="Name", default="")

    model_config = {"populate_by_name": True}

    @property
    def is_ready(self) -> bool:
        """True si l'instance est connectée ET loggée."""
        return self.connected and self.logged_in


class WAMessageInfo(BaseModel):
    """Champ Info de la réponse d'un message envoyé."""
    id:        str  = Field(alias="ID")
    chat:      str  = Field(alias="Chat")
    sender:    str  = Field(alias="Sender")
    is_group:  bool = Field(alias="IsGroup", default=False)
    timestamp: str  = Field(alias="Timestamp", default="")

    model_config = {"populate_by_name": True}


class WASentMessage(BaseModel):
    """Réponse d'Evolution Go après envoi d'un message (data.Info + data.Message)."""
    info: WAMessageInfo = Field(alias="Info")

    model_config = {"populate_by_name": True}

    @property
    def message_id(self) -> str:
        return self.info.id

    @property
    def chat_jid(self) -> str:
        return self.info.chat


class WAParticipant(BaseModel):
    """Participant d'un groupe WhatsApp."""
    jid:   str
    name:  str | None                 = None
    admin: WAParticipantRole | None   = None

    @property
    def phone_number(self) -> str:
        return self.jid.split("@")[0]

    @property
    def is_admin(self) -> bool:
        return self.admin in (WAParticipantRole.ADMIN, WAParticipantRole.SUPERADMIN)


class WAGroupInfo(BaseModel):
    """Métadonnées d'un groupe WhatsApp (GET /group/info)."""
    id:           str
    subject:      str                            # Nom du groupe
    description:  str | None                    = None
    owner:        str | None                    = None
    creation:     int | None                    = None
    participants: list[WAParticipant]           = Field(default_factory=list)

    @property
    def jid(self) -> str:
        return self.id

    @property
    def admins(self) -> list[WAParticipant]:
        return [p for p in self.participants if p.is_admin]


class WAWebhookConfig(BaseModel):
    """Configuration webhook d'une instance Evolution Go."""
    url:    str
    events: list[WAWebhookEvent] = Field(default_factory=list)
    enabled: bool                = True


class WAGroupParticipantUpdate(BaseModel):
    """
    Payload du webhook GROUP pour GROUP_PARTICIPANTS_UPDATE.
    Utilisé par le handler FastAPI pour la sync automatique des membres.
    """
    id:           str         # JID du groupe
    participants: list[str]   # JIDs concernés
    action:       str         # "add" | "remove" | "promote" | "demote"

    @property
    def is_add(self) -> bool:
        return self.action == "add"

    @property
    def is_remove(self) -> bool:
        return self.action == "remove"


# ══════════════════════════════════════════════════════════════════════════════
# Client principal + Singleton
# ══════════════════════════════════════════════════════════════════════════════


class EvolutionAPIClient:
    """
    Client async pour Evolution Go (WhatsApp self-hosted, version Go).

    ─── Singleton (usage recommandé) ───────────────────────────────────────

    # 2. Accès depuis n'importe où dans le backend
        client = EvolutionAPIClient.get_instance()
        await client.send_text("120363xxx@g.us", "Hello!")

    # 3. Injection FastAPI (optionnel mais propre)
        from fastapi import Depends
        WAClient = Annotated[EvolutionAPIClient, Depends(EvolutionAPIClient.as_dependency)]

    ─── Context manager direct (tests, scripts) ──────────────────────────────

        async with EvolutionAPIClient(base_url=..., api_key=...) as client:
            participants = await client.get_group_participants("120363xxx@g.us")
    """

    # ── Singleton state ──────────────────────────────────────────────────────
    _singleton: ClassVar[EvolutionAPIClient | None] = None

    DEFAULT_WEBHOOK_EVENTS: ClassVar[list[WAWebhookEvent]] = [
        WAWebhookEvent.MESSAGE,
        WAWebhookEvent.CONNECTION,
        WAWebhookEvent.GROUP,
        WAWebhookEvent.READ_RECEIPT,
    ]

    # ── Init ─────────────────────────────────────────────────────────────────

    def __init__(
        self,
        base_url: str,
        api_key:  str,
        *,
        timeout:    float = 30.0,
        send_delay: float = 1.5,
    ) -> None:
        """
        Args:
            base_url:   URL du serveur Evolution Go, ex: "http://localhost:8080"
            api_key:    GLOBAL_API_KEY configuré dans .env
            timeout:    Timeout HTTP global en secondes
            send_delay: Délai (s) avant chaque envoi WA (anti-ban)
        """
        self._send_delay = send_delay
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "apikey":       api_key,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Ferme le client HTTP proprement."""
        await self._http.aclose()

    # ── Singleton API ─────────────────────────────────────────────────────────

    @classmethod
    def initialize(
        cls,
        base_url: str,
        api_key:  str,
        *,
        timeout:    float = 30.0,
        send_delay: float = 1.5,
        force:      bool  = False,
    ) -> "EvolutionAPIClient":
        """
        Crée et enregistre le singleton.
        Lève RuntimeError si déjà initialisé, sauf si force=True.

        Returns l'instance (pour usage en context manager dans le lifespan).
        """
        if cls._singleton is not None and not force:
            raise RuntimeError(
                "EvolutionAPIClient est déjà initialisé. "
                "Utilise force=True pour réinitialiser."
            )
        cls._singleton = cls(
            base_url,
            api_key,
            timeout=timeout,
            send_delay=send_delay,
        )
        logger.info("EvolutionAPIClient initialisé → %s", base_url)
        return cls._singleton

    @classmethod
    def get_instance(cls) -> "EvolutionAPIClient":
        """
        Retourne le singleton initialisé.
        Lève EvolutionNotInitializedError si initialize() n'a pas été appelé.
        """
        if cls._singleton is None:
            raise EvolutionNotInitializedError(
                "EvolutionAPIClient non initialisé. "
                "Appelle EvolutionAPIClient.initialize(...) au démarrage."
            )
        return cls._singleton

    @classmethod
    async def as_dependency(cls) -> "EvolutionAPIClient":
        """
        FastAPI dependency — injecte le client dans les routes.

        Usage :
            WAClient = Annotated[EvolutionAPIClient, Depends(EvolutionAPIClient.as_dependency)]

            @router.post("/messages")
            async def post_message(client: WAClient):
                await client.send_text(...)
        """
        return cls.get_instance()

    @classmethod
    async def teardown(cls) -> None:
        """Ferme le singleton et libère les ressources (appel dans lifespan shutdown)."""
        if cls._singleton is not None:
            await cls._singleton.close()
            cls._singleton = None
            logger.info("EvolutionAPIClient fermé.")

    # ── HTTP core ─────────────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path:   str,
        *,
        params: dict[str, Any] | None = None,
        json:   dict[str, Any] | None = None,
    ) -> Any:
        """
        Effectue une requête HTTP et retourne le champ `data` de la réponse.
        Evolution Go encapsule toujours le payload dans { "data": {...}, "message": "success" }.
        """
        url = f"/{path.lstrip('/')}"
        logger.debug("→ %s %s  params=%s", method, url, params)

        try:
            response = await self._http.request(method, url, params=params, json=json)
        except httpx.ConnectError as exc:
            raise EvolutionConnectionError(
                f"Impossible de joindre Evolution Go ({self._http.base_url})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EvolutionError(f"Timeout sur {method} {url}") from exc

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: httpx.Response) -> Any:
        """Mappe les codes HTTP → exceptions métier et extrait response['data']."""
        status = response.status_code

        if status in (401, 403):
            raise EvolutionAuthError("API key invalide ou accès refusé", status_code=status)
        if status == 404:
            raise EvolutionNotFoundError(
                "Ressource introuvable", status_code=404, payload=response.text
            )
        if status == 429:
            raise EvolutionRateLimitError("Rate limit atteint", status_code=429)
        if response.is_error:
            raise EvolutionError(
                f"Erreur Evolution Go (HTTP {status})",
                status_code=status,
                payload=response.text,
            )

        body = response.json()
        # Evolution Go enveloppe dans { "data": {...}, "message": "success" }
        return body

    # ── Instance / Connexion ──────────────────────────────────────────────────

    async def get_status(self) -> WAInstanceStatus:
        """
        Retourne l'état de connexion de l'instance.
        GET /instance/status → { Connected, LoggedIn, Name }
        """
        data = await self._request("GET", "instance/status")
        return WAInstanceStatus.model_validate(data.get("data"))

    async def is_ready(self) -> bool:
        """True si l'instance est connectée ET loggée dans WhatsApp."""
        status = await self.get_status()
        return status.is_ready

    async def connect(self) -> bool:
        """
        Démarre la connexion et retourne le QR code ou le statut.
        GET /instance/connect
        """
        payload = {
          "immediate": True,
          "subscribe": [
            "GROUP",
          ],
          "webhookUrl": "http://ngl_clone_api:8000/v1/threads/webhook"
        }

        res = await self._request("POST", "instance/connect", json=payload)
        if isinstance(res, dict):
            has_success = res.get("message", "") == "success"
            if has_success:
                logger.info("Instance connectée avec succès.")
            else:
                logger.warning("Instance non connectée, mais message inattendu : %s", res)
            return has_success
        logger.error("Réponse inattendue de /instance/connect : %s", res)
        return False

    async def logout(self) -> None:
        """Déconnecte l'instance (logout + suppression de session WA)."""
        await self._request("POST", "instance/logout")
        logger.info("Instance déconnectée.")

    async def get_qr_code(self) -> dict[str, Any]:
        """
        Retourne le QR code de l'instance (pour re-scan).
        GET /instance/qrcode
        """
        return await self._request("GET", "instance/qrcode")

    # ── Groupes ───────────────────────────────────────────────────────────────

    async def get_group_info(self, group_jid: str) -> WAGroupInfo:
        """
        Retourne les métadonnées d'un groupe.
        GET /group/info?groupJid={jid}
        """
        data = await self._request(
            "GET",
            "group/info",
            params={"groupJid": group_jid},
        )
        return WAGroupInfo.model_validate(data)

    async def get_group_participants(self, group_jid: str) -> list[WAParticipant]:
        """
        Retourne la liste des participants d'un groupe.
        GET /group/participants?groupJid={jid}

        Point d'entrée principal pour l'import automatique des membres en BD.
        """
        data = await self._request(
            "GET",
            "group/participants",
            params={"groupJid": group_jid},
        )
        data = data.get("data")
        raw: list[dict[str, Any]] = (
            data.get("participants", data) if isinstance(data, dict) else data
        )
        return [WAParticipant.model_validate(p) for p in raw]

    async def get_group_with_participants(self, group_jid: str) -> WAGroupInfo:
        """
        Convenience : info + participants en deux appels parallèles (asyncio.gather).
        """
        info, participants = await asyncio.gather(
            self.get_group_info(group_jid),
            self.get_group_participants(group_jid),
        )
        info.participants = participants
        return info

    async def list_groups(self) -> list[WAGroupInfo]:
        """
        Retourne tous les groupes auxquels l'instance participe.
        GET /group/list
        """
        data = await self._request("GET", "group/list")
        groups: list[dict[str, Any]] = data if isinstance(data, list) else data.get("groups", [])
        return [WAGroupInfo.model_validate(g) for g in groups]

    async def join_group(self, invite_code: str) -> None:
        """
        Rejoint un groupe WhatsApp via son code d'invitation.
        POST /group/join  body: { "code": "AbCdEfGhIjKl" }

        Args:
            invite_code: Code extrait du lien d'invitation.
                         Ex: pour "https://chat.whatsapp.com/AbCdEfGhIjKl"
                         → invite_code = "AbCdEfGhIjKl"
                         Utilise extract_invite_code() pour extraire depuis une URL.
        """
        await self._request("POST", "group/join", json={"code": invite_code})
        logger.info("Groupe rejoint avec le code : %s", invite_code)

    async def get_group_invite_link(
        self,
        group_jid: str,
        *,
        reset: bool = False,
    ) -> str:
        """
        Retourne le lien d'invitation d'un groupe.
        POST /group/invitelink  body: { "groupJid": ..., "reset": bool }

        Args:
            group_jid: JID du groupe, ex: "120363xxx@g.us"
            reset:     True pour régénérer le lien (invalide l'ancien)

        Returns:
            URL complète, ex: "https://chat.whatsapp.com/AbCdEfGhIjKl"
        """
        data = await self._request(
            "POST",
            "group/invitelink",
            json={"groupJid": group_jid, "reset": reset},
        )
        return data.get("inviteLink", data) if isinstance(data, dict) else str(data)

    # ── Messages texte ────────────────────────────────────────────────────────

    async def send_text(
        self,
        number: str,
        text:   str,
        *,
        delay:        float | None  = None,
        mention_all:  bool          = False,
        mention_jids: list[str] | None     = None,
    ) -> WASentMessage:
        """
        Envoie un message texte.
        POST /send/text

        Args:
            number:       JID du destinataire (individu ou groupe)
            text:         Contenu du message
            delay:        Override délai anti-ban (None = send_delay du client)
            mention_all:  Mentionne tous les membres du groupe (@everyone)
            mention_jids: JIDs spécifiques à mentionner
        """
        await asyncio.sleep(delay if delay is not None else self._send_delay)
        payload: dict[str, Any] = {
            "number": number,
            "text": text,
            "delay": 0,
            "formatJid": True,
        }
        if mention_all:
            payload["mentionAll"] = True
        if mention_jids:
            payload["mentionedJid"] = ",".join(mention_jids)

        data = await self._request("POST", "send/text", json=payload)
        sent = WASentMessage.model_validate(data.get("data"))
        logger.info("Text → %s | id=%s", number, sent.message_id)
        return sent

    async def send_text_with_mentions(
        self,
        number:       str,
        text:         str,
        mention_jids: list[str],
        *,
        delay: float | None = None,
    ) -> WASentMessage:
        """
        Raccourci pour send_text avec mentions.
        Construit le texte avec @numéros si les JIDs sont dans le texte.
        """
        return await self.send_text(
            number,
            text,
            delay=delay,
            mention_jids=mention_jids,
        )

    # ── Messages médias ───────────────────────────────────────────────────────

    async def send_media(
        self,
        number:   str,
        url:      str,
        media_type: WAMediaType,
        *,
        caption:      str | None   = None,
        filename:     str | None   = None,
        delay:        float | None = None,
        mention_all:  bool         = False,
        mention_jids: list[str] | None    = None,
    ) -> WASentMessage:
        """
        Envoie un fichier média (image, vidéo, audio, document).
        POST /send/media

        Args:
            mention_jids:
            mention_all:
            number:     JID du destinataire
            url:        URL publique du média OU base64 encodé
                        (si la valeur ne commence pas par http/https, traité comme base64)
            media_type: WAMediaType.IMAGE | VIDEO | AUDIO | DOCUMENT | STICKER
            caption:    Légende (supportée pour image, vidéo, document)
            filename:   Nom de fichier (utile pour DOCUMENT)
            delay:      Override délai anti-ban
        """
        await asyncio.sleep(delay if delay is not None else self._send_delay)
        payload: dict[str, Any] = {
            "number": number,
            "url":    url,
            "type":   media_type.value,
        }
        if caption:
            payload["caption"] = caption
        if filename:
            payload["filename"] = filename
        if mention_all:
            payload["mentionAll"] = True
        if mention_jids:
            payload["mentionedJid"] = ",".join(mention_jids)

        data = await self._request("POST", "send/media", json=payload)
        sent = WASentMessage.model_validate(data)
        logger.info("%s → %s | id=%s", media_type.value, number, sent.message_id)
        return sent

    async def send_image(
        self,
        number:  str,
        url:     str,
        caption: str | None  = None,
        *,
        delay:   float | None = None,
    ) -> WASentMessage:
        """
        Raccourci : envoie une image.
        Accepte URL publique ou base64 (le serveur détecte automatiquement).
        """
        return await self.send_media(
            number, url, WAMediaType.IMAGE, caption=caption, delay=delay
        )

    async def send_video(
        self,
        number:  str,
        url:     str,
        caption: str | None  = None,
        *,
        delay:   float | None = None,
    ) -> WASentMessage:
        """
        Raccourci : envoie une vidéo.
        Accepte URL publique ou base64.
        """
        return await self.send_media(
            number, url, WAMediaType.VIDEO, caption=caption, delay=delay
        )

    async def send_audio(
        self,
        number: str,
        url:    str,
        *,
        delay:  float | None = None,
    ) -> WASentMessage:
        """Raccourci : envoie un fichier audio (mp3, ogg, etc.)."""
        return await self.send_media(number, url, WAMediaType.AUDIO, delay=delay)

    async def send_document(
        self,
        number:   str,
        url:      str,
        filename: str,
        caption:  str | None  = None,
        *,
        delay:    float | None = None,
    ) -> WASentMessage:
        """Raccourci : envoie un document avec son nom de fichier."""
        return await self.send_media(
            number, url, WAMediaType.DOCUMENT,
            caption=caption, filename=filename, delay=delay,
        )

    async def batch_send_text(
        self,
        targets: list[tuple[str, str]],
        *,
        delay: float | None = None,
    ) -> list[WASentMessage | BaseException]:
        """
        Envoie séquentiellement (anti-ban) une liste de messages.

        Args:
            targets: Liste de tuples (jid, texte)
            delay:   Délai entre chaque envoi

        Returns:
            Liste de WASentMessage ou exceptions pour chaque tentative.
        """
        results: list[WASentMessage | BaseException] = []
        for jid, text in targets:
            try:
                sent = await self.send_text(jid, text, delay=delay)
                results.append(sent)
            except EvolutionError as exc:
                logger.exception("Échec envoi → %s : %s", jid, exc)
                results.append(exc)
        return results

    async def send_reaction(
        self,
        number:     str,
        message_id: str,
        reaction:   str,
        *,
        participant: str | None = None,
    ) -> None:
        """
        Envoie une réaction emoji sur un message.
        POST /send/reaction

        Args:
            number:      JID du groupe ou contact
            message_id:  ID du message cible (WASentMessage.message_id)
            reaction:    Emoji, ex: "❤️", "😂", "🔥". Chaîne vide pour retirer.
            participant: JID de l'expéditeur original (requis dans les groupes)
        """
        payload: dict[str, Any] = {
            "number":    number,
            "messageId": message_id,
            "reaction":  reaction,
        }
        if participant:
            payload["participant"] = participant

        await self._request("POST", "send/reaction", json=payload)

    # ── Webhook ───────────────────────────────────────────────────────────────

    async def configure_webhook(
        self,
        url:    str,
        events: list[WAWebhookEvent] | None = None,
        *,
        enabled: bool = True,
    ) -> WAWebhookConfig:
        """
        Configure le webhook de l'instance.
        POST /webhook/set  (ou PUT selon la version)

        À appeler une fois au démarrage ou lors du changement d'URL publique
        (ex: après un redéploiement avec nouvelle URL ngrok).

        Args:
            url:     URL publique FastAPI, ex: "https://xxx.ngrok.io/webhooks/wa"
            events:  Événements à écouter (défaut : DEFAULT_WEBHOOK_EVENTS)
            enabled: Active ou désactive le webhook
        """
        active_events = events or self.DEFAULT_WEBHOOK_EVENTS
        config = WAWebhookConfig(url=url, events=active_events, enabled=enabled)
        await self._request(
            "POST",
            "webhook/set",
            json={
                "url":     config.url,
                "enabled": config.enabled,
                "events":  [e.value for e in config.events],
            },
        )
        logger.info(
            "Webhook configuré → %s | events=%s",
            url, [e.value for e in active_events],
        )
        return config

    async def get_webhook_config(self) -> WAWebhookConfig:
        """Retourne la configuration webhook active. GET /webhook/find"""
        data = await self._request("GET", "webhook/find")
        valid = {e.value for e in WAWebhookEvent}
        return WAWebhookConfig(
            url=data.get("url", ""),
            enabled=data.get("enabled", False),
            events=[
                WAWebhookEvent(e)
                for e in data.get("events", [])
                if e in valid
            ],
        )

    # ── Helpers statiques ─────────────────────────────────────────────────────

    @staticmethod
    def jid_to_phone(jid: str) -> str:
        """'22890xxxxxxxx@s.whatsapp.net' → '22890xxxxxxxx'"""
        return jid.split("@")[0]

    @staticmethod
    def phone_to_jid(phone: str) -> str:
        """'+22890xxxxxxxx' ou '22890xxxxxxxx' → '22890xxxxxxxx@s.whatsapp.net'"""
        clean = phone.lstrip("+").replace(" ", "").replace("-", "")
        return f"{clean}@s.whatsapp.net"

    @staticmethod
    def is_group_jid(jid: str) -> bool:
        """True si le JID est un groupe (@g.us), False si individuel (@s.whatsapp.net)."""
        return jid.endswith("@g.us")

    @staticmethod
    def extract_invite_code(invite_url: str) -> str:
        """
        Extrait le code depuis une URL d'invitation WhatsApp.
        "https://chat.whatsapp.com/AbCdEfGhIjKl" → "AbCdEfGhIjKl"
        """
        return invite_url.rstrip("/").split("/")[-1]

    @staticmethod
    def parse_participant_update(payload: dict[str, Any]) -> WAGroupParticipantUpdate:
        """
        Parse le payload brut du webhook GROUP (action: add/remove/promote/demote).
        À utiliser dans le handler FastAPI pour la sync automatique des membres.

        Usage dans un webhook handler :
            update = EvolutionAPIClient.parse_participant_update(webhook_body["data"])
            if update.is_add:
                await sync_service.add_member(update.id, update.participants[0])
        """
        return WAGroupParticipantUpdate.model_validate(payload)

async def initialize_evolution_client():
    """
    Initialise le singleton EvolutionAPIClient et connecte l'instance WhatsApp.
    
    Note: Ne pas utiliser async with ici car il fermerait le client immédiatement.
    Le client doit rester ouvert pour traiter les requêtes webhook.
    """
    client = EvolutionAPIClient.initialize(
        base_url=EVO_GLOBAL_API_URL,
        api_key=EVO_ACTIVE_INSTANCE_API_KEY,
    )
    if not await client.connect():
        raise RuntimeError("WhatsApp non connecté")
    logger.info("WhatsApp connecté avec succès")
    return client

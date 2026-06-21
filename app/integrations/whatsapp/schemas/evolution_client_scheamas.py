from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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

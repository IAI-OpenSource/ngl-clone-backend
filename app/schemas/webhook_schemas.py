"""
Schémas Pydantic pour les événements webhook WhatsApp (Evolution API).

Approche simplifiée: on valide la structure de base et on laisse le handler
accéder aux données brutes avec des accès sécurisés.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Énumérations
# ============================================================================

class WebhookEventType(str, Enum):
    """Types d'événements webhook WhatsApp."""
    JOINED_GROUP = "JoinedGroup"
    MESSAGE = "Message"


# ============================================================================
# Schéma de base pour le webhook
# ============================================================================

class WebhookBasePayload(BaseModel):
    """
    Schéma de base pour valider un payload webhook.
    Valide que les champs requis sont présents.
    """
    model_config = ConfigDict(from_attributes=True)
    
    event: WebhookEventType = Field(..., description="Type d'événement")
    instanceId: str = Field(..., description="ID de l'instance")
    instanceName: str = Field(..., description="Nom de l'instance")
    instanceToken: str = Field(..., description="Token de l'instance")
    data: Dict[str, Any] = Field(..., description="Données de l'événement")


# ============================================================================
# Schéma de réponse
# ============================================================================

class WebhookResponse(BaseModel):
    """Réponse standard pour le webhook."""
    success: bool = Field(..., description="Indique si le traitement a réussi")
    message: str = Field(..., description="Message de réponse")
    event_type: str = Field(..., description="Type d'événement traité")
    processed_at: datetime = Field(default_factory=datetime.now, description="Date de traitement")


# ============================================================================
# Modèles structurés pour accès typé (optionnel)
# ============================================================================

class ParticipantInfo(BaseModel):
    """Informations sur un participant."""
    JID: str
    PhoneNumber: Optional[str] = None
    LID: Optional[str] = None
    IsAdmin: bool = False
    IsSuperAdmin: bool = False
    DisplayName: Optional[str] = None
    Error: int = 0
    AddRequest: Optional[Any] = None


class GroupInfo(BaseModel):
    """Informations sur un groupe WhatsApp."""
    JID: str
    OwnerJID: Optional[str] = None
    OwnerPN: Optional[str] = None
    Name: str
    NameSetAt: Optional[datetime] = None
    NameSetBy: Optional[str] = None
    NameSetByPN: Optional[str] = None
    Topic: Optional[str] = None
    TopicID: Optional[str] = None
    TopicSetAt: Optional[datetime] = None
    TopicSetBy: Optional[str] = None
    TopicSetByPN: Optional[str] = None
    TopicDeleted: bool = False
    IsLocked: bool = False
    IsAnnounce: bool = False
    AnnounceVersionID: Optional[str] = None
    IsEphemeral: bool = False
    DisappearingTimer: int = 0
    IsIncognito: bool = False
    IsParent: bool = False
    DefaultMembershipApprovalMode: Optional[str] = None
    LinkedParentJID: Optional[str] = None
    IsDefaultSubGroup: bool = False
    IsJoinApprovalRequired: bool = False
    AddressingMode: Optional[str] = None
    GroupCreated: Optional[datetime] = None
    CreatorCountryCode: Optional[str] = None
    ParticipantVersionID: Optional[str] = None
    Participants: List[ParticipantInfo] = Field(default_factory=list)
    ParticipantCount: int = 0
    MemberAddMode: Optional[str] = None
    Suspended: bool = False


class JoinedGroupEvent(BaseModel):
    """Événement JoinedGroup structuré."""
    data: GroupInfo
    event: WebhookEventType = WebhookEventType.JOINED_GROUP
    instanceId: str
    instanceName: str
    instanceToken: str


class MessageInfo(BaseModel):
    """Informations sur un message."""
    AddressingMode: Optional[str] = None
    BroadcastListOwner: Optional[str] = None
    BroadcastRecipients: Optional[List[str]] = None
    Category: Optional[str] = None
    Chat: str
    DeviceSentMeta: Optional[Any] = None
    Edit: Optional[str] = None
    ID: str
    IsFromMe: bool = False
    IsGroup: bool = False
    MediaType: Optional[str] = None
    MsgBotInfo: Optional[Dict[str, Any]] = None
    MsgMetaInfo: Optional[Dict[str, Any]] = None
    Multicast: bool = False
    PushName: Optional[str] = None
    RecipientAlt: Optional[str] = None
    Sender: str
    SenderAlt: Optional[str] = None
    ServerID: int = 0
    Timestamp: datetime
    Type: str
    VerifiedName: Optional[str] = None


class MessageContent(BaseModel):
    """Contenu d'un message."""
    conversation: Optional[str] = None
    messageContextInfo: Optional[Dict[str, Any]] = None


class MessageData(BaseModel):
    """Données d'un événement Message."""
    Info: MessageInfo
    IsBotInvoke: bool = False
    IsDocumentWithCaption: bool = False
    IsEdit: bool = False
    IsEphemeral: bool = False
    IsLottieSticker: bool = False
    IsViewOnce: bool = False
    IsViewOnceV2: bool = False
    IsViewOnceV2Extension: bool = False
    Message: MessageContent
    NewsletterMeta: Optional[Any] = None
    RetryCount: int = 0
    SourceWebMsg: Optional[Any] = None
    UnavailableRequestID: Optional[str] = None
    groupData: GroupInfo


class MessageEvent(BaseModel):
    """Événement Message structuré."""
    data: MessageData
    event: WebhookEventType = WebhookEventType.MESSAGE
    instanceId: str
    instanceName: str
    instanceToken: str


# ============================================================================
# Parser principal
# ============================================================================

def parse_webhook_event(payload: dict) -> Union[JoinedGroupEvent, MessageEvent]:
        """
        Parse le payload brut et retourne l'événement structuré.
        
        Args:
            payload: Le payload brut reçu du webhook
            
        Returns:
            JoinedGroupEvent ou MessageEvent selon le type
            
        Raises:
            ValueError: Si le type d'événement n'est pas supporté ou si la validation échoue
        """
        # Valider le payload de base
        base = WebhookBasePayload(**payload)
        
        event_type = base.event
        
        try:
            if event_type == WebhookEventType.JOINED_GROUP:
                # Pour JoinedGroup, data contient directement les infos du groupe
                group_data = GroupInfo(**base.data)
                return JoinedGroupEvent(
                    data=group_data,
                    event=base.event,
                    instanceId=base.instanceId,
                    instanceName=base.instanceName,
                    instanceToken=base.instanceToken
                )
            
            elif event_type == WebhookEventType.MESSAGE:
                message_data = MessageData(**base.data)
                return MessageEvent(
                    data=message_data,
                    event=base.event,
                    instanceId=base.instanceId,
                    instanceName=base.instanceName,
                    instanceToken=base.instanceToken
                )
            
            else:
                raise ValueError(f"Type d'événement non supporté: {event_type}")
                
        except Exception as e:
            raise ValueError(f"Erreur de validation pour {event_type}: {str(e)}") from e


# Alias pour compatibilité
WebhookPayload = WebhookBasePayload

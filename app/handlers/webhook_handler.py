"""
Handler pour gérer les événements webhook WhatsApp (Evolution API).

Ce module gère deux types d'événements principaux :
1. JoinedGroup - Quand un utilisateur/bot rejoint ou est ajouté à un groupe
2. Message - Quand un message est envoyé dans un groupe
"""

import logging
from datetime import datetime, timezone

from app.schemas.webhook_schemas import (
    JoinedGroupEvent,
    MessageEvent,
    WebhookEventType,
    WebhookResponse,
    parse_webhook_event,
)

# Configuration du logger
logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Handler principal pour les événements webhook WhatsApp.
    
    Ce handler parse les payloads entrants, identifie le type d'événement,
    et délègue le traitement à la méthode appropriée.
    """

    def __init__(self):
        """Initialise le handler."""
        logger.info("WebhookHandler initialisé")

    async def handle_webhook(
        self,
        payload: dict
    ) -> WebhookResponse:
        """
        Méthode principale pour traiter un événement webhook.
        
        Args:
            payload: Le payload brut reçu du webhook
            
        Returns:
            WebhookResponse: Réponse standardisée
            
        Raises:
            ValueError: Si le payload est invalide ou le type d'événement non supporté
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Début du traitement du webhook à {start_time}")

        try:
            # Parser l'événement spécifique
            event = parse_webhook_event(payload)
            
            # Traiter selon le type
            if isinstance(event, JoinedGroupEvent):
                response = await self._handle_joined_group(event)
            elif isinstance(event, MessageEvent):
                response = await self._handle_message(event)
            else:
                raise ValueError(f"Type d'événement non géré: {event.event}")

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Webhook traité en {duration:.3f}s - Type: {event.event.value}")
            
            return response

        except Exception as e:
            logger.error(f"Erreur lors du traitement du webhook: {str(e)}", exc_info=True)
            return WebhookResponse(
                success=False,
                message=f"Erreur: {str(e)}",
                event_type=payload.get("event", "unknown"),
                processed_at=datetime.now(timezone.utc)
            )

    async def _handle_joined_group(
        self,
        event: JoinedGroupEvent
    ) -> WebhookResponse:
        """
        Traite un événement JoinedGroup.
        
        Cet événement est déclenché quand :
        - Un bot rejoint un groupe
        - Un utilisateur est ajouté à un groupe
        - Un groupe est créé
        
        Args:
            event: L'événement JoinedGroup parsé
            
        Returns:
            WebhookResponse: Réponse de traitement
        """
        logger.info(f"Traitement de JoinedGroup pour {event.data.JID}")
        
        group_data = event.data
        
        # Extraire les informations importantes
        group_info = {
            "jid": group_data.JID,
            "name": group_data.Name,
            "owner_jid": group_data.OwnerJID,
            "owner_phone": group_data.OwnerPN,
            "participant_count": group_data.ParticipantCount,
            "created_at": group_data.GroupCreated,
            "is_locked": group_data.IsLocked,
            "is_announce": group_data.IsAnnounce,
        }
        
        participants_info = [
            {
                "jid": p.JID,
                "phone": p.PhoneNumber,
                "is_admin": p.IsAdmin,
                "is_super_admin": p.IsSuperAdmin,
            }
            for p in group_data.Participants
        ]
        
        logger.info(f"Groupe: {group_info}")
        logger.info(f"Participants ({len(participants_info)}): {participants_info}")
        
        # Logique métier à implémenter ici
        # Exemples :
        # - Mettre à jour la base de données avec les infos du groupe
        # - Envoyer une notification
        # - Synchroniser les membres du groupe
        
        # TODO: Ajouter la logique métier spécifique
        # await self._sync_group_to_database(group_data)
        # await self._notify_group_join(event)
        
        return WebhookResponse(
            success=True,
            message=f"JoinedGroup traité - Groupe: {group_data.Name} ({group_data.JID})",
            event_type=WebhookEventType.JOINED_GROUP.value,
            processed_at=datetime.now(timezone.utc)
        )

    async def _handle_message(
        self,
        event: MessageEvent
    ) -> WebhookResponse:
        """
        Traite un événement Message.
        
        Cet événement est déclenché quand un message est envoyé dans un groupe.
        
        Args:
            event: L'événement Message parsé
            
        Returns:
            WebhookResponse: Réponse de traitement
        """
        logger.info(f"Traitement de Message dans {event.data.Info.Chat}")
        
        message_info = event.data.Info
        message_content = event.data.Message
        group_data = event.data.groupData
        
        # Extraire les informations importantes
        message_details = {
            "message_id": message_info.ID,
            "type": message_info.Type,
            "sender_jid": message_info.Sender,
            "sender_phone": message_info.SenderAlt,
            "sender_name": message_info.PushName,
            "chat_jid": message_info.Chat,
            "timestamp": message_info.Timestamp,
            "is_group": message_info.IsGroup,
            "conversation": message_content.conversation,
        }
        
        group_details = {
            "jid": group_data.JID,
            "name": group_data.Name,
            "owner_jid": group_data.OwnerJID,
            "participant_count": group_data.ParticipantCount,
        }
        
        logger.info(f"Message: {message_details}")
        logger.info(f"Groupe: {group_details}")
        
        # Logique métier à implémenter ici
        # Exemples :
        # - Enregistrer le message dans la base de données
        # - Détecter les commandes (ex: /mapgroup)
        # - Répondre automatiquement
        # - Notifier les administrateurs
        
        # TODO: Ajouter la logique métier spécifique
        # if message_content.conversation and message_content.conversation.startswith("/"):
        #     await self._handle_command(message_content.conversation, message_info, group_data)
        # 
        # await self._save_message_to_database(message_info, message_content, group_data)
        
        # Vérifier si c'est une commande
        conversation = message_content.conversation or ""
        if conversation.startswith("/"):
            logger.info(f"Commande détectée: {conversation}")
            # TODO: Implémenter le traitement des commandes
            # await self._process_command(conversation, message_info, group_data)

        return WebhookResponse(
            success=True,
            message=f"Message traité - Type: {message_info.Type}, Groupe: {group_data.Name}",
            event_type=WebhookEventType.MESSAGE.value,
            processed_at=datetime.now(timezone.utc)
        )

    # =========================================================================
    # Méthodes utilitaires (à implémenter selon les besoins)
    # =========================================================================

    async def _sync_group_to_database(
        self,
        group_data: dict
    ) -> None:
        """
        Synchronise les informations du groupe avec la base de données.
        
        Args:
            group_data: Données du groupe à synchroniser
        """
        # TODO: Implémenter la synchronisation
        logger.debug(f"Synchronisation du groupe: {group_data}")
        pass

    async def _save_message_to_database(
        self,
        message_info: dict,
        message_content: dict,
        group_data: dict
    ) -> None:
        """
        Enregistre un message dans la base de données.
        
        Args:
            message_info: Informations sur le message
            message_content: Contenu du message
            group_data: Données du groupe
        """
        # TODO: Implémenter l'enregistrement
        logger.debug(f"Enregistrement du message: {message_info.get('id')}")
        pass

    async def _handle_command(
        self,
        command: str,
        message_info: dict,
        group_data: dict
    ) -> None:
        """
        Traite une commande reçue dans un message.
        
        Args:
            command: La commande à traiter (ex: "/mapgroup")
            message_info: Informations sur le message
            group_data: Données du groupe
        """
        # TODO: Implémenter le traitement des commandes
        logger.info(f"Traitement de la commande: {command}")
        pass

    async def _notify_group_join(
        self,
        event: JoinedGroupEvent
    ) -> None:
        """
        Envoie une notification pour un événement JoinedGroup.
        
        Args:
            event: L'événement JoinedGroup
        """
        # TODO: Implémenter les notifications
        logger.debug(f"Notification pour JoinedGroup: {event.data.Name}")
        pass


# Instance singleton du handler
def get_webhook_handler() -> WebhookHandler:
    """
    Retourne une instance du WebhookHandler.
    
    Returns:
        WebhookHandler: Instance du handler
    """
    return WebhookHandler()

"""
Handler pour gérer les événements webhook WhatsApp (Evolution API).

Ce module gère deux types d'événements principaux :
1. JoinedGroup - Quand un utilisateur/bot rejoint ou est ajouté à un groupe
2. Message - Quand un message est envoyé dans un groupe
"""

import json
import logging
from datetime import datetime, timezone

from app.schemas.webhook_schemas import (
    JoinedGroupEvent,
    MessageEvent,
    WebhookEventType,
    WebhookResponse,
    parse_webhook_event,
)
from fastapi import Request
from app.whatsapp.base.client_handler import client_command_handler

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
        req: Request
    ) :
        """
        Méthode principale pour traiter un événement webhook.
        
        Args:
            req: La requête HTTP reçue
            
        Returns:
            WebhookResponse: Réponse standardisée
            
        Raises:
            ValueError: Si le payload est invalide ou le type d'événement non supporté
        """

        start_time = datetime.now(timezone.utc)
        logger.info(f"Début du traitement du webhook à {start_time}")

        try:
            # Vérification ultra-optimisée : lire le body brut et vérifier l'event type
            # avant de faire un parsing complet
            body = await req.body()
            
            # Vérifier rapidement si c'est un événement géré sans parser tout le JSON
            if b'"event":"Message"' not in body and b'"event":"JoinedGroup"' not in body:
                # Événement non géré, ignorer sans parsing complet
                logger.debug("Événement non géré détecté, ignoré sans parsing")
                return
            
            # Parser uniquement si c'est un événement géré
            payload = json.loads(body)
            logger.debug(payload)
            event = parse_webhook_event(payload)

            # Traiter selon le type
            if isinstance(event, JoinedGroupEvent):
                await self._handle_joined_group(event)
            elif isinstance(event, MessageEvent):
                await self._handle_message(event)
            else:
                raise ValueError(f"Type d'événement non géré: {event.event}")

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Webhook traité en {duration:.3f}s - Type: {event.event.value}")


        except Exception as e:
            logger.error(f"Erreur lors du traitement du webhook: {str(e)}", exc_info=True)


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
    @staticmethod
    async def _handle_message(
        event: MessageEvent
    ) -> None:
        """
        Traite un événement Message.
        
        Cet événement est déclenché quand un message est envoyé dans un groupe.
        
        Args:
            event: L'événement Message parsé
            
        Returns:
            WebhookResponse: Réponse de traitement
        """
        logger.info(f"Traitement de Message dans {event.data.Info.Chat}")
        msg = event.data.Message.conversation
        is_command = msg and msg.startswith("/")
        if is_command:
            await client_command_handler.process(event)

# Instance singleton du handler
def get_webhook_handler() -> WebhookHandler:
    """
    Retourne une instance du WebhookHandler.
    
    Returns:
        WebhookHandler: Instance du handler
    """
    return WebhookHandler()

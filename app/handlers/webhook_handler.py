"""
Handler pour gérer les événements webhook WhatsApp (Evolution API).

Ce module gère deux types d'événements principaux :
1. JoinedGroup - Quand un utilisateur/bot rejoint ou est ajouté à un groupe
2. Message - Quand un message est envoyé dans un groupe
"""

import json
import logging
from datetime import datetime, timezone

from app.integrations.evolution_client import EvolutionAPIClient
from app.schemas.webhook_schemas import (
    JoinedGroupEvent,
    MessageEvent,
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
            logger.info(f"Full Raw Payload : {json.dumps(payload, indent=2)})")

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

    @staticmethod
    async def _handle_joined_group(
        event: JoinedGroupEvent
    ) -> None:
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

        # Envoyer un message de présentation dans le groupe
        try:
            evo_client = EvolutionAPIClient.get_instance()
            await evo_client.send_text(
                number=group_data.JID,
                text=(
                    "👋 Kpakpara raté à tous !\n\n"
                    "Je suis votre assistant WhatsApp. 🤖\n\n"
                    "Pour associer ce groupe à un thread et commencer à gérer vos messages, "
                    "utilisez la commande :\n\n"
                    "🔗 */map_group*\n\n"
                    "C'est tout !"
                )
            )
            logger.info(f"Message de présentation envoyé au groupe {group_data.JID}")
        except Exception as e:
            logger.error(f"Échec de l'envoi du message de présentation: {e}")

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
        logger.info(f"Message : {msg}")
        logger.info(f"Full Payload : {event.model_dump_json(indent=2)}")
        if msg is not None and msg.startswith("/"):
            command = msg.strip().split()[0]
            await client_command_handler.process(event, command)

# Instance singleton du handler
def get_webhook_handler() -> WebhookHandler:
    """
    Retourne une instance du WebhookHandler.
    
    Returns:
        WebhookHandler: Instance du handler
    """
    return WebhookHandler()

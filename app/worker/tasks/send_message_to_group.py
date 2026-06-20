from logging import getLogger
from uuid import UUID

from celery import shared_task

from app.db.session import AsyncSessionLocal
from app.repositories.message_repository import MessageRepository
from app.repositories.thread_repository import ThreadRepository
from app.worker.tasks.base.async_loop_manager import task_async_loop_manager
from app.worker.tasks.base.workers_task_names import WorkersTaskNames
from app.integrations.evolution_client import (
    EvolutionAPIClient,
    EvolutionError,
    EvolutionNotInitializedError,
)
from app.core.config import EVO_GLOBAL_API_URL, EVO_ACTIVE_INSTANCE_API_KEY
from app.db.models.enums.enums import WAStatus

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.SEND_MESSAGE_TO_GROUP)
def send_message_to_group(message_id: str):
    """Tâche Celery pour envoyer un message dans un groupe WhatsApp via Evolution Go.

    Args:
        message_id: UUID du message (string)
    """
    groupe_uuid = UUID(message_id)
    logger.info(f"Enqueue envoi WA pour le message {message_id}")
    task_async_loop_manager.run_async(_send_message_to_group_async(groupe_uuid))


async def _send_message_to_group_async(message_id: UUID):
    db_session = AsyncSessionLocal()
    try:
        message_repo = MessageRepository(db_session)
        thread_repo = ThreadRepository(db_session)

        # Récupérer message + mentions
        msg_res = await message_repo.get_message_by_id_with_mentions(message_id=message_id)
        if msg_res.is_error():
            logger.error(f"Message {message_id} introuvable: {msg_res.error}")
            return

        message, mentioned_members = msg_res.data

        # Récupérer le thread pour obtenir le wa_group_jid
        thread_res = await thread_repo.get_thread_by_id(thread_id=message.thread_id)
        if thread_res.is_error():
            logger.error(f"Thread pour message {message_id} introuvable: {thread_res.error}")
            return

        thread = thread_res.data
        group_jid = thread.wa_group_jid

        # Initialiser le client Evolution si nécessaire
        try:
            client = EvolutionAPIClient.get_instance()
        except EvolutionNotInitializedError:
            # Initialise avec les variables d'environnement gérées par config
            EvolutionAPIClient.initialize(base_url=EVO_GLOBAL_API_URL, api_key=EVO_ACTIVE_INSTANCE_API_KEY)
            client = EvolutionAPIClient.get_instance()

        # Préparer mentions (JIDs)
        mention_jids = [m.wa_jid for m in mentioned_members if m.wa_jid is not None]

        # Envoyer le message
        try:
            if mention_jids:
                sent = await client.send_text_with_mentions(number=group_jid, text=message.content, mention_jids=mention_jids)
            else:
                sent = await client.send_text(number=group_jid, text=message.content)

            # Mettre à jour le message en base avec le statut et l'ID WA
            await message_repo.update_message(message_id=message_id, wa_message_id=sent.message_id, wa_status=WAStatus.SENT)
            await db_session.commit()
            logger.info(f"Message {message_id} envoyé via WA id={sent.message_id}")

        except EvolutionError as exc:
            logger.exception("Erreur Evolution lors de l'envoi du message %s: %s", message_id, exc)
            await message_repo.update_message(message_id=message_id, wa_status=WAStatus.FAILED)
            await db_session.commit()

        except Exception as exc:
            logger.exception("Erreur inattendue lors de l'envoi du message %s: %s", message_id, exc)
            await message_repo.update_message(message_id=message_id, wa_status=WAStatus.FAILED)
            await db_session.commit()

    finally:
        await db_session.close()

from base64 import b64encode
from datetime import datetime
from logging import getLogger
from uuid import UUID

from celery import shared_task

from app.db.session import AsyncSessionLocal
from app.integrations.whatsapp.card_generator import CardGenerator
from app.repositories.message_repository import MessageRepository
from app.repositories.thread_repository import ThreadRepository
from app.utils.format import formater_date_heure_en_francais
from app.worker.tasks.base.async_loop_manager import task_async_loop_manager
from app.worker.tasks.base.workers_task_names import WorkersTaskNames
from app.integrations.whatsapp.base.evolution_client import (
    EvolutionAPIClient,
)
from app.integrations.whatsapp.exceptions.evolution_client_exceptions import EvolutionError, \
    EvolutionNotInitializedError
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


async def _generate_image(
    thread_name: str,
    text: str,
    time_stamp: datetime,
    mentioned_names: list[str]
) -> str:
    """Coroutine métier — exécutée dans la boucle asyncio persistante du worker."""
    generator = CardGenerator.get_instance()

    length = len(text)
    if length < 100:
        font_size = 50
    elif length < 220:
        font_size = 40
    elif length < 350:
        font_size = 32
    else:
        font_size = 25

    image_bytes = await generator.render(
        template_name="v1_template.html",
        context={
            "thread_name": thread_name,
            "text": text,
            "mentioned_names": mentioned_names,
            "timestamp": formater_date_heure_en_francais(time_stamp),
            "font_size": font_size,
        },
    )

    b64_payload = b64encode(image_bytes).decode("utf-8")
    return b64_payload



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

        # Construire le texte avec mentions formatées (@nom ou @phonenumber)
        # Cela permet l'affichage visuel des mentions dans WhatsApp

        # Envoyer le message
        try:
            image_to_send = await _generate_image(
                thread_name=thread.name,
                text=message.content,
                time_stamp=message.created_at,
                mentioned_names=mention_jids,
            )
            sent = await client.send_image(number=group_jid, caption=message.content, url=image_to_send, mention_jids=mention_jids)

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

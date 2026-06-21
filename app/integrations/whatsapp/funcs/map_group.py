from logging import getLogger

from app.cache.base.cache_wrapper import cache_manager
from app.db.session import AsyncSessionLocal
from app.integrations.whatsapp.base.evolution_client import EvolutionAPIClient
from app.schemas.thread_schemas import CreateThread
from app.schemas.webhook_schemas import MessageEvent
from app.services.thread_service import ThreadService
from json import dumps

from app.utils.whatsapp_utils import generate_random_numeric_password, generate_slug
from app.integrations.whatsapp.messages import success_thread_add
from app.worker.celery_app import celery_app
from app.worker.tasks.base.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


async def map_group_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    redis = cache_manager.get_redis_connection_from_pool()
    db_session = AsyncSessionLocal()
    thread_scv = ThreadService(db_session, redis)
    try:
        random_mdp = generate_random_numeric_password()

        payload = CreateThread(
            name=data.data.groupData.Name,
            slug=generate_slug(data.data.groupData.Name),
            description=None,
            wa_group_jid=data.data.groupData.JID,
            wa_group_name=data.data.groupData.Name,
            password=random_mdp,
        )

        res = await thread_scv.service_create_thread(payload)
        if res.is_error():
            await ctx.send_text(
                number=data.data.groupData.JID, text=res.error.error_message
            )
            return

        msg = success_thread_add(res.data, random_mdp)

        await ctx.send_text(number=data.data.groupData.JID, text=msg)

        # Convertir ParticipantInfo en dicts pour la sérialisation JSON
        # Utiliser les noms de champs attendus par CreateMember schema
        participants_list = [p.model_dump() for p in data.data.groupData.Participants]
        task_data = dumps(participants_list)

        logger.info(
            f"Envoi de la tâche de synchronisation des membres pour le thread {res.data.id} avec {len(participants_list)} participants"
        )
        celery_app.send_task(
            WorkersTaskNames.SYNC_THREAD_MEMBERS_FROM_GROUP,
            kwargs={"group_participants": task_data, "thread_id": str(res.data.id)},
        )
    finally:
        await redis.close()
        await db_session.close()

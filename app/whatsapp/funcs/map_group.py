from app.cache.base.cache_wrapper import cache_manager
from app.db.session import AsyncSessionLocal
from app.integrations.evolution_client import EvolutionAPIClient
from app.schemas.thread_schemas import CreateThread
from app.schemas.webhook_schemas import MessageEvent
from app.services.thread_service import ThreadService
import re
import unicodedata

from app.whatsapp.messages import success_thread_add


def _generate_slug(text: str) -> str:
    text = text.lower()

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    text = re.sub(r"[^a-z0-9]+", "-", text)

    text = text.strip("-")

    return text


async def map_group_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    redis = cache_manager.get_redis_connection_from_pool()
    db_session = AsyncSessionLocal()
    thread_scv = ThreadService(db_session, redis)
    try:
        payload = CreateThread(
            name=data.data.groupData.Name,
            slug=_generate_slug(data.data.groupData.Name),
            description=None,
            wa_group_jid=data.data.groupData.JID,
            wa_group_name=data.data.groupData.Name,
            password=None
        )

        res = await thread_scv.service_create_thread(payload)
        if res.is_error():
            await ctx.send_text(number=data.data.groupData.JID, text=res.error.error_message)
            return
        msg = success_thread_add(res.data)

        await ctx.send_text(number=data.data.groupData.JID, text=msg)
    finally:
        await redis.close()
        await db_session.close()

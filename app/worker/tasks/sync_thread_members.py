from asyncio import gather
from datetime import datetime, UTC
from logging import getLogger
from typing import List
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.cache.base.cache_wrapper import cache_manager
from app.cache.thread_cache import ThreadCache
from app.db.models.member import Member
from app.db.models.enums.enums import WAMemberRole
from app.db.session import AsyncSessionLocal
from app.integrations.whatsapp.base.evolution_client import EvolutionAPIClient
from app.repositories.member_repository import MemberRepository
from app.repositories.thread_member_repository import ThreadMemberRepository
from app.repositories.thread_repository import ThreadRepository
from app.schemas.member_schemas import CreateMember
from app.utils.whatsapp_utils import phone_from_wa_jid
from app.worker.tasks.base.async_loop_manager import task_async_loop_manager
from app.worker.tasks.base.workers_task_names import WorkersTaskNames
from json import loads

logger = getLogger(__name__)

@shared_task(name=WorkersTaskNames.SYNC_THREAD_MEMBERS_FROM_GROUP)
def sync_thread_members_from_group(
    group_participants: str,
    thread_id: str,
    must_send_response: bool
):
    """
    Tâche Celery pour synchroniser les membres des threads à partir des groupes.
    Cette tâche est exécutée de manière asynchrone par le worker Celery.
    Args:
        group_participants: Liste de dictionnaires représentant les participants.
                           Chaque dict doit contenir au moins 'jid'.
                           Peut contenir: jid, name, admin.
        thread_id: L'ID du thread (UUID sous forme de string)
        must_send_response: Parametre optionnel indiquant si on doit faire à l'user un retour apres la tache
    """
    logger.info(f"Démarrage de la synchronisation des membres pour le thread {thread_id}")
    
    thread_id_uuid = UUID(thread_id)
    raw_data = loads(group_participants)
    parsed_participants = [
        CreateMember(
            wa_jid=p.get("JID", ""),
            display_name=None,
            avatar_url=None,
            wa_name=p.get("DisplayName"),
            phone_number=phone_from_wa_jid(p.get("PhoneNumber", "")),
            is_admin=p.get("IsAdmin", False)
        ) for p in raw_data]
    
    logger.debug(f"Nombre de participants à traiter: {len(parsed_participants)}")

    task_async_loop_manager.run_async(_sync_thread_members_from_group_async(
        group_participants=parsed_participants,
        thread_id=thread_id_uuid,
        must_respond=must_send_response
    ))

async def _invalid_caches(thread_id: UUID, wa_jid: str, must_invalid_thread_cache: bool, must_invalid_thread_members_cache: bool):
    redis = cache_manager.get_redis_connection_from_pool()

    tasks = []

    try:
        cache = ThreadCache(redis)
        if must_invalid_thread_members_cache:
            tasks.append(
                cache.invalid_members_by_thread_in_cache(thread_id)
            )
        if must_invalid_thread_cache:
            tasks.extend(
                [
                    cache.invalid_thread_by_wa_group_in_cache(wa_jid),
                    cache.invalid_threads_list_in_cache(),
                    cache.invalid_thread_in_cache(thread_id),
                ]
            )
        if tasks:
            await gather(*tasks, return_exceptions=True)
        logger.info(f"Invalidation des caches terminée pour le thread {thread_id}")
    finally:
        await redis.close()




async def _sync_thread_members_from_group_async(
    group_participants: List[CreateMember],
    thread_id: UUID,
    must_respond: bool
):
    """
    Fonction asynchrone interne pour synchroniser les membres.
    """
    db_session = AsyncSessionLocal()
    must_invalid_thread_members_cache = False
    must_invalid_thread_cache = False
    try:
        logger.debug(f"[Async] Début du traitement pour thread {thread_id}")
        
        participant_wa_jids = [p.wa_jid for p in group_participants if p.wa_jid]
        
        logger.debug(f"[Async] Récupération des {len(participant_wa_jids)} wa_jid en base")
        
        member_repo = MemberRepository(db_session)
        stmt = select(Member).where(Member.wa_jid.in_(participant_wa_jids))
        result = await db_session.execute(stmt)
        existing_members = list(result.scalars().all())
        existing_wa_jids = {m.wa_jid for m in existing_members}
        
        logger.info(f"[Async] {len(existing_members)} membres existants trouvés, {len(participant_wa_jids) - len(existing_members)} nouveaux à créer")
        
        new_members_data = [member for member in group_participants if member.wa_jid not in existing_wa_jids]

        created_members = []
        if new_members_data:
            logger.debug(f"[Async] Création de {len(new_members_data)} nouveaux membres")
            members_result = await member_repo.insert_many_members(new_members_data)
            if not members_result.is_error():
                created_members = members_result.data
                await db_session.commit()
                logger.info(f"[Async] {len(created_members)} nouveaux membres créés avec succès")

        
        thread_member_repo = ThreadMemberRepository(db_session)
        
        all_members_by_wa_jid = {m.wa_jid: m for m in existing_members}
        all_members_by_wa_jid.update({m.wa_jid: m for m in created_members})
        
        thread_members_data = []
        for participant in group_participants:
            wa_jid = participant.wa_jid
            if wa_jid and wa_jid in all_members_by_wa_jid:
                member_id = all_members_by_wa_jid[wa_jid].id

                if participant.is_admin:
                    wa_role = WAMemberRole.ADMIN
                else:
                    wa_role = WAMemberRole.MEMBER
                
                thread_members_data.append({
                    "thread_id": thread_id,
                    "member_id": member_id,
                    "wa_role": wa_role,
                    "is_active": True
                })
        
        if thread_members_data:
            logger.debug(f"[Async] Création de {len(thread_members_data)} associations thread/membre")
            thread_members_result = await thread_member_repo.bulk_insert_thread_members(thread_members_data)
            if thread_members_result.is_error():
                # Rollback si erreur
                logger.error(f"[Async] Erreur lors de la création des associations: {thread_members_result.error}")
                await db_session.rollback()
            else:
                await db_session.commit()
                must_invalid_thread_members_cache = True
                logger.info(f"[Async] {len(thread_members_data)} associations thread/membre créées avec succès")

        thread_repo = ThreadRepository(db_session)

        update_res = await thread_repo.update_last_wa_sync_at(thread_id, datetime.now(UTC))

        if update_res.is_error():
            logger.error(f"[Async] Erreur lors de la mise à jour du last_wa_sync_at pour le thread {thread_id}: {update_res.error}")
            await db_session.rollback()
        else:
            must_invalid_thread_cache = True
            if must_respond:
                evo_client = EvolutionAPIClient.get_instance()

                await evo_client.send_text(
                    number=update_res.data.wa_group_jid,
                    text=f"La synchronisation des membres du thread {update_res.data.wa_group_name} est terminée avec succès ✅"
                )

        await db_session.commit()
        await _invalid_caches(thread_id, update_res.data.wa_group_jid, must_invalid_thread_cache, must_invalid_thread_members_cache)
        logger.info(f"[Async] Synchronisation terminée avec succès pour le thread {thread_id}")
        
    except Exception as e:
        logger.exception(f"[Async] Erreur lors de la synchronisation des membres pour thread {thread_id}: {str(e)}", exc_info=True)
        await db_session.rollback()
        raise e
    finally:
        await db_session.close()
        logger.debug(f"[Async] Session DB fermée pour thread {thread_id}")

from logging import getLogger
from typing import List
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.db.models.member import Member
from app.db.models.enums.enums import WAMemberRole
from app.db.session import AsyncSessionLocal
from app.repositories.member_repository import MemberRepository
from app.repositories.thread_member_repository import ThreadMemberRepository
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
):
    """
    Tâche Celery pour synchroniser les membres des threads à partir des groupes.
    Cette tâche est exécutée de manière asynchrone par le worker Celery.
    Args:
        group_participants: Liste de dictionnaires représentant les participants.
                           Chaque dict doit contenir au moins 'jid'.
                           Peut contenir: jid, name, admin.
        thread_id: L'ID du thread (UUID sous forme de string)
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
    ))


async def _sync_thread_members_from_group_async(
    group_participants: List[CreateMember],
    thread_id: UUID,
):
    """
    Fonction asynchrone interne pour synchroniser les membres.
    """
    db_session = AsyncSessionLocal()
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
        
        # Étape 3: Identifier les nouveaux membres à créer
        new_members_data = [member for member in group_participants if member.wa_jid not in existing_wa_jids]

        # Étape 4: Créer les nouveaux membres en bulk
        created_members = []
        if new_members_data:
            logger.debug(f"[Async] Création de {len(new_members_data)} nouveaux membres")
            members_result = await member_repo.insert_many_members(new_members_data)
            if not members_result.is_error():
                created_members = members_result.data
                await db_session.commit()
                logger.info(f"[Async] {len(created_members)} nouveaux membres créés avec succès")
        
        # Étape 5: Créer les associations thread_member pour TOUS les participants
        # (les existants + les nouveaux)
        thread_member_repo = ThreadMemberRepository(db_session)
        
        # Construire la liste des associations
        all_members_by_wa_jid = {m.wa_jid: m for m in existing_members}
        all_members_by_wa_jid.update({m.wa_jid: m for m in created_members})
        
        thread_members_data = []
        for participant in group_participants:
            wa_jid = participant.wa_jid
            if wa_jid and wa_jid in all_members_by_wa_jid:
                member_id = all_members_by_wa_jid[wa_jid].id
                # Déterminer le rôle
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
        
        # Étape 6: Insérer toutes les associations thread_member
        if thread_members_data:
            logger.debug(f"[Async] Création de {len(thread_members_data)} associations thread/membre")
            thread_members_result = await thread_member_repo.bulk_insert_thread_members(thread_members_data)
            if thread_members_result.is_error():
                # Rollback si erreur
                logger.error(f"[Async] Erreur lors de la création des associations: {thread_members_result.error}")
                await db_session.rollback()
            else:
                await db_session.commit()
                logger.info(f"[Async] {len(thread_members_data)} associations thread/membre créées avec succès")
        
        await db_session.commit()
        logger.info(f"[Async] Synchronisation terminée avec succès pour le thread {thread_id}")
        
    except Exception as e:
        logger.error(f"[Async] Erreur lors de la synchronisation des membres pour thread {thread_id}: {str(e)}", exc_info=True)
        await db_session.rollback()
        raise e
    finally:
        await db_session.close()
        logger.debug(f"[Async] Session DB fermée pour thread {thread_id}")

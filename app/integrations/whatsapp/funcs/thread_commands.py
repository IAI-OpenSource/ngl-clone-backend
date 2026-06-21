from asyncio import gather
from logging import getLogger
from typing import Optional
from uuid import UUID

from app.cache.base.cache_wrapper import cache_manager
from app.cache.thread_cache import ThreadCache
from app.db.session import AsyncSessionLocal
from app.integrations.whatsapp.base.evolution_client import EvolutionAPIClient
from app.repositories.thread_repository import ThreadRepository
from app.schemas.thread_schemas import ReadThread
from app.schemas.webhook_schemas import MessageEvent
from app.services.thread_service import ThreadService
from app.integrations.whatsapp.messages import (
    format_edit_confirmation,
    format_edit_error,
    format_lock_confirmation,
    format_unlock_confirmation,
    format_ngl_status,
    get_help_message,
    get_docs_message,
)

logger = getLogger(__name__)


async def _invalid_thread_cache(thread_cache: ThreadCache, thread_id: UUID, wa_group_jid: str):
    """
    Invalide les caches liés à un thread spécifique.

    Args:
        thread_id: ID du thread à invalider
        wa_group_jid: JID du groupe pour invalider le cache lié au groupe
    """
    try:
        await gather(
            thread_cache.invalid_thread_in_cache(thread_id),
            thread_cache.invalid_thread_by_wa_group_in_cache(wa_group_jid),
            thread_cache.invalid_threads_list_in_cache(),
            thread_cache.invalidate_raw_thread_in_cache(thread_id),
            return_exceptions=True
        )
    except Exception as e:
        logger.exception(f"Erreur lors de l'invalidation du cache pour le thread {thread_id}: {e}")

async def _get_thread_by_group_jid(wa_group_jid: str) -> Optional[ReadThread]:
    """
    Récupère un thread à partir du JID du groupe WhatsApp.
    Utilise le service layer qui gère le cache automatiquement.
    
    Args:
        wa_group_jid: Le JID du groupe WhatsApp
        
    Returns:
        ReadThread si trouvé, None sinon
    """
    db_session = AsyncSessionLocal()
    redis = cache_manager.get_redis_connection_from_pool()
    try:
        thread_service = ThreadService(db_session, redis)
        result = await thread_service.service_find_thread_by_wa_group_jid(wa_group_jid)
        
        if result.is_success():
            return result.data
        logger.error(f"Thread non trouvé pour wa_group_jid: {wa_group_jid}")
        return None
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération du thread: {e}")
        return None
    finally:
        await redis.close()
        await db_session.close()


async def _update_thread_lock_status(
    thread: ReadThread,
    is_locked: bool,
    wa_group_jid: str,
    ctx: EvolutionAPIClient
) -> bool:
    """
    Met à jour le statut de verrouillage d'un thread.
    
    Args:
        thread: Le thread à mettre à jour
        is_locked: True pour verrouiller, False pour déverrouiller
        wa_group_jid: JID du groupe pour envoyer la réponse
        ctx: Client EvolutionAPI pour envoyer des messages
        
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    db_session = AsyncSessionLocal()
    redis = cache_manager.get_redis_connection_from_pool()
    try:
        thread_repo = ThreadRepository(db_session)
        result = await thread_repo.update_thread(
            thread_id=thread.id,
            is_currently_locked=is_locked
        )
        
        if result.is_success():
            # Invalider le cache
            thread_cache = ThreadCache(redis)
            await _invalid_thread_cache(thread_cache, thread.id, wa_group_jid)
            return True
        else:
            error_msg = result.error.error_message
            await ctx.send_text(
                number=wa_group_jid,
                text=f"❌ Erreur: {error_msg}"
            )
            return False
    except Exception as e:
        logger.exception(f"Erreur lors de la mise à jour du thread: {e}")
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ Une erreur interne est survenue."
        )
        return False
    finally:
        await redis.close()
        await db_session.close()


async def _update_thread_field(
    thread: ReadThread,
    field: str,
    new_value: str,
    wa_group_jid: str,
    ctx: EvolutionAPIClient
) -> bool:
    """
    Met à jour un champ d'un thread.
    
    Args:
        thread: Le thread à mettre à jour
        field: Le nom du champ (name, description, slug)
        new_value: La nouvelle valeur
        wa_group_jid: JID du groupe pour envoyer la réponse
        ctx: Client EvolutionAPI pour envoyer des messages
        
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    # Validation
    if field == "name" and (len(new_value) < 1 or len(new_value) > 100):
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ Le nom doit contenir entre 1 et 100 caractères."
        )
        return False
    
    if field == "slug" and (len(new_value) < 1 or len(new_value) > 50):
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ Le slug doit contenir entre 1 et 50 caractères."
        )
        return False
    
    if field == "description" and len(new_value) > 500:
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ La description ne peut pas dépasser 500 caractères."
        )
        return False
    
    db_session = AsyncSessionLocal()
    redis = cache_manager.get_redis_connection_from_pool()
    try:
        thread_repo = ThreadRepository(db_session)
        # Appel direct avec les bons types pour chaque champ
        if field == "name":
            result = await thread_repo.update_thread(
                thread_id=thread.id,
                name=new_value
            )
        elif field == "description":
            result = await thread_repo.update_thread(
                thread_id=thread.id,
                description=new_value
            )
        elif field == "slug":
            result = await thread_repo.update_thread(
                thread_id=thread.id,
                slug=new_value
            )
        else:
            await ctx.send_text(
                number=wa_group_jid,
                text="❌ Champ inconnu."
            )
            return False
        
        if result.is_success():
            # Invalider le cache
            thread_cache = ThreadCache(redis)
            await _invalid_thread_cache(thread_cache, thread.id, wa_group_jid)
            
            old_value = getattr(thread, field, "N/A")
            msg = format_edit_confirmation(field, str(old_value), new_value)
            await ctx.send_text(number=wa_group_jid, text=msg)
            return True
        else:
            error_msg = result.error.error_message if result.error else "Erreur inconnue"
            msg = format_edit_error(error_msg)
            await ctx.send_text(number=wa_group_jid, text=msg)
            return False
    except Exception as e:
        logger.exception(f"Erreur lors de la mise à jour du champ {field}: {e}")
        msg = format_edit_error("Une erreur interne est survenue.")
        await ctx.send_text(number=wa_group_jid, text=msg)
        return False
    finally:
        await redis.close()
        await db_session.close()


# ============================================================================
# Handlers des commandes
# ============================================================================

async def ngl_status_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler pour la commande /ngl.
    Affiche le statut du thread associé au groupe.
    """
    wa_group_jid = data.data.groupData.JID
    
    logger.info(f"Exécution de /ngl pour le groupe {wa_group_jid}")
    
    thread = await _get_thread_by_group_jid(wa_group_jid)
    
    if thread is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="⚠️ Ce groupe n'est pas connecté à un thread. Utilisez * /map_group * pour l'associer."
        )
        return
    
    msg = format_ngl_status(thread)
    await ctx.send_text(number=wa_group_jid, text=msg)


async def lock_thread_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler pour la commande /lock.
    Verrouille le thread pour bloquer les nouveaux messages.
    """
    wa_group_jid = data.data.groupData.JID
    
    logger.info(f"Exécution de /lock pour le groupe {wa_group_jid}")
    
    thread = await _get_thread_by_group_jid(wa_group_jid)
    
    if thread is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="⚠️ Ce groupe n'est pas connecté à un thread."
        )
        return
    
    if thread.is_currently_locked:
        await ctx.send_text(
            number=wa_group_jid,
            text="🔒 Ce thread est déjà verrouillé."
        )
        return
    
    success = await _update_thread_lock_status(thread, True, wa_group_jid, ctx)
    if success:
        msg = format_lock_confirmation(thread.name)
        await ctx.send_text(number=wa_group_jid, text=msg)


async def unlock_thread_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler pour la commande /unlock.
    Déverrouille le thread pour autoriser les nouveaux messages.
    """
    wa_group_jid = data.data.groupData.JID
    
    logger.info(f"Exécution de /unlock pour le groupe {wa_group_jid}")
    
    thread = await _get_thread_by_group_jid(wa_group_jid)
    
    if thread is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="⚠️ Ce groupe n'est pas connecté à un thread."
        )
        return
    
    if not thread.is_currently_locked:
        await ctx.send_text(
            number=wa_group_jid,
            text="🔓 Ce thread est déjà déverrouillé."
        )
        return
    
    success = await _update_thread_lock_status(thread, False, wa_group_jid, ctx)
    if success:
        msg = format_unlock_confirmation(thread.name)
        await ctx.send_text(number=wa_group_jid, text=msg)


async def edit_thread_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler générique pour les commandes /edit-name, /edit-desc, /edit-slug.
    Parse la commande et met à jour le champ correspondant.
    """
    wa_group_jid = data.data.groupData.JID
    msg_text = data.data.Message.conversation
    if msg_text is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ Commande invalide."
        )
        return
    parts = msg_text.strip().split(maxsplit=1)
    command = parts[0]
    
    logger.info(f"Exécution de {command} pour le groupe {wa_group_jid}")
    
    # Mapping des commandes aux champs
    field_mapping = {
        "/edit-name": "name",
        "/edit-desc": "description",
        "/edit-slug": "slug",
    }
    
    field = field_mapping.get(command)
    if field is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="❌ Commande d'édition invalide. Utilisez * /help * pour voir les commandes."
        )
        return
    
    if len(parts) < 2:
        field_names = {
            "name": "nom",
            "description": "description",
            "slug": "slug",
        }
        field_name = field_names.get(field, field)
        await ctx.send_text(
            number=wa_group_jid,
            text=f"❌ Veuillez fournir une valeur pour {field_name}. Ex: {command} Nouveau {field_name}"
        )
        return
    
    new_value = parts[1].strip()
    thread = await _get_thread_by_group_jid(wa_group_jid)
    
    if thread is None:
        await ctx.send_text(
            number=wa_group_jid,
            text="⚠️ Ce groupe n'est pas connecté à un thread."
        )
        return
    
    await _update_thread_field(thread, field, new_value, wa_group_jid, ctx)


async def help_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler pour la commande /help.
    Affiche la liste des commandes disponibles.
    """
    wa_group_jid = data.data.groupData.JID
    
    logger.info(f"Exécution de /help pour le groupe {wa_group_jid}")
    
    msg = get_help_message()
    await ctx.send_text(number=wa_group_jid, text=msg)


async def docs_handler(ctx: EvolutionAPIClient, data: MessageEvent):
    """
    Handler pour la commande /docs.
    Affiche la documentation du projet.
    """
    wa_group_jid = data.data.groupData.JID
    
    logger.info(f"Exécution de /docs pour le groupe {wa_group_jid}")
    
    msg = get_docs_message()
    await ctx.send_text(number=wa_group_jid, text=msg)

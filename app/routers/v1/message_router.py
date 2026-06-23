from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, Query
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.globals.api_base_response import ApiBaseResponse
from app.schemas.message_schemas import (
    CreateMessage,
    ListMessagesInfos,
    MessageInfos,
    ReadMessage,
    PaginatedMessagesInfos,
    PaginatedMessagesResponse,
)
from app.services.message_service import MessageService
from app.schemas.thread_schemas import ThreadAuthPayload
from app.auth.dependencies import get_connected_thread
from app.schemas.globals.api_utils_schemas import ApiUtilsSchemas
from app.globals.businnes_error import AppError

router = APIRouter(prefix="/messages", tags=[ApiTags.MESSAGES])


def get_message_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> MessageService:
    return MessageService(db, cache)


@router.post(
    "/", response_model=MessageInfos, summary="Ajouter un message au thread connecté", status_code=201
)
async def create_message(
    message_data: CreateMessage,
    response: Response,
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
    message_service: Annotated[MessageService, Depends(get_message_service)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour ajouter un message à un thread auquel on est connecté. Le thread est déterminé par le token d'authentification fourni dans l'en-tête de la requête.
    **La route retourne un 429 en cas de RateLimiting**
    """

    service_result = await message_service.service_create_message(
        message_data=message_data, user_payload=thread
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get(
    "/thread/",
    response_model=ListMessagesInfos,
    responses=ApiUtilsSchemas.AUTH_REQUIRED_RESPONSES,
    summary="Lister TOUS les messages du thread auquel on est connecté (déprécié)",
    deprecated=True,
)
async def get_thread_messages(
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
) -> ApiBaseResponse[list[ReadMessage], AppError]:
    """Route pour récupérer TOUS les messages du thread auquel on est actuellement connecté.
    
    **Cette route est dépréciée.** Utilisez plutôt GET /messages/thread/paginated/ pour une pagination efficace.
    """

    service_result = await message_service.service_get_messages_by_thread_id(
        thread_id=UUID(thread.thread_id)
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get(
    "/thread/paginated/",
    response_model=PaginatedMessagesInfos,
    responses=ApiUtilsSchemas.AUTH_REQUIRED_RESPONSES,
    summary="Lister les messages du thread avec pagination par curseur",
)
async def get_thread_messages_paginated(
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
    limit: Annotated[int, Query(ge=1, le=100, description="Nombre de messages par page (1-100, par défaut 20)")] = 20,
    cursor: Annotated[Optional[str], Query(description="Curseur de pagination (base64). None pour la première page")] = None,
) -> ApiBaseResponse[PaginatedMessagesResponse, AppError]:
    """Route pour récupérer les messages du thread actuel avec pagination par curseur.
    
    Cette route implémente une pagination par curseur (cursor-based pagination) optimisée pour :
    - Une meilleure performance avec de grands volumes de messages
    - Une navigation fluide entre les pages
    - Un cache efficace des résultats paginés
    - Une expérience utilisateur optimale
    
    **Paramètres :**
    - `limit` : Nombre de messages par page (1-100, par défaut 20)
    - `cursor` : Curseur pour la page suivante ou précédente (encodé en base64). 
                 Si None, récupère la première page (messages les plus récents)
    
    **Réponse :**
    - `messages` : Liste des messages de la page actuelle
    - `has_next_page` : True s'il y a une page suivante
    - `next_cursor` : Curseur pour la page suivante (à utiliser avec le même limit)
    - `has_previous_page` : True s'il y a une page précédente
    - `previous_cursor` : Curseur pour la page précédente
    
    **Exemple d'utilisation :**
    1. Première requête : GET /messages/thread/paginated/?limit=20
       -> Retourne les 20 messages les plus récents avec next_cursor si applicable
    
    2. Page suivante : GET /messages/thread/paginated/?limit=20&cursor=<next_cursor>
       -> Retourne les 20 messages suivants (plus anciens)
    
    3. Page précédente : GET /messages/thread/paginated/?limit=20&cursor=<previous_cursor>
       -> Retourne les 20 messages précédents (plus récents)
    """

    service_result = await message_service.service_get_messages_by_thread_id_paginated(
        thread_id=UUID(thread.thread_id),
        limit=limit,
        cursor=cursor,
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get(
    "/{message_id}",
    response_model=MessageInfos,
    summary="Récupérer un message par son ID",
    responses=ApiUtilsSchemas.AUTH_REQUIRED_RESPONSES,
)
async def get_message_by_id(
    message_id: Annotated[UUID, Path(..., description="ID du message à récupérer")],
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour récupérer un message par son ID."""

    service_result = await message_service.service_find_message_by_id(
        message_id=message_id, connected_thread=thread
    )

    return service_result.to_HTTP_api_base_response(reponse=response)

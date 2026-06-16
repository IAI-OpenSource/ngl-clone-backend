from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.businnes_error import AppError
from app.schemas.globals.api_base_response import ApiBaseResponse
from app.schemas.message_schemas import (
    CreateMessage,
    ListMessagesInfos,
    MessageInfos,
    ReadMessage,
)
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=[ApiTags.MESSAGES])


def get_message_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> MessageService:
    return MessageService(db, cache)


@router.post("/", response_model=MessageInfos)
async def create_message(
    message_data: CreateMessage,
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour ajouter un message à un thread."""

    service_result = await message_service.service_create_message(
        message_data=message_data
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/thread/{thread_id}", response_model=ListMessagesInfos)
async def get_messages_by_thread(
    thread_id: Annotated[UUID, Path(..., description="ID du thread dont les messages doivent être récupérés")],
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    is_hidden: Annotated[
        Optional[bool],
        Query(description="Filtrer par statut de masquage du message"),
    ] = None,
) -> ApiBaseResponse[list[ReadMessage], AppError]:
    """Route pour récupérer les messages d'un thread."""

    service_result = await message_service.service_get_messages_by_thread_id(
        thread_id=thread_id,
        is_hidden=is_hidden,
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/{message_id}", response_model=MessageInfos)
async def get_message_by_id(
    message_id: Annotated[UUID, Path(..., description="ID du message à récupérer")],
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour récupérer un message par son ID."""

    service_result = await message_service.service_find_message_by_id(
        message_id=message_id
    )

    return service_result.to_HTTP_api_base_response(reponse=response)

"""
Repository pour la table messages.
Gère les opérations CRUD sur les messages.
"""

from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.message import Message
from app.db.models.enums.enums import WAStatus
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class MessageRepository:
    """Repository pour la gestion des messages."""

    db: AsyncSession

    async def insert_message(
        self,
        thread_id: UUID,
        content: str,
        wa_message_id: Optional[str] = None,
        wa_status: WAStatus = WAStatus.PENDING,
        wa_forwarded_at: Optional[datetime] = None,
        is_hidden: bool = False,
        hidden_reason: Optional[str] = None,
        hidden_at: Optional[datetime] = None,
    ) -> DefaultAppCrudResult[Message]:
        """Fonction pour insérer un message en base de données."""
        try:
            message = Message(
                thread_id=thread_id,
                content=content,
                wa_message_id=wa_message_id,
                hidden_reason=hidden_reason,
            )
            # Les champs avec init=False doivent être assignés après la création
            message.wa_status = wa_status
            message.wa_forwarded_at = wa_forwarded_at
            message.is_hidden = is_hidden
            message.hidden_at = hidden_at

            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)

            logger.info(f"Message {message.id} ajouté avec succès !")
            return CrudResult.crud_success(
                data=message, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def get_message_by_id(self, message_id: UUID) -> DefaultAppCrudResult[Message]:
        """Fonction pour récupérer un message à partir de son ID."""
        try:
            stmt = select(Message).where(Message.id == message_id)
            result = await self.db.execute(stmt)
            message = result.scalar_one_or_none()

            if message is None:
                logger.info(f"Message avec ID {message_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Message inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=message)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_messages_by_thread_id(
        self,
        thread_id: UUID,
        is_hidden: Optional[bool] = None,
    ) -> DefaultAppCrudResult[list[Message]]:
        """Fonction pour récupérer tous les messages d'un thread."""
        try:
            stmt = select(Message).where(Message.thread_id == thread_id)

            if is_hidden:
                stmt = stmt.where(Message.is_hidden == True)
            elif is_hidden is False:
                stmt = stmt.where(Message.is_hidden == False)

            result = await self.db.execute(stmt)
            messages = list(result.scalars().all())

            return CrudResult.crud_success(data=messages)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def get_messages_by_wa_status(
        self,
        wa_status: WAStatus,
    ) -> DefaultAppCrudResult[list[Message]]:
        """Fonction pour récupérer tous les messages par statut WhatsApp."""
        try:
            stmt = select(Message).where(Message.wa_status == wa_status)
            result = await self.db.execute(stmt)
            messages = list(result.scalars().all())

            return CrudResult.crud_success(data=messages)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def update_message(
        self,
        message_id: UUID,
        content: Optional[str] = None,
        wa_message_id: Optional[str] = None,
        wa_status: Optional[WAStatus] = None,
        wa_forwarded_at: Optional[datetime] = None,
        is_hidden: Optional[bool] = None,
        hidden_reason: Optional[str] = None,
        hidden_at: Optional[datetime] = None,
    ) -> DefaultAppCrudResult[Message]:
        """Fonction pour mettre à jour un message dans la base de données."""
        try:
            old_message = await self.get_message_by_id(message_id=message_id)

            if old_message.is_error():
                return old_message

            if content is not None:
                old_message.data.content = content
            if wa_message_id is not None:
                old_message.data.wa_message_id = wa_message_id
            if wa_status is not None:
                old_message.data.wa_status = wa_status
            if wa_forwarded_at is not None:
                old_message.data.wa_forwarded_at = wa_forwarded_at
            if is_hidden is not None:
                old_message.data.is_hidden = is_hidden
            if hidden_reason is not None:
                old_message.data.hidden_reason = hidden_reason
            if hidden_at is not None:
                old_message.data.hidden_at = hidden_at

            await self.db.commit()

            logger.info(f"Message {message_id} mis à jour avec succès")
            return CrudResult.crud_success(data=old_message.data)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def delete_message(self, message_id: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer un message de la base de données."""
        try:
            message = await self.get_message_by_id(message_id)

            if message.is_error():
                return CrudResult.crud_failure(
                    message.error, status_code=message.status_code
                )

            await self.db.delete(message.data)
            await self.db.commit()

            logger.info(f"Message {message_id} supprimé avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

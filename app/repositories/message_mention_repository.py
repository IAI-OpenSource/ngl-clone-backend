"""
Repository pour la table message_mentions.
Gère les opérations CRUD sur les mentions de membres dans les messages.
"""

from dataclasses import dataclass
from logging import getLogger
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.message_mention import MessageMention
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils
from app.globals.businnes_error import AppError, AppErrorType

logger = getLogger(__name__)


@dataclass
class MessageMentionRepository:
    """Repository pour la gestion des mentions de membres dans les messages."""

    db: AsyncSession

    async def insert_message_mention(
        self,
        message_id: UUID,
        member_id: UUID,
    ) -> DefaultAppCrudResult[MessageMention]:
        """Fonction pour insérer une mention en base de données."""
        try:
            message_mention = MessageMention(
                message_id=message_id,
                member_id=member_id,
            )
            self.db.add(message_mention)
            await self.db.commit()
            await self.db.refresh(message_mention)

            logger.info(f"Mention message {message_id} - membre {member_id} ajoutée avec succès !")
            return CrudResult.crud_success(
                data=message_mention, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, MessageMention
            )

    async def get_message_mention_by_ids(
        self, message_id: UUID, member_id: UUID
    ) -> DefaultAppCrudResult[MessageMention]:
        """Fonction pour récupérer une mention à partir des IDs."""
        try:
            stmt = select(MessageMention).where(
                MessageMention.message_id == message_id,
                MessageMention.member_id == member_id,
            )
            result = await self.db.execute(stmt)
            message_mention = result.scalar_one_or_none()

            if message_mention is None:
                logger.info(f"Mention message {message_id} - membre {member_id} non trouvée")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Mention inexistante",
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=message_mention)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_message_mentions_by_message_id(
        self, message_id: UUID
    ) -> DefaultAppCrudResult[list[MessageMention]]:
        """Fonction pour récupérer toutes les mentions d'un message."""
        try:
            stmt = select(MessageMention).where(MessageMention.message_id == message_id)
            result = await self.db.execute(stmt)
            message_mentions = list(result.scalars().all())

            return CrudResult.crud_success(data=message_mentions)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, MessageMention
            )

    async def get_message_mentions_by_member_id(
        self, member_id: UUID
    ) -> DefaultAppCrudResult[list[MessageMention]]:
        """Fonction pour récupérer toutes les mentions d'un membre."""
        try:
            stmt = select(MessageMention).where(MessageMention.member_id == member_id)
            result = await self.db.execute(stmt)
            message_mentions = list(result.scalars().all())

            return CrudResult.crud_success(data=message_mentions)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, MessageMention
            )

    async def get_message_mentions_by_thread_id(
        self, thread_id: UUID
    ) -> DefaultAppCrudResult[list[MessageMention]]:
        """Fonction pour récupérer toutes les mentions d'un thread (via les messages)."""
        try:
            # Requête avec jointure pour récupérer les mentions des messages d'un thread
            from sqlalchemy import join
            from app.db.models.message import Message
            
            stmt = select(MessageMention).join(
                Message, Message.id == MessageMention.message_id
            ).where(Message.thread_id == thread_id)
            
            result = await self.db.execute(stmt)
            message_mentions = list(result.scalars().all())

            return CrudResult.crud_success(data=message_mentions)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, MessageMention
            )

    async def delete_message_mention(
        self, message_id: UUID, member_id: UUID
    ) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer une mention de la base de données."""
        try:
            message_mention = await self.get_message_mention_by_ids(
                message_id=message_id, member_id=member_id
            )

            if message_mention.is_error():
                return CrudResult.crud_failure(
                    message_mention.error, status_code=message_mention.status_code
                )

            await self.db.delete(message_mention.data)
            await self.db.commit()

            logger.info(f"Mention message {message_id} - membre {member_id} supprimée avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, MessageMention
            )

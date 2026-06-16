"""
Repository pour la table thread_members.
Gère les opérations CRUD sur l'association entre threads et membres.
"""

from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.thread_member import ThreadMember
from app.db.models.enums.enums import WAMemberRole
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils
from app.globals.businnes_error import AppError, AppErrorType

logger = getLogger(__name__)


@dataclass
class ThreadMemberRepository:
    """Repository pour la gestion des associations thread/membre."""

    db: AsyncSession

    async def insert_thread_member(
        self,
        thread_id: UUID,
        member_id: UUID,
        wa_role: WAMemberRole = WAMemberRole.MEMBER,
        is_active: bool = True,
    ) -> DefaultAppCrudResult[ThreadMember]:
        """Fonction pour insérer une association thread/membre en base de données."""
        try:
            thread_member = ThreadMember(
                thread_id=thread_id,
                member_id=member_id,
                wa_role=wa_role,
            )
            # is_active a init=False, donc on l'assigne après
            thread_member.is_active = is_active

            self.db.add(thread_member)
            await self.db.commit()
            await self.db.refresh(thread_member)

            logger.info(f"Association thread {thread_id} - membre {member_id} ajoutée avec succès !")
            return CrudResult.crud_success(
                data=thread_member, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

    async def get_thread_member_by_ids(
        self, thread_id: UUID, member_id: UUID
    ) -> DefaultAppCrudResult[ThreadMember]:
        """Fonction pour récupérer une association thread/membre à partir des IDs."""
        try:
            stmt = select(ThreadMember).where(
                ThreadMember.thread_id == thread_id,
                ThreadMember.member_id == member_id,
            )
            result = await self.db.execute(stmt)
            thread_member = result.scalar_one_or_none()

            if thread_member is None:
                logger.info(f"Association thread {thread_id} - membre {member_id} non trouvée")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Association thread/membre inexistante",
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=thread_member)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_thread_members_by_thread_id(
        self, thread_id: UUID
    ) -> DefaultAppCrudResult[list[ThreadMember]]:
        """Fonction pour récupérer toutes les associations d'un thread."""
        try:
            stmt = select(ThreadMember).where(ThreadMember.thread_id == thread_id)
            result = await self.db.execute(stmt)
            thread_members = list(result.scalars().all())

            return CrudResult.crud_success(data=thread_members)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

    async def get_thread_members_by_member_id(
        self, member_id: UUID
    ) -> DefaultAppCrudResult[list[ThreadMember]]:
        """Fonction pour récupérer toutes les associations d'un membre."""
        try:
            stmt = select(ThreadMember).where(ThreadMember.member_id == member_id)
            result = await self.db.execute(stmt)
            thread_members = list(result.scalars().all())

            return CrudResult.crud_success(data=thread_members)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

    async def get_active_thread_members_by_thread_id(
        self, thread_id: UUID
    ) -> DefaultAppCrudResult[list[ThreadMember]]:
        """Fonction pour récupérer les membres actifs d'un thread."""
        try:
            stmt = select(ThreadMember).where(
                ThreadMember.thread_id == thread_id,
                ThreadMember.is_active == True,
                ThreadMember.left_at == None,
            )
            result = await self.db.execute(stmt)
            thread_members = list(result.scalars().all())

            return CrudResult.crud_success(data=thread_members)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

    async def update_thread_member(
        self,
        thread_id: UUID,
        member_id: UUID,
        wa_role: Optional[WAMemberRole] = None,
        is_active: Optional[bool] = None,
        left_at: Optional[datetime] = None,
    ) -> DefaultAppCrudResult[ThreadMember]:
        """Fonction pour mettre à jour une association thread/membre dans la base de données."""
        try:
            old_thread_member = await self.get_thread_member_by_ids(
                thread_id=thread_id, member_id=member_id
            )

            if old_thread_member.is_error():
                return old_thread_member

            if wa_role is not None:
                old_thread_member.data.wa_role = wa_role
            if is_active is not None:
                old_thread_member.data.is_active = is_active
            if left_at is not None:
                old_thread_member.data.left_at = left_at

            await self.db.commit()

            logger.info(f"Association thread {thread_id} - membre {member_id} mise à jour avec succès")
            return CrudResult.crud_success(data=old_thread_member.data)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

    async def delete_thread_member(
        self, thread_id: UUID, member_id: UUID
    ) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer une association thread/membre de la base de données."""
        try:
            thread_member = await self.get_thread_member_by_ids(
                thread_id=thread_id, member_id=member_id
            )

            if thread_member.is_error():
                return CrudResult.crud_failure(
                    thread_member.error, status_code=thread_member.status_code
                )

            await self.db.delete(thread_member.data)
            await self.db.commit()

            logger.info(f"Association thread {thread_id} - membre {member_id} supprimée avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, ThreadMember
            )

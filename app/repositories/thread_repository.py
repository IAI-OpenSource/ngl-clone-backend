"""
Repository pour la table threads.
Gère les opérations CRUD sur les groupes de discussion (threads).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.thread import Thread
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils
from app.schemas.thread_schemas import CreateThread
from app.utils.security_utils import hasher_password
logger = getLogger(__name__)


@dataclass
class ThreadRepository:
    """Repository pour la gestion des threads (groupes de discussion)."""

    db: AsyncSession

    async def insert_thread(
        self, thread_data: CreateThread
    ) -> DefaultAppCrudResult[Thread]:
        """Fonction pour insérer un thread en base de données."""
        try:
            thread = Thread(
                name=thread_data.name,
                slug=thread_data.slug,
                description=thread_data.description,
                wa_group_jid=thread_data.wa_group_jid,
                wa_group_name=thread_data.wa_group_name,
                # is_currently_locked sera False par défaut; laissé explicite si besoin

            )
            if thread_data.password is not None:
                thread.password_hash = hasher_password(thread_data.password)

            self.db.add(thread)
            await self.db.commit()
            await self.db.refresh(thread)

            logger.info(f"Thread {thread_data.slug} ajouté avec succès !")
            return CrudResult.crud_success(
                data=thread, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Thread
            )

    async def get_thread_by_id(self, thread_id: UUID) -> DefaultAppCrudResult[Thread]:
        """Fonction pour récupérer un thread à partir de son ID."""
        try:
            stmt = select(Thread).where(Thread.id == thread_id)
            result = await self.db.execute(stmt)
            thread = result.scalar_one_or_none()

            if thread is None:
                logger.info(f"Thread avec ID {thread_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Thread inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=thread)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_thread_by_slug(self, slug: str) -> DefaultAppCrudResult[Thread]:
        """Fonction pour récupérer un thread à partir de son slug."""
        try:
            stmt = select(Thread).where(Thread.slug == slug)
            result = await self.db.execute(stmt)
            thread = result.scalar_one_or_none()

            if thread is None:
                logger.info(f"Thread avec slug {slug} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Thread inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=thread)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_thread_by_wa_group_jid(
        self, wa_group_jid: str
    ) -> DefaultAppCrudResult[Thread]:
        """Fonction pour récupérer un thread à partir de son identifiant de groupe WhatsApp."""
        try:
            stmt = select(Thread).where(Thread.wa_group_jid == wa_group_jid)
            result = await self.db.execute(stmt)
            thread = result.scalar_one_or_none()

            if thread is None:
                logger.info(f"Thread avec wa_group_jid {wa_group_jid} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Thread inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=thread)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_all_threads(
        self,
        is_active: Optional[bool] = None,
    ) -> DefaultAppCrudResult[list[Thread]]:
        """Fonction pour récupérer tous les threads de la base de données."""
        try:
            stmt = select(Thread)
            if is_active:
                stmt = stmt.where(Thread.is_active == True)
            elif is_active is not None:
                stmt = stmt.where(Thread.is_active == False)

            result = await self.db.execute(stmt)
            threads = list(result.scalars().all())

            return CrudResult.crud_success(data=threads)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Thread
            )

    async def update_thread(
        self,
        thread_id: UUID,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        wa_group_name: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_currently_locked: Optional[bool] = None,
        last_wa_sync_at: Optional[datetime] = None,
    ) -> DefaultAppCrudResult[Thread]:
        """Fonction pour mettre à jour un thread dans la base de données."""
        try:
            old_thread = await self.get_thread_by_id(thread_id=thread_id)

            if old_thread.is_error():
                return old_thread

            if name is not None:
                old_thread.data.name = name
            if slug is not None:
                old_thread.data.slug = slug
            if description is not None:
                old_thread.data.description = description
            if wa_group_name is not None:
                old_thread.data.wa_group_name = wa_group_name
            if password_hash is not None:
                old_thread.data.password_hash = password_hash
            if is_active is not None:
                old_thread.data.is_active = is_active
            if is_currently_locked is not None:
                old_thread.data.is_currently_locked = is_currently_locked
            if last_wa_sync_at is not None:
                old_thread.data.last_wa_sync_at = last_wa_sync_at

            old_thread.data.updated_at = datetime.now(UTC)

            await self.db.commit()

            logger.info(f"Thread {thread_id} mis à jour avec succès")
            return CrudResult.crud_success(data=old_thread.data)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Thread
            )

    async def delete_thread(self, thread_id: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer un thread de la base de données."""
        try:
            thread = await self.get_thread_by_id(thread_id)

            if thread.is_error():
                return CrudResult.crud_failure(
                    thread.error, status_code=thread.status_code
                )

            await self.db.delete(thread.data)
            await self.db.commit()

            logger.info(f"Thread {thread_id} supprimé avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Thread
            )

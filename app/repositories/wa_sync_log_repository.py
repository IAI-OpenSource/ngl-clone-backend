"""
Repository pour la table wa_sync_log.
Gère les opérations CRUD sur les logs de synchronisation WhatsApp.
"""

from dataclasses import dataclass
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.wa_sync_log import WASyncLog
from app.db.models.enums.enums import WASyncType
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class WASyncLogRepository:
    """Repository pour la gestion des logs de synchronisation WhatsApp."""

    db: AsyncSession

    async def insert_sync_log(
        self,
        thread_id: UUID,
        sync_type: WASyncType,
        wa_jid: Optional[str] = None,
        members_added: int = 0,
        members_removed: int = 0,
        payload: Optional[dict] = None,
    ) -> DefaultAppCrudResult[WASyncLog]:
        """Fonction pour insérer un log de synchronisation en base de données."""
        try:
            sync_log = WASyncLog(
                thread_id=thread_id,
                sync_type=sync_type,
                wa_jid=wa_jid,
                payload=payload,
            )
            # members_added et members_removed ont init=False, on les assigne après
            sync_log.members_added = members_added
            sync_log.members_removed = members_removed
            
            self.db.add(sync_log)
            await self.db.commit()
            await self.db.refresh(sync_log)

            logger.info(f"Log de synchronisation pour thread {thread_id} ajouté avec succès !")
            return CrudResult.crud_success(
                data=sync_log, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WASyncLog
            )

    async def get_sync_log_by_id(self, log_id: UUID) -> DefaultAppCrudResult[WASyncLog]:
        """Fonction pour récupérer un log de synchronisation à partir de son ID."""
        try:
            stmt = select(WASyncLog).where(WASyncLog.id == log_id)
            result = await self.db.execute(stmt)
            sync_log = result.scalar_one_or_none()

            if sync_log is None:
                logger.info(f"Log de synchronisation avec ID {log_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Log de synchronisation inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=sync_log)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_sync_logs_by_thread_id(
        self, thread_id: UUID
    ) -> DefaultAppCrudResult[list[WASyncLog]]:
        """Fonction pour récupérer tous les logs de synchronisation d'un thread."""
        try:
            stmt = select(WASyncLog).where(WASyncLog.thread_id == thread_id)
            result = await self.db.execute(stmt)
            sync_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=sync_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WASyncLog
            )

    async def get_sync_logs_by_type(
        self, sync_type: WASyncType
    ) -> DefaultAppCrudResult[list[WASyncLog]]:
        """Fonction pour récupérer tous les logs de synchronisation par type."""
        try:
            stmt = select(WASyncLog).where(WASyncLog.sync_type == sync_type)
            result = await self.db.execute(stmt)
            sync_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=sync_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WASyncLog
            )

    async def get_sync_logs_by_wa_jid(
        self, wa_jid: str
    ) -> DefaultAppCrudResult[list[WASyncLog]]:
        """Fonction pour récupérer tous les logs de synchronisation par identifiant WhatsApp."""
        try:
            stmt = select(WASyncLog).where(WASyncLog.wa_jid == wa_jid)
            result = await self.db.execute(stmt)
            sync_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=sync_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WASyncLog
            )

    async def delete_sync_log(self, log_id: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer un log de synchronisation de la base de données."""
        try:
            sync_log = await self.get_sync_log_by_id(log_id)

            if sync_log.is_error():
                return CrudResult.crud_failure(
                    sync_log.error, status_code=sync_log.status_code
                )

            await self.db.delete(sync_log.data)
            await self.db.commit()

            logger.info(f"Log de synchronisation {log_id} supprimé avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WASyncLog
            )

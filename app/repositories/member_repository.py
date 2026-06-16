"""
Repository pour la table members.
Gère les opérations CRUD sur les membres (utilisateurs WhatsApp).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.member import Member
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class MemberRepository:
    """Repository pour la gestion des membres (utilisateurs WhatsApp)."""

    db: AsyncSession

    async def insert_member(
        self,
        wa_jid: str,
        wa_name: Optional[str] = None,
        display_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> DefaultAppCrudResult[Member]:
        """Fonction pour insérer un membre en base de données."""
        try:
            member = Member(
                wa_jid=wa_jid,
                wa_name=wa_name,
                display_name=display_name,
                phone_number=phone_number,
                avatar_url=avatar_url,
            )
            self.db.add(member)
            await self.db.commit()
            await self.db.refresh(member)

            logger.info(f"Membre {wa_jid} ajouté avec succès !")
            return CrudResult.crud_success(
                data=member, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Member
            )

    async def get_member_by_id(self, member_id: UUID) -> DefaultAppCrudResult[Member]:
        """Fonction pour récupérer un membre à partir de son ID."""
        try:
            stmt = select(Member).where(Member.id == member_id)
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if member is None:
                logger.info(f"Membre avec ID {member_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Membre inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=member)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_member_by_wa_jid(self, wa_jid: str) -> DefaultAppCrudResult[Member]:
        """Fonction pour récupérer un membre à partir de son identifiant WhatsApp."""
        try:
            stmt = select(Member).where(Member.wa_jid == wa_jid)
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if member is None:
                logger.info(f"Membre avec wa_jid {wa_jid} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Membre inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=member)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_all_members(
        self,
        is_active: Optional[bool] = None,
    ) -> DefaultAppCrudResult[list[Member]]:
        """Fonction pour récupérer tous les membres de la base de données."""
        try:
            stmt = select(Member)
            if is_active:
                stmt = stmt.where(Member.is_active == True)
            elif is_active is not None:
                stmt = stmt.where(Member.is_active == False)

            result = await self.db.execute(stmt)
            members = list(result.scalars().all())

            return CrudResult.crud_success(data=members)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Member
            )

    async def update_member(
        self,
        member_id: UUID,
        wa_name: Optional[str] = None,
        display_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> DefaultAppCrudResult[Member]:
        """Fonction pour mettre à jour un membre dans la base de données."""
        try:
            old_member = await self.get_member_by_id(member_id=member_id)

            if old_member.is_error():
                return old_member

            if wa_name is not None:
                old_member.data.wa_name = wa_name
            if display_name is not None:
                old_member.data.display_name = display_name
            if phone_number is not None:
                old_member.data.phone_number = phone_number
            if avatar_url is not None:
                old_member.data.avatar_url = avatar_url
            if is_active is not None:
                old_member.data.is_active = is_active

            old_member.data.updated_at = datetime.now(UTC)

            await self.db.commit()

            logger.info(f"Membre {member_id} mis à jour avec succès")
            return CrudResult.crud_success(data=old_member.data)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Member
            )

    async def delete_member(self, member_id: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer un membre de la base de données."""
        try:
            member = await self.get_member_by_id(member_id)

            if member.is_error():
                return CrudResult.crud_failure(
                    member.error, status_code=member.status_code
                )

            await self.db.delete(member.data)
            await self.db.commit()

            logger.info(f"Membre {member_id} supprimé avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Member
            )

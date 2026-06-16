from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.member_cache import MemberCache
from app.globals.cache_duration import CacheDuration
from app.repositories.member_repository import MemberRepository
from app.schemas.member_schemas import CreateMember, ReadMember, UpdateMember

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class MemberService:
    """Service pour la gestion des membres (utilisateurs WhatsApp)."""

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__member_cache = MemberCache(cache)
        self.__member_repo = MemberRepository(self.__db)
        self._service_name = ServicesNames.MEMBER_SERVICE

    async def service_find_member_by_id(
        self, member_id: UUID
    ) -> DefaultAppServiceResult[ReadMember]:
        """Logique métier de récupération d'un membre par ID."""
        
        member_from_cache = await self.__member_cache.get_member_from_cache(
            member_id=member_id
        )
        
        if member_from_cache is not None:
            return ServiceResult.service_success(data=member_from_cache)
        
        member_repo = await self.__member_repo.get_member_by_id(member_id=member_id)
        
        if member_repo.is_error():
            logger.error(f"Erreur: {member_repo.error}")
            return member_repo.to_service_error(service_name=self._service_name)
        
        read_member = ReadMember.model_validate(member_repo.data)
        
        await self.__member_cache.set_member_in_cache(
            member=read_member, ttl=CacheDuration.TWENTY_MINUTES
        )
        
        return ServiceResult.service_success(
            data=read_member,
            service_name=self._service_name,
        )

    async def service_find_member_by_wa_jid(
        self, wa_jid: str
    ) -> DefaultAppServiceResult[ReadMember]:
        """Logique métier de récupération d'un membre par son ID WhatsApp."""
        
        member_repo = await self.__member_repo.get_member_by_wa_jid(wa_jid=wa_jid)
        
        if member_repo.is_error():
            logger.error(f"Erreur: {member_repo.error}")
            return member_repo.to_service_error(service_name=self._service_name)
        
        read_member = ReadMember.model_validate(member_repo.data)
        
        await self.__member_cache.set_member_in_cache(
            member=read_member, ttl=CacheDuration.TWENTY_MINUTES
        )
        
        return ServiceResult.service_success(
            data=read_member,
            service_name=self._service_name,
        )

    async def service_find_all_members(
        self, is_active: Optional[bool] = None
    ) -> DefaultAppServiceResult[list[ReadMember]]:
        """Logique métier de récupération de tous les membres."""
        
        members_repo = await self.__member_repo.get_all_members(is_active=is_active)
        
        if members_repo.is_error():
            logger.error(f"Erreur: {members_repo.error}")
            return members_repo.to_service_error(service_name=self._service_name)
        
        read_members = [ReadMember.model_validate(member) for member in members_repo.data]
        
        return ServiceResult.service_success(
            data=read_members,
            service_name=self._service_name,
        )

    async def service_create_member(
        self, member_data: CreateMember
    ) -> DefaultAppServiceResult[ReadMember]:
        """Logique métier pour créer un membre."""
        
        member_repo = await self.__member_repo.insert_member(
            wa_jid=member_data.wa_jid,
            wa_name=member_data.wa_name,
            display_name=member_data.display_name,
            phone_number=member_data.phone_number,
            avatar_url=member_data.avatar_url,
        )
        
        if member_repo.is_error():
            logger.error(f"Erreur: {member_repo.error}")
            return member_repo.to_service_error(service_name=self._service_name)
        
        read_member = ReadMember.model_validate(member_repo.data)
        
        await self.__member_cache.set_member_in_cache(
            member=read_member, ttl=CacheDuration.TWENTY_MINUTES
        )
        
        return ServiceResult.service_success(
            data=read_member,
            status_code=member_repo.status_code,
            service_name=self._service_name,
        )

    async def service_update_member(
        self,
        member_id: UUID,
        member_update_data: UpdateMember
    ) -> DefaultAppServiceResult[ReadMember]:
        """Logique métier pour mettre à jour un membre."""
        
        member_repo = await self.__member_repo.update_member(
            member_id=member_id,
            wa_name=member_update_data.wa_name,
            display_name=member_update_data.display_name,
            phone_number=member_update_data.phone_number,
            avatar_url=member_update_data.avatar_url,
            is_active=member_update_data.is_active,
        )
        
        if member_repo.is_error():
            logger.error(f"Erreur: {member_repo.error}")
            return member_repo.to_service_error(service_name=self._service_name)
        
        read_member = ReadMember.model_validate(member_repo.data)
        
        await self.__member_cache.set_member_in_cache(
            member=read_member, ttl=CacheDuration.TWENTY_MINUTES
        )
        
        return ServiceResult.service_success(
            data=read_member,
            service_name=self._service_name,
        )

    async def service_delete_member(
        self, member_id: UUID
    ) -> DefaultAppServiceResult[None]:
        """Logique métier pour supprimer un membre."""
        
        member_repo = await self.__member_repo.delete_member(member_id=member_id)
        
        if member_repo.is_error():
            logger.error(f"Erreur: {member_repo.error}")
            return member_repo.to_service_error(service_name=self._service_name)
        
        await self.__member_cache.invalid_member_in_cache(member_id)
        
        return ServiceResult.service_success(
            data=None,
            status_code=member_repo.status_code,
            service_name=self._service_name,
        )

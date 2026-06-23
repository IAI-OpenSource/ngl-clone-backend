"""
Repository pour la table messages.
Gère les opérations CRUD sur les messages.
"""

from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from fastapi import status

from app.db.models.message import Message
from app.db.models.member import Member
from app.db.models.message_mention import MessageMention
from app.db.models.enums.enums import WAStatus
from app.db.models.thread_member import ThreadMember
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils
from app.utils.pagination_cursor_utils import PaginationCursorUtils

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
        mentioned_member_ids: Optional[List[UUID]] = None,
    ) -> DefaultAppCrudResult[Message]:
        """Fonction pour insérer un message en base de données avec gestion des mentions.

        Args:
            thread_id: ID du thread
            content: Contenu du message
            wa_message_id: ID WhatsApp du message
            wa_status: Statut WhatsApp
            wa_forwarded_at: Date de transfert WhatsApp
            is_hidden: Si le message est caché
            hidden_reason: Raison du masquage
            hidden_at: Date du masquage
            mentioned_member_ids: Liste des IDs des membres mentionnés

        Returns:
            CrudResult contenant le message créé

        Processus:
            1. Vérifie que tous les member_ids existent (si fournis)
            2. Crée le message
            3. Crée les MessageMention en bulk pour les mentions
            4. Commit atomique
        """
        try:

            if mentioned_member_ids:
                # Vérification en une seule requête avec IN pour optimiser
                stmt = select(ThreadMember.member_id).where(
                    ThreadMember.member_id.in_(mentioned_member_ids),
                    ThreadMember.thread_id == thread_id,
                )
                result = await self.db.execute(stmt)
                existing_member_ids = set(result.scalars().all())

                # Trouver les IDs inexistants
                has_missings = set(mentioned_member_ids) != existing_member_ids
                if has_missings:
                    missings = set(mentioned_member_ids) - existing_member_ids
                    logger.warning(
                        f"Tentative de mention de membres inexistants dans le thread {thread_id}: "
                        f"{missings}"
                    )
                    return CrudResult.crud_failure(
                        RepositoriesUtils.not_found_error(
                            f"Certains membre mentionnés ne font pas partie de ce Thread : {missings}"
                        ),
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                valid_mentioned_ids = list(existing_member_ids)
            else:
                valid_mentioned_ids = []

            message = Message(
                thread_id=thread_id,
                content=content,
                wa_message_id=wa_message_id,
                hidden_reason=hidden_reason,
            )

            message.wa_status = wa_status
            message.wa_forwarded_at = wa_forwarded_at
            message.is_hidden = is_hidden
            message.hidden_at = hidden_at

            self.db.add(message)
            await self.db.flush()  # Obtenir l'ID du message pour les mentions

            if valid_mentioned_ids:
                message_mentions = [
                    MessageMention(message_id=message.id, member_id=member_id)
                    for member_id in valid_mentioned_ids
                ]
                self.db.add_all(message_mentions)

            await self.db.commit()
            await self.db.refresh(message)

            logger.info(
                f"Message {message.id} ajouté avec succès avec {len(valid_mentioned_ids)} mention(s)!"
            )
            return CrudResult.crud_success(
                data=message, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            await self.db.rollback()
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def get_message_by_id(
        self, message_id: UUID
    ) -> DefaultAppCrudResult[Message]:
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

    async def get_message_by_id_with_mentions(
        self, message_id: UUID
    ) -> DefaultAppCrudResult[tuple[Message, list[Member]]]:
        """Récupère un message avec ses membres mentionnés de manière optimisée.

        Utilise joinedload pour charger les mentions et leurs membres en une seule requête.
        Idéal pour récupérer un message unique avec toutes ses données de mentions.

        Returns:
            CrudResult contenant un tuple (message, liste_des_membres_mentionnés)
        """
        try:
            stmt = (
                select(Message)
                .where(Message.id == message_id)
                .options(joinedload(Message.mentions).joinedload(MessageMention.member))
            )
            result = await self.db.execute(stmt)
            message = result.unique().scalar_one_or_none()

            if message is None:
                logger.info(f"Message avec ID {message_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Message inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            mentioned_members = [mention.member for mention in message.mentions]
            return CrudResult.crud_success(data=(message, mentioned_members))

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_messages_by_thread_id_with_mentions(
        self,
        thread_id: UUID,
        is_hidden: Optional[bool] = None,
    ) -> DefaultAppCrudResult[list[tuple[Message, list[Member]]]]:
        """Récupère tous les messages d'un thread avec leurs membres mentionnés.

        Utilise selectinload pour éviter le problème cartésien avec plusieurs messages.
        Idéal pour récupérer une liste de messages avec leurs mentions.

        Args:
            thread_id: L'ID du thread
            is_hidden: Filtre optionnel pour les messages cachés

        Returns:
            CrudResult contenant une liste de tuples (message, liste_des_membres_mentionnés)
        """
        try:
            stmt = (
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(desc(Message.created_at))
            )

            if is_hidden:
                stmt = stmt.where(Message.is_hidden == True)
            elif is_hidden is False:
                stmt = stmt.where(Message.is_hidden == False)

            stmt = stmt.options(
                selectinload(Message.mentions).selectinload(MessageMention.member)
            )

            result = await self.db.execute(stmt)
            messages = list(result.scalars().all())

            # Préparer les données avec membres mentionnés
            messages_with_mentions = []
            for msg in messages:
                mentioned_members = [mention.member for mention in msg.mentions]
                messages_with_mentions.append((msg, mentioned_members))

            return CrudResult.crud_success(data=messages_with_mentions)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    @staticmethod
    def _build_messages_with_mentions(
        messages: list[Message],
    ) -> list[tuple[Message, list[Member]]]:
        """Construit la liste de tuples (message, membres_mentionnés) depuis une liste de messages ORM.

        Les mentions doivent déjà être chargées via selectinload.

        Args:
            messages: Liste de messages SQLAlchemy avec leurs mentions chargées

        Returns:
            Liste de tuples (message, liste_des_membres_mentionnés)
        """
        return [
            (msg, [mention.member for mention in msg.mentions])
            for msg in messages
        ]

    def _base_paginated_stmt(
        self,
        thread_id: UUID,
        is_hidden: Optional[bool],
    ):
        """Construit le stmt de base commun à toutes les branches de pagination.

        Args:
            thread_id: ID du thread
            is_hidden: Filtre sur le champ is_hidden

        Returns:
            Select SQLAlchemy configuré avec les filtres et le selectinload des mentions
        """
        stmt = select(Message).where(Message.thread_id == thread_id)

        if is_hidden is True:
            stmt = stmt.where(Message.is_hidden == True)
        elif is_hidden is False:
            stmt = stmt.where(Message.is_hidden == False)

        stmt = stmt.options(
            selectinload(Message.mentions).selectinload(MessageMention.member)
        )
        return stmt

    async def get_messages_by_thread_id_paginated(
        self,
        thread_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
        is_hidden: Optional[bool] = False,
    ) -> DefaultAppCrudResult[tuple[list[tuple[Message, list[Member]]], bool, bool, Optional[str], Optional[str]]]:
        """Récupère les messages d'un thread avec pagination par curseur.

        Cette méthode utilise une requête optimisée avec des index sur (thread_id, created_at, id)
        pour une pagination efficace par curseur.

        Args:
            thread_id: L'ID du thread
            limit: Nombre maximum de messages à récupérer (par défaut 20)
            cursor: Curseur de pagination encodé (base64). Si None, récupère la première page.
                    Format: {"thread_id": UUID, "id": UUID, "dateable": datetime, "direction": "next"|"previous"}
            is_hidden: Filtre optionnel pour les messages cachés (par défaut False = exclut les cachés)

        Returns:
            CrudResult contenant un tuple avec:
                - Liste de tuples (message, liste_des_membres_mentionnés)
                - has_next_page: True s'il y a une page suivante
                - has_previous_page: True s'il y a une page précédente
                - next_cursor: Curseur pour la page suivante (base64 encodé)
                - previous_cursor: Curseur pour la page précédente (base64 encodé)
        """
        try:
            has_next_page = False
            has_previous_page = False
            next_cursor: Optional[str] = None
            previous_cursor: Optional[str] = None

            if cursor is None:
                # --- Première page : messages les plus récents, ordre DESC ---
                stmt = (
                    self._base_paginated_stmt(thread_id, is_hidden)
                    .order_by(desc(Message.created_at), desc(Message.id))
                    .limit(limit + 1)  # +1 pour détecter s'il y a une page suivante
                )

                result = await self.db.execute(stmt)
                messages = list(result.scalars().all())

                if len(messages) > limit:
                    has_next_page = True
                    messages = messages[:limit]

                messages_with_mentions = self._build_messages_with_mentions(messages)

                if has_next_page and messages_with_mentions:
                    last_msg = messages_with_mentions[-1][0]
                    next_cursor = PaginationCursorUtils.encode_messages_cursor(
                        last_item_id=last_msg.id,
                        last_item_created_at=last_msg.created_at,
                        thread_id=thread_id,
                        is_next_page=True,
                    )

                # Pas de page précédente pour la première page
                has_previous_page = False

            else:
                # --- Navigation avec curseur ---
                try:
                    thread_id_from_cursor, last_msg_id, last_created_at, is_next = (
                        PaginationCursorUtils.decode_messages_cursor(cursor)
                    )
                except ValueError as e:
                    return CrudResult.crud_failure(
                        RepositoriesUtils.not_found_error(f"Curseur de pagination invalide: {e}"),
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # Valider que le curseur correspond au bon thread
                if thread_id_from_cursor != thread_id:
                    return CrudResult.crud_failure(
                        RepositoriesUtils.not_found_error(
                            "Curseur de pagination invalide pour ce thread"
                        ),
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                if is_next:
                    # --- Page suivante : messages plus anciens que le curseur, ordre DESC ---
                    stmt = (
                        self._base_paginated_stmt(thread_id, is_hidden)
                        .where(
                            or_(
                                Message.created_at < last_created_at,
                                and_(
                                    Message.created_at == last_created_at,
                                    Message.id < last_msg_id,
                                ),
                            )
                        )
                        .order_by(desc(Message.created_at), desc(Message.id))
                        .limit(limit + 1)
                    )

                    result = await self.db.execute(stmt)
                    messages = list(result.scalars().all())

                    if len(messages) > limit:
                        has_next_page = True
                        messages = messages[:limit]

                    messages_with_mentions = self._build_messages_with_mentions(messages)

                    if has_next_page and messages_with_mentions:
                        new_last_msg = messages_with_mentions[-1][0]
                        next_cursor = PaginationCursorUtils.encode_messages_cursor(
                            last_item_id=new_last_msg.id,
                            last_item_created_at=new_last_msg.created_at,
                            thread_id=thread_id,
                            is_next_page=True,
                        )

                    # Il y a forcément une page précédente puisqu'on a avancé
                    has_previous_page = True
                    previous_cursor = PaginationCursorUtils.encode_messages_cursor(
                        last_item_id=last_msg_id,
                        last_item_created_at=last_created_at,
                        thread_id=thread_id,
                        is_next_page=False,
                    )

                else:
                    # --- Page précédente : messages plus récents que le curseur ---
                    # On récupère en ordre ASC pour avoir le "slice" correct côté ancien,
                    # puis on inverse pour restituer l'ordre DESC attendu par le client.
                    stmt = (
                        self._base_paginated_stmt(thread_id, is_hidden)
                        .where(
                            or_(
                                Message.created_at > last_created_at,
                                and_(
                                    Message.created_at == last_created_at,
                                    Message.id > last_msg_id,
                                ),
                            )
                        )
                        .order_by(Message.created_at, Message.id)  # ASC pour limiter depuis l'ancien bord
                        .limit(limit + 1)
                    )

                    result = await self.db.execute(stmt)
                    # messages en ordre ASC : [plus_ancien ... plus_recent]
                    messages = list(result.scalars().all())

                    if len(messages) > limit:
                        # On garde les `limit` messages les plus récents
                        # (en ASC cela correspond à la fin de la liste)
                        has_previous_page = True
                        messages = messages[len(messages) - limit:]
                    
                    # Inverser pour restituer l'ordre DESC attendu
                    messages.reverse()

                    messages_with_mentions = self._build_messages_with_mentions(messages)

                    if has_previous_page and messages_with_mentions:
                        # Le message le plus récent de la page (premier après reverse) sert de curseur précédent
                        new_first_msg = messages_with_mentions[0][0]
                        previous_cursor = PaginationCursorUtils.encode_messages_cursor(
                            last_item_id=new_first_msg.id,
                            last_item_created_at=new_first_msg.created_at,
                            thread_id=thread_id,
                            is_next_page=False,
                        )

                    # Il y a forcément une page suivante puisqu'on a reculé
                    has_next_page = True
                    if messages_with_mentions:
                        new_last_msg = messages_with_mentions[-1][0]
                        next_cursor = PaginationCursorUtils.encode_messages_cursor(
                            last_item_id=new_last_msg.id,
                            last_item_created_at=new_last_msg.created_at,
                            thread_id=thread_id,
                            is_next_page=True,
                        )

            return CrudResult.crud_success(
                data=(messages_with_mentions, has_next_page, has_previous_page, next_cursor, previous_cursor)
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

    async def get_mentioned_members_by_message(
        self, message_id: UUID
    ) -> DefaultAppCrudResult[list[Member]]:
        """Récupère uniquement les membres mentionnés dans un message.

        Requête directe sur la table de jointure MessageMention.
        La méthode la plus légère en ressources si vous n'avez besoin que des membres.

        Args:
            message_id: L'ID du message

        Returns:
            CrudResult contenant la liste des membres mentionnés
        """
        try:
            stmt = (
                select(Member)
                .join(MessageMention, Member.id == MessageMention.member_id)
                .where(MessageMention.message_id == message_id)
            )
            result = await self.db.execute(stmt)
            mentioned_members = list(result.scalars().all())

            return CrudResult.crud_success(data=mentioned_members)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Message
            )

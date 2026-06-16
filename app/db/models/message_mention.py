"""
Modèle pour la table message_mentions.
Table de jointure entre messages et members pour les mentions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.member import Member


# Noms des contraintes
FK_MESSAGE_MENTIONS_MESSAGE = "fk_message_mentions_message"
FK_MESSAGE_MENTIONS_MEMBER = "fk_message_mentions_member"
IDX_MESSAGE_MENTIONS_MEMBER = "idx_message_mentions_member"


class MessageMention(Base, IntegrityMapperMixin):
    """Représentation d'une mention d'un membre dans un message."""

    __tablename__ = "message_mentions"

    # Clés étrangères (composite primary key)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE", name=FK_MESSAGE_MENTIONS_MESSAGE),
        nullable=False,
        primary_key=True,
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE", name=FK_MESSAGE_MENTIONS_MEMBER),
        nullable=False,
        primary_key=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )

    # Index
    __table_args__ = (
        Index(IDX_MESSAGE_MENTIONS_MEMBER, "member_id"),
    )

    # Relations
    message: Mapped["Message"] = relationship(
        "Message",
        foreign_keys=[message_id],
        back_populates="mentions",
        uselist=False,
        init=False,
    )
    member: Mapped["Member"] = relationship(
        "Member",
        foreign_keys=[member_id],
        back_populates="message_mentions",
        uselist=False,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_MESSAGE_MENTIONS_MESSAGE: "Le message spécifié n'existe pas.",
        FK_MESSAGE_MENTIONS_MEMBER: "Le membre spécifié n'existe pas.",
    }
"""
Modèle pour la table thread_members.
Table de jointure entre threads et members avec rôle WhatsApp.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    ForeignKey,
    Boolean,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums.enums import WAMemberRole

if TYPE_CHECKING:
    from app.db.models.thread import Thread
    from app.db.models.member import Member


# Noms des contraintes
FK_THREAD_MEMBERS_THREAD = "fk_thread_members_thread"
FK_THREAD_MEMBERS_MEMBER = "fk_thread_members_member"
UQ_THREAD_MEMBERS_THREAD_MEMBER = "uq_thread_members_thread_member"
IDX_THREAD_MEMBERS_MEMBER = "idx_thread_members_member_active"


class ThreadMember(Base, IntegrityMapperMixin):
    """Représentation de l'association entre un thread et un membre."""

    __tablename__ = "thread_members"

    # Clés étrangères (composite primary key)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE", name=FK_THREAD_MEMBERS_THREAD),
        nullable=False,
        primary_key=True,
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE", name=FK_THREAD_MEMBERS_MEMBER),
        nullable=False,
        primary_key=True,
    )

    # Rôle dans le groupe WhatsApp
    wa_role: Mapped[WAMemberRole] = mapped_column(
        SQLEnum(WAMemberRole), nullable=False, default=WAMemberRole.MEMBER
    )

    # Statut
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, init=False
    )

    # Date de départ (si le membre a quitté)
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )

    # Index
    __table_args__ = (
        Index(
            IDX_THREAD_MEMBERS_MEMBER,
            "member_id",
            postgresql_where=(is_active == True),
        ),
    )

    # Relations
    thread: Mapped["Thread"] = relationship(
        "Thread",
        foreign_keys=[thread_id],
        back_populates="members",
        uselist=False,
        init=False,
    )
    member: Mapped["Member"] = relationship(
        "Member",
        foreign_keys=[member_id],
        back_populates="thread_members",
        uselist=False,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_THREAD_MEMBERS_THREAD: "Le thread spécifié n'existe pas.",
        FK_THREAD_MEMBERS_MEMBER: "Le membre spécifié n'existe pas.",
        UQ_THREAD_MEMBERS_THREAD_MEMBER: "Ce membre est déjà associé à ce thread.",
    }
"""
Énumérations pour les types de base de données.
"""

from enum import Enum


class UserType(str, Enum):
    """Rôles des utilisateurs sur la plateforme."""

    ADMIN = "ADMIN"
    USER = "USER"


class SexeType(str, Enum):
    """Sexes possibles pour les utilisateurs."""

    F = "F"
    M = "M"


class WAStatus(str, Enum):
    """Statut des messages WhatsApp."""

    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class WAMemberRole(str, Enum):
    """Rôle des membres dans un groupe WhatsApp."""

    MEMBER = "member"
    ADMIN = "admin"


class WASyncType(str, Enum):
    """Type de synchronisation WhatsApp."""

    INITIAL_IMPORT = "initial_import"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MANUAL_REFRESH = "manual_refresh"


class ReportStatus(str, Enum):
    """Statut d'un rapport."""

    PENDING = "pending"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class ReportCategory(str, Enum):
    """Catégorie d'un rapport."""

    HARASSMENT = "harassment"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"

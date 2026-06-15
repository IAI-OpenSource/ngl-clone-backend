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

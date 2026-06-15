from dataclasses import dataclass
from enum import Enum


@dataclass
class BaseCacheEntity:
    """Defininis toutes les entités qui peuvent être mises en cache avec leurs clés respectives"""

    USER = "entity:user:{id}"
    SESSION = "entity:session:{id}"


class AvailableCacheKeys(str, Enum):
    """Definis toutes les clés de cache utilisées dans l'application, organisées par entité et par type de données"""

    # J'ai juste essayé d'imaginer quelques clés de cache qui pourraient être utiles pour les différentes entités,
    # mais on peut en ajouter ou en enlever selon les besoins spécifiques de l'application.

    # Clés de cache pour les utilisateurs
    USER_OBJECT = BaseCacheEntity.USER  # Clé pour un utilisateur spécifique

    # Clés de cache pour les sessions
    SESSION_OBJECT = BaseCacheEntity.SESSION  # Clé pour une session spécifique

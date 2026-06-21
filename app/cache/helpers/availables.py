from dataclasses import dataclass
from enum import Enum


@dataclass
class BaseCacheEntity:
    """Defininis toutes les entités qui peuvent être mises en cache avec leurs clés respectives"""

    USER = "entity:user:{id}"
    SESSION = "entity:session:{id}"
    MESSAGE = "entity:message:{id}"
    THREAD = "entity:thread:{id}"
    THREAD_BY_WA_GROUP = "entity:thread:wa_group:{wa_group_jid}"
    MEMBER = "entity:member:{id}"


class AvailableCacheKeys(str, Enum):
    """Definis toutes les clés de cache utilisées dans l'application, organisées par entité et par type de données"""

    # J'ai juste essayé d'imaginer quelques clés de cache qui pourraient être utiles pour les différentes entités,
    # mais on peut en ajouter ou en enlever selon les besoins spécifiques de l'application.

    # Clés de cache pour les utilisateurs
    USER_OBJECT = BaseCacheEntity.USER  # Clé pour un utilisateur spécifique

    # Clés de cache pour les sessions
    SESSION_OBJECT = BaseCacheEntity.SESSION  # Clé pour une session spécifique

    # Clés de cache pour les messages
    MESSAGE_OBJECT = BaseCacheEntity.MESSAGE  # Clé pour un message spécifique

    # Clés de cache pour les threads
    THREAD_OBJECT = BaseCacheEntity.THREAD  # Clé pour un thread spécifique
    THREAD_BY_WA_GROUP_OBJECT = BaseCacheEntity.THREAD_BY_WA_GROUP  # Clé pour un thread par JID WhatsApp

    INTERNAL_THREAD_RAW_OBJECT = BaseCacheEntity.THREAD + ":raw"  # Clé pour les données brutes d'un thread

    # Clés de cache pour les membres
    MEMBER_OBJECT = BaseCacheEntity.MEMBER  # Clé pour un membre spécifique

    # Clés de cache pour les listes
    THREADS_LIST = "entity:thread:list"  # Clé pour la liste de tous les threads
    MESSAGES_BY_THREAD_LIST = BaseCacheEntity.THREAD + ":messageslist"  # Clé pour la liste des messages d'un thread
    MEMBERS_BY_THREAD_LIST = BaseCacheEntity.THREAD + ":memberslist"  # Clé pour la liste des membres d'un thread

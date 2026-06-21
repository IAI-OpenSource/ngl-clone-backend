

class WorkersTaskNames:
    """
    Classe pour centraliser les noms des tâches Celery utilisées dans l'application pour éviter les erreurs de frappe
    et faciliter la maintenance. Chaque nom de tâche est défini comme une constante de classe.
    """

    SYNC_THREAD_MEMBERS_FROM_GROUP: str = "sync_thread_members_from_group"

    SEND_MESSAGE_TO_GROUP: str = "send_message_to_group"


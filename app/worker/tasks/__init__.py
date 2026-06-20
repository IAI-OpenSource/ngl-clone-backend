def add_all_tasks():
    """
    Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter.
    """
    from app.worker.tasks.sync_thread_members import sync_thread_members_from_group

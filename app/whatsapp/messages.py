from app.schemas.thread_schemas import ReadThread


def success_thread_add(thread: ReadThread) -> str:
    """Message de succès pour l'ajout d'un thread."""
    return f"""Thread '{thread.name}' ajouté avec succès !
Slug: {thread.slug}
Vous pouvez maintenant accéder à ce thread via l'API ou l'interface utilisateur.
Mot Passe : {'Avec Mot de passe' if thread.has_password else "Pas de mot de passe"}
"""
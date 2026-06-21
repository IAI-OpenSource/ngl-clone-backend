from app.schemas.thread_schemas import ReadThread
from app.utils.format import formater_date_heure_en_francais


def success_thread_add(thread: ReadThread, mdp: str) -> str:
    """Message de succès pour l'ajout d'un thread."""
    return f"""Thread '{thread.name}' ajouté avec succès !
Slug: {thread.slug}
Vous pouvez maintenant accéder à ce thread via l'API ou l'interface utilisateur.
Mot Passe par défaut : {mdp}"""


def format_ngl_status(thread: ReadThread) -> str:
    """Formate le statut du thread pour la commande /ngl."""
    status_emoji = "🟢" if thread.is_active else "🔴"
    status_text = "Actif" if thread.is_active else "Inactif"
    lock_emoji = "🔒" if thread.is_currently_locked else "🔓"
    lock_text = "Oui" if thread.is_currently_locked else "Non"
    
    last_sync = formater_date_heure_en_francais(thread.last_wa_sync_at) if thread.last_wa_sync_at else "Jamais"
    created = formater_date_heure_en_francais(thread.created_at)
    
    description = thread.description or "Aucune"
    
    return f"""📡 *Statut du Thread*

📌 *Nom:* {thread.name}
🔗 *Slug:* {thread.slug}
📝 *Description:* {description}

{status_emoji} *Statut:* {status_text}
{lock_emoji} *Verrouillé:* {lock_text}

📅 *Créé le:* {created}
🔄 *Dernière sync:* {last_sync}"""


def format_lock_confirmation(thread_name: str) -> str:
    """Message de confirmation pour /lock."""
    return f"""🔒 *Thread verrouillé*

Le thread *'{thread_name}'* a été verrouillé.
Les nouveaux messages ne seront plus acceptés.

⚠️ Seuls les administrateurs peuvent déverrouiller."""


def format_unlock_confirmation(thread_name: str) -> str:
    """Message de confirmation pour /unlock."""
    return f"""🔓 *Thread déverrouillé*

Le thread *'{thread_name}'* a été déverrouillé.
Les nouveaux messages sont à nouveau acceptés."""


def format_edit_confirmation(field: str, old_value: str, new_value: str) -> str:
    """Message de confirmation pour /edit-XXX."""
    field_names = {
        "name": "Nom",
        "description": "Description",
        "slug": "Slug",
    }
    field_name = field_names.get(field, field)
    return f"""✅ *Thread modifié*

*Champ '{field_name}'* mis à jour:
*Ancienne valeur:* {old_value}
*Nouvelle valeur:* {new_value}"""


def format_edit_error(error_message: str) -> str:
    """Message d'erreur pour /edit-XXX."""
    return f"""❌ *Erreur de modification*

{error_message}"""


def get_help_message() -> str:
    """Message d'aide pour /help."""
    return """📚 *Commandes Disponibles*

🔍 */ngl* - Voir le statut du thread

🔒 */lock* - Verrouiller le thread *(Admin)*
🔓 */unlock* - Déverrouiller le thread *(Admin)*

✏️ */edit-name <texte>* - Changer le nom *(Admin)*
✏️ */edit-desc <texte>* - Changer la description *(Admin)*
✏️ */edit-slug <texte>* - Changer le slug *(Admin)*

❓ */help* - Afficher cette aide
📖 */docs* - Documentation du projet"""


def get_docs_message() -> str:
    """Message de documentation pour /docs."""
    return """📖 *À propos de NGL Clone*

NGL Clone est un projet open source pour créer et gérer des threads de discussion anonymes avec une intégration WhatsApp.

🌐 *Liens utiles:*
• Code source: [à compléter]
• Documentation: [à compléter]
• Contribuer: [à compléter]

💡 *Technologies:* Python, FastAPI, SQLAlchemy, WhatsApp API (Evolution)

🤝 *Contribuez:* Ce projet est open source, n'hésitez pas à contribuer !"""
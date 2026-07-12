from app.core.config import FRONTEND_URL
from app.schemas.thread_schemas import ReadThread
from app.utils.format import formater_date_heure_en_francais

def _get_all_messages_url(thread_slug: str) -> str:
    return f"{FRONTEND_URL}/threads/{thread_slug}/new-message"

def _get_new_message_url(thread_slug: str) -> str:
    return f"{FRONTEND_URL}/threads/{thread_slug}/messages"

def format_new_message_caption(thread_slug: str, mentioned_names: list[str] | None = None) -> str:
    """Formate la légende de l'image envoyée sur WhatsApp pour un nouveau message."""

    
    mention_intro = ""
    if mentioned_names:
        formatted_names = [name.strip().title() for name in mentioned_names if name]
        
        if len(formatted_names) == 1:
            mention_intro = f"{formatted_names[0]}, on parle de toi ici ! 🤫\n\n"
        elif len(formatted_names) == 2:
            mention_intro = f"{formatted_names[0]} et {formatted_names[1]}, on parle de vous ici ! 🤫\n\n"
        elif len(formatted_names) > 2:
            names_str = ", ".join(formatted_names[:-1]) + f" et {formatted_names[-1]}"
            mention_intro = f"{names_str}, on parle de vous ici ! 🤫\n\n"
            
    return f"""📣 *Nouveau Message Anonyme !*
    
{mention_intro}

💬 *Écris ton message :* {_get_new_message_url(thread_slug)}
👀 *Voir les autres messages :* {_get_all_messages_url(thread_slug)}"""


def success_thread_add(thread: ReadThread, mdp: str) -> str:
    """Message de succès pour l'ajout d'un thread."""
    
    return f"""🎉 *Thread '{thread.name}' configuré avec succès !*
    
🔒 *Mot de passe par défaut :* `{mdp}`

🔗 *Lien pour envoyer un message anonyme :*
👉 {_get_new_message_url(thread.slug)}

🔑 *Accéder aux messages reçus :*
👉 {_get_all_messages_url(thread.slug)}"""


def format_ngl_status(thread: ReadThread) -> str:
    """Formate le statut du thread pour la commande /ngl."""
    status_emoji = "🟢" if thread.is_active else "🔴"
    status_text = "Actif" if thread.is_active else "Inactif"
    lock_emoji = "🔒" if thread.is_currently_locked else "🔓"
    lock_text = "Oui" if thread.is_currently_locked else "Non"
    
    last_sync = formater_date_heure_en_francais(thread.last_wa_sync_at) if thread.last_wa_sync_at else "Jamais"
    created = formater_date_heure_en_francais(thread.created_at)
    last_update_at = formater_date_heure_en_francais(thread.updated_at)
    description = thread.description or "Aucune"

    
    return f"""📡 *Statut du Thread*

📌 *Nom:* {thread.name}
🔗 *Slug:* {thread.slug}
📝 *Description:* {description}

{status_emoji} *Statut:* {status_text}
{lock_emoji} *Verrouillé:* {lock_text}

📅 *Créé le:* {created}
✏️ *Dernière modification:* {last_update_at}
🔄 *Dernière sync:* {last_sync}

💬 *Écris ton message:* {_get_new_message_url(thread.slug)}
👀 *Voir les autres messages:* {_get_all_messages_url(thread.slug)}"""


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
🔄 */sync-thread* - Synchroniser manuellement les membres du thread avec WhatsApp *(Admin)*

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

💀 Essayez pas de pirater le truc ou de faire de la merde svp, pardon c'est un truc juste pour s'amuser🤣

🌐 *Liens utiles:*
• Code source Front : https://github.com/IAI-OpenSource/ngl-clone-frontend
• Code source Back : https://github.com/IAI-OpenSource/ngl-clone-backend 
• Documentation: Aller lire le code 🤣
• Contribuer: DM ou si t'as la flemme de DM ouvre directement une PR, si c'est bon on va merger

💡 *Technos:* Typescript, Python, React, FastAPI, SQLAlchemy, WhatsApp API (Evolution) et d'autres trucs mais j'ai la flemme de tout lister

🤝 *Contribuez:* Ce projet est Full open source, n'hésitez pas à contribuer pour améliorer le spaghetti !"""
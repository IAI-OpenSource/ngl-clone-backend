# Ce fichier contient les messages d'erreur et de succès utilisés dans l'application
# Cela permet de centraliser la gestion des messages et de faciliter leur maintenance.


class Messages:
    # Messages d'erreur généraux
    INTERNAL_SERVER_ERROR = (
        "Une erreur interne est survenue. Veuillez réessayer plus tard."
    )
    NOT_FOUND = "Ressource non trouvée."
    UNAUTHORIZED = "Non autorisé. Veuillez vous connecter."
    FORBIDDEN = "Accès interdit. Vous n'avez pas les permissions nécessaires."
    BAD_REQUEST = "Requête invalide. Veuillez vérifier les données envoyées."

    # Messages spécifiques
    USER_NOT_FOUND = "Utilisateur non trouvé."

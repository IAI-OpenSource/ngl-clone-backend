# Routeurs HTTP, Schémas Pydantic & Middlewares

Ce document décrit le fonctionnement de la couche API, la configuration des réponses pour un Swagger de qualité, et les middlewares globaux.

---

> **📄 Documentation Available in English**
> An English version of this document is available: [routers_and_schemas_en.md](./routers_and_schemas_en.md)

---

## 1. Routeurs & Dépendances de Services

Les routeurs FastAPI reçoivent les requêtes, valident les données entrantes et délèguent immédiatement le travail aux services concernés.

### 1.1. Injection de Services
L'injection de services s'effectue au niveau de la signature des fonctions de route en utilisant `Annotated` et `Depends`. Des fonctions factory locales (comme `get_user_service`) créent les instances de service en leur injectant les ressources d'infrastructure (base de données et cache) :

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.cache.base.cache_wrapper import get_redis, CacheWrapper
from app.services.user_service import UserService

router = APIRouter(prefix="/users")

def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)]
) -> UserService:
    return UserService(db, cache)
```

---

## 2. Configuration Premium pour Swagger / OpenAPI

Pour obtenir une documentation interactive Swagger UI propre et professionnelle, sans schémas générés automatiquement aux noms illisibles (ex: `ApiBaseResponse_ReadUser_AppError_`), suivez scrupuleusement la règle suivante :

> [!IMPORTANT]
> - **`response_model` (FastAPI)** : Utilisez toujours une sous-classe concrète héritant de `DefaultAppApiResponse[T]` (ex: `UserInfos`). C'est ce type concret qui pilote la documentation OpenAPI et la sérialisation finale.
> - **Annotation de retour (`-> ...` Python)** : Utilisez `ApiBaseResponse[D, E]` (ex: `ApiBaseResponse[ReadUser, AppError]`). C'est le type réel retourné par la méthode helper `to_HTTP_api_base_response()`, ce qui évite les plaintes du linter de type statique.

### Exemple complet de Route propre :
```python
# 1. Définition du schéma concret (dans app/schemas/user_schemas.py)
class UserInfos(DefaultAppApiResponse[ReadUser]):
    """Schéma enveloppe de réponse pour les informations d'un utilisateur"""

# 2. Utilisation dans le routeur (dans app/routers/v1/auth_router.py)
@router.get("/me", response_model=UserInfos)
async def me(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiBaseResponse[ReadUser, AppError]:
    """Récupère les informations de l'utilisateur actuellement connecté"""
    
    service_res = auth_service.get_me(user=current_user)
    
    # to_HTTP_api_base_response injecte le statut HTTP et construit l'ApiBaseResponse
    return service_res.to_HTTP_api_base_response(reponse=response)
```

---

## 3. Middlewares Globaux

Le cycle de traitement des requêtes HTTP est sécurisé par des middlewares interceptant les requêtes et réponses.

### 3.1. Gestion des exceptions non capturées (`exception_handler_middleware.py`)
Ce middleware intercepte toutes les exceptions Python non gérées au sein de l'application (qui remonteraient autrement sous forme d'erreurs brutes ou de réponses vides) :
- Enregistre le traceback complet de l'erreur dans les logs via `logger.exception`.
- Traduit et retourne une réponse JSON standardisée de statut HTTP 500 respectant le schéma [DefaultAppApiResponse](../app/schemas/globals/api_base_response.py) contenant l'erreur `UNKNOWN_ERROR` avec le message utilisateur : *"Une erreur interne est survenue. Veuillez réessayer plus tard."*

### 3.2. Journalisation et Alerte de requêtes lentes (`request_logging_middleware.py`)
Ce middleware trace chaque requête HTTP entrante et sortante.
- Loggue la méthode HTTP, le chemin URL de la requête, le code de statut retourné et la durée exacte d'exécution en secondes.
- **Alerte de lenteur** : Si la durée d'exécution d'une requête dépasse **1 seconde**, un log de niveau `WARNING` est automatiquement généré avec le tag `REQUÊTE LENTE` pour faciliter l'identification des requêtes lourdes ou des problèmes de base de données.

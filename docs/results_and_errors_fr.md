# Gestion des Résultats et des Erreurs (Generic Results & Errors)

Ce document explique le fonctionnement du système de retour standardisé de l'application et comment l'utiliser pour gérer à la fois les données de succès et les erreurs de manière type-safe dans les couches **Repository**, **Service**, **Integration** et **API**.

Le code source associé à ce système est localisé dans [app/globals/app_result.py](../app/globals/app_result.py).

---

> **📄 Documentation Available in English**
> An English version of this document is available: [results_and_errors_en.md](./results_and_errors_en.md)

---

## 1. Principes de base

Toutes les réponses internes de l'application héritent d'une classe de base générique : `GenericAppResult[D, E]`.
- **`D`** représente le type de données retourné en cas de **succès** (ex: un modèle Pydantic, un type primitif, `None`, etc.).
- **`E`** représente le type d'erreur retourné en cas d'**échec** (par défaut, `AppError`).

Le système fournit trois classes spécialisées pour chaque couche de l'architecture :
1. **`CrudResult[D, E]`** (couche [Repository](../app/repositories/__init__.py))
2. **`ServiceResult[D, E]`** (couche [Service](../app/services/__init__.py))
3. **`IntegrationServiceResult[D, E]`** (couche [Intégrations Externes](../app/integrations/__init__.py))

---

## 2. Utilisation Standard (Erreurs par défaut : `AppError`)

Dans la majorité des cas, l'erreur par défaut [AppError](../app/globals/businnes_error.py) est suffisante. 

Pour simplifier l'écriture et améliorer la lisibilité du code, des alias de types préconfigurés avec `AppError` sont mis à disposition :
- **`DefaultAppCrudResult[D]`** est un alias de `CrudResult[D, AppError]`
- **`DefaultAppServiceResult[D]`** est un alias de `ServiceResult[D, AppError]`
- **`DefaultAppIntegrationServiceResult[D]`** est un alias de `IntegrationServiceResult[D, AppError]`
- **`DefaultAppApiResponse[D]`** est un alias de `ApiBaseResponse[D, AppError]`

Ces alias ne nécessitent qu'un seul paramètre générique (le type de donnée en cas de succès `D`).

### Exemple dans un Repository :

```python
from app.repositories import DefaultAppCrudResult, CrudResult
from app.schemas.user_schemas import ReadUser  # Modèle Pydantic
from app.globals.businnes_error import AppError, AppErrorType

async def get_user_by_id(user_id: UUID) -> DefaultAppCrudResult[User]:
    user = await db.get(User, user_id)
    if not user:
        # L'erreur par défaut est AppError
        error = AppError(
            error_type=AppErrorType.NOT_FOUND,
            error_message="L'utilisateur n'existe pas."
        )
        return CrudResult.crud_failure(error, status_code=404)

    return CrudResult.crud_success(user)
```

### Exemple dans un Service (Propagation et Conversion) :

```python
from app.services import DefaultAppServiceResult, ServiceResult
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import ReadUser

async def get_user_profile(user_id: UUID) -> DefaultAppServiceResult[ReadUser]:
    # Appel au repository
    repo_res = await UserRepository(db).get_user_by_id(user_id)

    if repo_res.is_error():
        # Conversion directe du CrudResult d'erreur en ServiceResult d'erreur.
        # Le type d'erreur (AppError) et le code de statut (404) sont conservés.
        return repo_res.to_service_error(service_name="UserService")

    read_user = ReadUser.model_validate(repo_res.data)
    return ServiceResult.service_success(read_user)
```

---

## 3. Utilisation Avancée (Erreurs Personnalisées)

Si une opération nécessite une structure d'erreur spécifique (ex: des erreurs de validation complexes, des détails spécifiques à un service tiers), vous pouvez définir un modèle d'erreur personnalisé et le passer en deuxième paramètre générique.

### Étape 1 : Définir le modèle d'erreur personnalisé
```python
from pydantic import BaseModel

class PaymentErrorDetail(BaseModel):
    transaction_id: str
    failure_code: str
    user_message: str
```

### Étape 2 : Spécifier le type d'erreur dans le Result
```python
from app.services import ServiceResult

def process_payment(amount: float) -> ServiceResult[PaymentResponse, PaymentErrorDetail]:
    payment_status, details = stripe_client.charge(amount)
    
    if not payment_status:
        custom_err = PaymentErrorDetail(
            transaction_id=details.id,
            failure_code=details.code,
            user_message="Votre solde est insuffisant."
        )
        return ServiceResult.service_failure(custom_err, status_code=402)
        
    return ServiceResult.service_success(PaymentResponse(status="success"))
```

---

## 4. Intégration API & Génération OpenAPI / Swagger

Pour que FastAPI génère correctement la documentation interactive (Swagger UI) et valide la réponse HTTP, vous devez configurer le retour de votre route.

### Approche A : Spécification Générique Directe
Vous pouvez annoter directement votre route avec `ApiBaseResponse[DataType, ErrorType]` :

```python
from fastapi import APIRouter, Response
from app.schemas.globals.api_base_response import ApiBaseResponse

router = APIRouter()

@router.post("/pay", response_model=ApiBaseResponse[PaymentResponse, PaymentErrorDetail])
async def pay(response: Response) -> ApiBaseResponse[PaymentResponse, PaymentErrorDetail]:
    service_res = payment_service.process_payment(100.0)
    
    # to_HTTP_api_base_response se charge d'instancier correctement le schéma de réponse
    # et de modifier le status_code HTTP de l'objet Response
    return service_res.to_HTTP_api_base_response(response)
```

### Approche B : Par Sous-classage (Recommandé pour Swagger plus propre)
L'utilisation directe de types génériques imbriqués peut parfois donner des noms de schémas générés automatiquement peu lisibles dans Swagger (ex: `ApiBaseResponse_PaymentResponse_PaymentErrorDetail_`). 

Pour un rendu Swagger premium et des schémas explicites, créez une sous-classe concrète :

```python
# app/schemas/payment.py
from app.schemas.globals.api_base_response import ApiBaseResponse

class PaymentApiResponse(ApiBaseResponse[PaymentResponse, PaymentErrorDetail]):
    """Réponse standardisée pour les opérations de paiement"""
    # Pas besoin de redéclarer les champs, ils sont hérités et typés automatiquement !
```

Puis dans votre routeur, utilisez cette sous-classe comme `response_model`, mais annotez le retour Python avec le type réellement renvoyé par `to_HTTP_api_base_response`.
Le helper retourne actuellement `ApiBaseResponse[D, E]`, pas la sous-classe concrète `PaymentApiResponse`. Un type checker ne peut donc pas inférer automatiquement que `ApiBaseResponse[PaymentResponse, PaymentErrorDetail]` est compatible avec `PaymentApiResponse`, même si FastAPI/Pydantic valident correctement la réponse au runtime.

```python
@router.post("/pay", response_model=PaymentApiResponse)
async def pay(response: Response) -> ApiBaseResponse[PaymentResponse, PaymentErrorDetail]:
    service_res = payment_service.process_payment(100.0)
    
    # Le retour est converti et validé proprement
    return service_res.to_HTTP_api_base_response(response)
```

Pour les routes simples qui n'ont pas de schéma d'erreur personnalisé, il existe un alias de `ApiBaseResponse` préconfiguré avec `AppError` : `DefaultAppApiResponse[D]`. Vous pouvez l'utiliser directement pour une documentation Swagger propre sans devoir spécifier le type d'erreur à chaque fois.

```python
from app.schemas.globals.api_base_response import DefaultAppApiResponse
from app.schemas.user_schemas import ReadUser

class ReadUserApiResponse(DefaultAppApiResponse[ReadUser]):
    """Réponse standardisée pour les opérations utilisateur"""
    # Pas besoin de redéclarer les champs, ils sont hérités et typés automatiquement !
```

Puis dans votre routeur :
```python
@router.get("/users/{user_id}", response_model=ReadUserApiResponse)
async def read_user(user_id: UUID, response: Response) -> ApiBaseResponse[ReadUser, AppError]:
    service_res = await user_service.service_find_user_by_id(user_id)
    return service_res.to_HTTP_api_base_response(response)
```

En résumé :
- `response_model=ReadUserApiResponse` sert à FastAPI, à la validation de sortie et à Swagger/OpenAPI.
- `-> ApiBaseResponse[ReadUser, AppError]` sert au typage statique Python, car c'est le type réellement retourné par `to_HTTP_api_base_response`.
- Annoter la route avec `-> ReadUserApiResponse` provoque généralement une erreur de typage tant que le helper ne construit pas explicitement cette sous-classe.

---

## 5. Bonnes Pratiques & Anti-patterns

> [!TIP]
> - **Utilisez toujours les helpers de classe** (`crud_success`, `service_failure`, etc.) au lieu d'instancier les classes directement via `__init__`.
> - **Utilisez l'approche par sous-classage de `ApiBaseResponse` ou `DefaultAppApiResponse` dans `response_model`** pour toutes les routes publiques afin de garder votre documentation Swagger claire et professionnelle.
> - **Gardez l'annotation de retour alignée avec le helper utilisé** : avec `to_HTTP_api_base_response`, annotez `ApiBaseResponse[D, E]`, pas la sous-classe OpenAPI.

> [!WARNING]
> - **Ne pas court-circuiter le typage** en utilisant `Any` comme type d'erreur si vous connaissez la structure de l'erreur. Spécifier la structure permet au frontend d'avoir un typage rigoureux généré via OpenAPI.
> - **Ne confondez pas `response_model` et annotation de retour** : `response_model` pilote FastAPI/OpenAPI, l'annotation `-> ...` pilote le type checker.

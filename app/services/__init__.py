from typing import Generic, Optional
from fastapi import Response

from app.globals.app_result import GenericAppResult, D, E
from app.globals.businnes_error import AppError
from app.globals.services_names import ServicesNames
from app.schemas.globals.api_base_response import ApiBaseResponse


class ServiceResult(GenericAppResult[D, E], Generic[D, E]):
    """
    Classe générique pour typer les réponses d'opérations des Services.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error), ainsi que des
    métadonnées comme le nom du service et le code de statut HTTP.
    """

    def __init__(
        self,
        ok: bool,
        service_name: str,
        status_code: int,
        data: Optional[D] = None,
        error: Optional[E] = None,
    ):
        super().__init__(ok=ok, data=data, error=error)
        self._service_name: str = service_name
        self._status_code: int = status_code

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<ServiceResult {self._service_name} Success: {self._data!r}>"
        return f"<ServiceResult {self._service_name} Error: {self._error!r}>"

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def status_code(self) -> int:
        return self._status_code

    def to_HTTP_api_base_response(self, reponse: Response) -> ApiBaseResponse[D, E]:
        """
        Methode pour convertir une instance de ServiceResult en une réponse HTTP API standardisée (ApiBaseResponse)
        à retourner aux clients de l'API.

        Cette méthode n'est utilisable que si la reponse à retourner est exactement ce que le service renvoie, c'est pas
        magie

        Args:
            reponse: L'objet Response de FastAPI pour pouvoir modifier le status code de la réponse HTTP à retourner.

        Returns:
            ApiBaseResponse[T, U] :  Une instance de ApiBaseResponse contenant les données de succès ou le message d'erreur,
             avec le code de status HTTP approprié.

        """
        if self.is_error():
            return ApiBaseResponse[D, E].error_response(
                error_message=self.error,
                response=reponse,
                status_code=self.status_code,
            )

        return ApiBaseResponse[D, E].success_response(
            data=self.data, response=reponse, status_code=self.status_code
        )

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def service_success(
        cls,
        data: D,
        status_code: int = 200,
        service_name: str = ServicesNames.UNKNOWN_SERVICE,
    ) -> "ServiceResult[D, E]":
        """
        Crée une réponse de succès avec les données fournies, le code de status HTTP à retourner et le nom du service.
        Args:
            data: Les données de succès à encapsuler dans la réponse.
            status_code: Le code de status HTTP à retourner (200 par défaut, mais doit être personnalisé ouiiiii).
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant les données de succès.
        """
        # pyrefly: ignore [bad-return]
        return cls(
            ok=True, data=data, status_code=status_code, service_name=service_name
        )

    @classmethod
    def service_failure(
        cls,
        error: E,
        status_code: int = 500,
        service_name: str = ServicesNames.UNKNOWN_SERVICE,
    ) -> "ServiceResult[D, E]":
        """
        Crée une réponse d'erreur avec le message fourni, le code de status HTTP à retourner et le nom du service.
        Args:
            error: Le message d'erreur à encapsuler dans la réponse.
            status_code: Le code de status HTTP à retourner (400 par défaut, on mettra des codes plus spécifiques selon les cas d'erreur)
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant le message d'erreur.
        """
        # pyrefly: ignore [bad-return]
        return cls(
            ok=False, error=error, status_code=status_code, service_name=service_name
        )


DefaultAppServiceResult = ServiceResult[D, AppError]

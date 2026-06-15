from typing import Generic, Optional, Any

from app.globals.app_result import GenericAppResult, D, E
from app.globals.businnes_error import AppError
from app.globals.services_names import ServicesNames
from app.services import ServiceResult


class CrudResult(GenericAppResult[D, E], Generic[D, E]):
    """
    Classe générique pour typer les réponses d'opérations CRUD dans les Repository.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """

    def __init__(
        self,
        ok: bool,
        status_code: int,
        data: Optional[D] = None,
        error: Optional[E] = None,
    ):
        super().__init__(ok=ok, data=data, error=error)
        self._status_code: int = status_code

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<CRUDResponse Status {self._status_code} Success: {self._data!r}>"
        return f"<CRUDResponse Status {self._status_code} Error: {self._error!r}>"

    @property
    def status_code(self) -> int:
        return self._status_code

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def crud_success(cls, data: D, status_code: int = 200) -> "CrudResult[D, E]":
        """Crée une réponse de succès avec les données fournies."""
        # pyrefly: ignore [bad-return]
        return cls(ok=True, data=data, status_code=status_code)

    @classmethod
    def crud_failure(cls, error: E, status_code: int = 500) -> "CrudResult[D, E]":
        """Crée une réponse d'erreur avec l'objet d'erreur fourni."""
        # pyrefly: ignore [bad-return]
        return cls(ok=False, error=error, status_code=status_code)

    def to_service_error(
        self, service_name: str = ServicesNames.UNKNOWN_SERVICE
    ) -> "ServiceResult[Any, E]":
        """Convertit ce CRUDResult en un ServiceResult d'erreur, en conservant le message et le status code."""
        result = ServiceResult.service_failure(
            # pyrefly: ignore [bad-argument-type]
            error=self.error,
            status_code=self.status_code,
            service_name=service_name,
        )
        # pyrefly: ignore [bad-return]
        return result


DefaultAppCrudResult = CrudResult[D, AppError]

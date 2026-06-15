from typing import Generic, Optional

from app.globals.app_result import GenericAppResult, D, E
from app.globals.businnes_error import AppError
from app.globals.services_names import ServicesNames


class IntegrationServiceResult(GenericAppResult[D, E], Generic[D, E]):
    """
    Classe générique pour typer les réponses d'opérations des Services Intégrés.
    """

    def __init__(
        self,
        ok: bool,
        service_name: str,
        status_code: int,
        data: Optional[D] = None,
        error: Optional[E] = None,
    ):
        """
        Initialise une instance de IntegrationServiceResult.
        UTILISER LES FONCTIONS D'AIDE (Helpers) POUR CRÉER DES INSTANCES DE CETTE CLASSE.
        Args:
            ok: Indique si l'opération a réussi ou échoué.
            service_name: Le nom du service qui génère cette réponse.
            status_code: Le code de statut HTTP associé à la réponse.
            data: Les données de succès à encapsuler dans la réponse (optionnel, utilisé uniquement si ok=True).
            error: L'objet d'erreur à encapsuler dans la réponse (optionnel, utilisé uniquement si ok=False).
        """
        super().__init__(ok=ok, data=data, error=error)
        self._service_name: str = service_name
        self._status_code: int = status_code

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<IntegrationServiceResult {self._service_name} Success: {self._data!r}>"
        return f"<IntegrationServiceResult {self._service_name} Error: {self._error!r}>"

    @property
    def integration_service_name(self) -> str:
        return self._service_name

    @property
    def status_code(self) -> int:
        return self._status_code

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def integration_service_success(
        cls,
        data: D,
        status_code: int = 200,
        service_name: str = ServicesNames.UNKNOWN_SERVICE,
    ) -> "IntegrationServiceResult[D, E]":
        """Crée une réponse de succès avec les données fournies."""
        # pyrefly: ignore [bad-return]
        return cls(
            ok=True, data=data, status_code=status_code, service_name=service_name
        )

    @classmethod
    def integration_service_failure(
        cls,
        error: E,
        status_code: int = 500,
        service_name: str = ServicesNames.UNKNOWN_SERVICE,
    ) -> "IntegrationServiceResult[D, E]":
        """Crée une réponse d'erreur avec l'objet d'erreur fourni."""
        # pyrefly: ignore [bad-return]
        return cls(
            ok=False, error=error, status_code=status_code, service_name=service_name
        )


AppIntegrationServiceResult = IntegrationServiceResult[D, AppError]

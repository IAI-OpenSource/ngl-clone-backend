from logging import getLogger, Logger
from typing import Generic, Any
from typing_extensions import TypeVar

from app.globals.businnes_error import AppError

logger: Logger = getLogger(__name__)

MISSING = object()


# Définition des variables de type (TypeVar)
# 'D' représentera le type de la donnée en cas de succès
# 'E' représentera le type de l'erreur en cas d'échec
# IMPORTANT: Aucune contrainte pour permettre la modularité maximale
# (tout type d'erreur personnalisé fonctionne, pas seulement AppError)
D = TypeVar("D")
E = TypeVar("E", default=AppError)


class GenericAppResult(Generic[D, E]):
    """
    Classe Générique pour typer les réponses d'opérations dans tout le systeme.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """

    __slots__ = ("_ok", "_data", "_error")

    def __init__(self, ok: bool, data: Any = MISSING, error: Any = MISSING):
        """
        Initialise une instance de GenericAppResult. Valide les arguments pour assurer la cohérence des données.
        NE PAS UTILISER DIRECTEMENT, UTILISER LES FONCTIONS DE CLASSE success() et failure() POUR CRÉER DES INSTANCES.
        Args:
            ok: bool: Indique si la réponse est un succès (True) ou une erreur (False).
            data: D | object: Les données de succès, requis si ok est True. Ignoré si ok est False.
            error: E | object: Le message d'erreur, requis si ok est False. Ignoré si ok est True.
        """
        if ok and data is MISSING:
            raise ValueError("Une réponse de succès doit contenir des données.")

        if not ok and error is MISSING:
            raise ValueError("Une réponse d'erreur doit contenir un message d'erreur.")

        self._ok: bool = ok
        self._data: D | object = data
        self._error: E | object = error

    def is_success(self) -> bool:
        """
        Verifie si la réponse est une reponse de succès.
        Returns:
            bool: True si c'est une reponse de succès, False sinon.
        """
        return self._ok

    def is_error(self) -> bool:
        """
        Verifie si la réponse est une reponse d'erreur.
        Returns:
            bool: True si c'est une reponse d'erreur, False sinon.
        """
        return not self._ok

    @property
    def data(self) -> D:
        """
        Retourne les données de succès. Lève une exception si c'est une erreur.
        Returns:
            D: Les données de succès.
        Raises:
            RuntimeError: Si la réponse est une erreur et que l'on tente d'accéder aux données.
        """
        if self.is_error():
            raise RuntimeError(
                "Tentative d'accéder aux données sur une réponse d'erreur."
            )
        return self._data  # type: ignore

    @property
    def error(self) -> E:
        """
        Retourne le message d'erreur. Lève une exception si c'est un succès.
        Returns:
            E: Le message d'erreur.
        Raises:
            RuntimeError: Si la réponse est un succès et que l'on tente d'accéder à l'erreur
        """
        if not self.is_error():
            raise RuntimeError(
                "Tentative d'accéder à l'erreur sur une réponse de succès."
            )
        return self._error  # type: ignore

    @classmethod
    def failure(cls, error: E) -> "GenericAppResult[D, E]":
        """
        Crée une réponse d'erreur avec le message d'erreur fourni.
        Args:
            error (E) : Le message d'erreur à inclure dans la réponse.
        Returns:
            GenericAppResult[D, E] : Une instance de GenericAppResult représentant une erreur.
        """
        # pyrefly: ignore [bad-return]
        return cls(ok=False, error=error)

    @classmethod
    def success(cls, data: D) -> "GenericAppResult[D, E]":
        """
        Crée une réponse de succès avec les données fournies.
        Args:
            data (D) : Les données à inclure dans la réponse de succès.
        Returns:
            GenericAppResult[D, E] : Une instance de GenericAppResult représentant un succès.
        """
        # pyrefly: ignore [bad-return]
        return cls(ok=True, data=data)

    def __repr__(self) -> str:
        if self.is_success():
            return f"GenericAppResult(Status=SUCCESS, Data={self._data})"
        return f"GenericAppResult(Status=FAILURE, Error={self._error})"

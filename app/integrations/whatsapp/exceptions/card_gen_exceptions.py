from __future__ import annotations


class CardGeneratorError(Exception):
    """Erreur lors de la génération d'une carte."""


class CardGeneratorNotInitializedError(CardGeneratorError):
    """Singleton non initialisé — appeler CardGenerator.initialize() d'abord."""

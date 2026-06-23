from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
from json import dumps, loads
from typing import Optional, Tuple
from uuid import UUID


class PaginationCursorUtils:

    @staticmethod
    def _encode(payload: dict) -> str:
        """
        Encode un dictionnaire de données en une chaîne de caractères utilisable comme curseur de pagination.
        Args:
            payload: Un dictionnaire contenant les données à encoder.

        Returns:
            str: Un encoding base64 du dictionnaire de données.
        """

        raw = dumps(payload, separators=(",", ":"))
        return urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def _decode(payload: str) -> dict:
        """
        Decode une chaîne de caractères encodée en un dictionnaire de données.
        Args:
            payload: Une chaîne de caractères encodée représentant les données du curseur.

        Returns:
            dict: Un dictionnaire contenant les données décodées du curseur.
        """

        decoded_bytes = urlsafe_b64decode(payload.encode())
        decoded_str = decoded_bytes.decode()
        return loads(decoded_str)

    @classmethod
    def encode_pagination_cursor(cls, last_item_id: UUID, secondary_dateable_attribute: datetime) -> str:
        """
        Encode un curseur de pagination à partir de l'ID du dernier élément et d'un attribut de date secondaire.
        Args:
            last_item_id: L'ID du dernier élément de la page actuelle.
            secondary_dateable_attribute: Un attribut de date utilisé pour garantir un ordre stable

        Returns:
            str: Un encoding base64 du curseur de pagination.
        """

        payload = {
            "dateable": secondary_dateable_attribute.isoformat(),
            "id": str(last_item_id),
        }

        return cls._encode(payload)

    @classmethod
    def decode_pagination_cursor(cls, payload: str) -> tuple[UUID, datetime]:
        """
        Decode un curseur de pagination encodé pour extraire les données de l'ID et de la date.
        Args:
            payload: Une chaîne de caractères encodée représentant le curseur de pagination.

        Returns:
            tuple[UUID, datetime]: Un tuple contenant l'ID du dernier élément et l'attribut de date décodés du curseur.
        """
        try:
            decoded = cls._decode(payload)


            return UUID(decoded["id"]), datetime.fromisoformat(decoded["dateable"])
        except Exception:
            raise ValueError("Curseur de pagination invalide.")

    @classmethod
    def encode_messages_cursor(
        cls,
        last_item_id: UUID,
        last_item_created_at: datetime,
        thread_id: UUID,
        is_next_page: bool = True
    ) -> str:
        """
        Encode un curseur de pagination spécifique pour les messages d'un thread.
        
        Pour la pagination par curseur, on a besoin de :
        - L'ID du dernier message de la page (pour garantir l'ordre)
        - La date de création du dernier message (pour éviter les problèmes d'ordre si des messages sont supprimés)
        - L'ID du thread (pour s'assurer que le curseur est valide pour ce thread)
        - Un flag pour indiquer si c'est pour la page suivante ou précédente
        
        Args:
            last_item_id: L'ID du dernier message de la page actuelle
            last_item_created_at: La date de création du dernier message
            thread_id: L'ID du thread
            is_next_page: Si True, curseur pour la page suivante, sinon pour la page précédente

        Returns:
            str: Curseur encodé en base64
        """
        payload = {
            "thread_id": str(thread_id),
            "id": str(last_item_id),
            "dateable": last_item_created_at.isoformat(),
            "direction": "next" if is_next_page else "previous"
        }
        return cls._encode(payload)

    @classmethod
    def decode_messages_cursor(cls, payload: str) -> Tuple[UUID, UUID, datetime, bool]:
        """
        Décode un curseur de pagination pour les messages d'un thread.
        
        Args:
            payload: Curseur encodé en base64

        Returns:
            Tuple[UUID, UUID, datetime, bool]: 
                - thread_id: L'ID du thread
                - message_id: L'ID du message de référence
                - created_at: La date de création du message
                - is_next_page: True pour page suivante, False pour page précédente

        Raises:
            ValueError: Si le curseur est invalide ou mal formaté
        """
        try:
            decoded = cls._decode(payload)
            thread_id = UUID(decoded["thread_id"])
            message_id = UUID(decoded["id"])
            created_at = datetime.fromisoformat(decoded["dateable"])
            direction = decoded.get("direction", "next")
            is_next_page = direction == "next"
            
            return thread_id, message_id, created_at, is_next_page
        except Exception as e:
            raise ValueError(f"Curseur de pagination invalide: {e}")

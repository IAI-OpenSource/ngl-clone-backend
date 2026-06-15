from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.db.models.enums.enums import UserType
from app.schemas.user_schemas import ReadUser


class RoleChecker:

    def __init__(self, allowed_roles: list[UserType]):
        self._allowed_roles = allowed_roles

    async def __call__(
        self, current_user: Annotated[ReadUser, Depends(get_current_user)]
    ):

        user_role = current_user.role

        if user_role not in self._allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès Refusé : Rôle insuffisant",
            )

        return current_user


class OthersCustomRoleChecker:
    """
    Classe pour vérifier les rôles personnalisés des utilisateurs.
    """

    pass

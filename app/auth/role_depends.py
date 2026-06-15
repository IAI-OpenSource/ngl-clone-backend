from app.auth.role_checker import RoleChecker
from app.db.models.enums.enums import UserType


class RoleDepends:

    all_authorize = RoleChecker(
        [
            UserType.ADMIN,
            UserType.USER,
        ]
    )

    only_admin_authorize = RoleChecker(
        [
            UserType.ADMIN,
        ]
    )

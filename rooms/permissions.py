from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Allow read-only access to everyone and write access to admins."""

    def has_permission(self, request, view):
        """Allow safe methods for all users and others for staff only."""

        return bool(
            (
                request.method in SAFE_METHODS
                and request.user
            )
            or (request.user and request.user.is_staff)
        )

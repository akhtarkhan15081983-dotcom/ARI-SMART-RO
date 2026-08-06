from rest_framework.permissions import BasePermission


class IsAdminOrManager(BasePermission):

    def has_permission(self, request, view):

        return request.user.is_authenticated and (
            request.user.role == "ADMIN"
            or request.user.role == "MANAGER"
        )


class IsEngineer(BasePermission):

    def has_permission(self, request, view):

        return request.user.is_authenticated and (
            request.user.role == "ENGINEER"
        )


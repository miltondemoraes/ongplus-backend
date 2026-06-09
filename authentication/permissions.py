from rest_framework.permissions import BasePermission


class IsDonor(BasePermission):
    """Permite acesso somente a usuários com perfil de Doador."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'donor'
        )


class IsOng(BasePermission):
    """Permite acesso somente a usuários com perfil de ONG."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'ong'
        )


class IsAdmin(BasePermission):
    """Permite acesso somente a administradores."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsNotOng(BasePermission):
    """Bloqueia ONGs de acessar fluxos de doação (conforme workflow do cliente)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role != 'ong'

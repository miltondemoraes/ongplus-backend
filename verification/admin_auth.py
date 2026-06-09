from django.http import JsonResponse

from transparency.auth_helpers import get_authenticated_user


def require_admin(request):
    user = get_authenticated_user(request)
    if user is None:
        return None, JsonResponse({'error': 'Autenticação necessária.'}, status=401)
    if user.role != 'admin':
        return None, JsonResponse({'error': 'Acesso restrito a administradores.'}, status=403)
    return user, None

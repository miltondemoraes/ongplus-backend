from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication


def get_authenticated_user(request):
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return user

    auth = JWTAuthentication()
    result = auth.authenticate(request)
    if result is None:
        return None
    return result[0]


def require_ngo_access(request, ong):
    user = get_authenticated_user(request)
    if user is None:
        return None, JsonResponse({'error': 'Autenticação necessária.'}, status=401)

    if user.is_staff or user.role == 'admin':
        return user, None

    user_ngo = getattr(user, 'ngo_profile', None)
    if user_ngo and user_ngo.id == ong.id:
        return user, None

    return None, JsonResponse({'error': 'Sem permissão para esta ONG.'}, status=403)

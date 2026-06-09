from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    CurrentUserSerializer,
    DonorRegisterSerializer,
    OngRegisterSerializer,
)


# --- Task 5: Views de cadastro ---

class DonorRegisterView(generics.CreateAPIView):
    serializer_class = DonorRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
            },
            status=status.HTTP_201_CREATED,
        )


class OngRegisterView(generics.CreateAPIView):
    serializer_class = OngRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
            },
            status=status.HTTP_201_CREATED,
        )


# --- Task 6: Views de login e logout ---

class CustomLoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'detail': 'Logout realizado com sucesso.'},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception:
            return Response(
                {'detail': 'Token inválido ou já expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


# --- Task 7: View de usuário atual ---

class CurrentUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Senha alterada com sucesso.'},
            status=status.HTTP_200_OK,
        )

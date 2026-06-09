from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    CustomLoginView,
    CurrentUserView,
    DonorRegisterView,
    LogoutView,
    OngRegisterView,
)

urlpatterns = [
    path('register/donor/', DonorRegisterView.as_view(), name='register-donor'),
    path('register/ong/', OngRegisterView.as_view(), name='register-ong'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]

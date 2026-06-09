from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, full_name, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        VISITOR = 'visitor', 'Visitante'
        DONOR = 'donor', 'Doador'
        ONG = 'ong', 'ONG'
        ADMIN = 'admin', 'Administrador'

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VISITOR)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.email


class DonorProfile(models.Model):
    """Perfil estendido para usuários com role='donor'."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donor_profile',
        help_text="Usuário associado ao perfil de doador",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Telefone de contato do doador",
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        help_text="Data de nascimento do doador",
    )
    preferred_causes = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de causas de interesse, ex: ['meio-ambiente', 'educacao']",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'donor_profile'
        verbose_name = 'Perfil de Doador'
        verbose_name_plural = 'Perfis de Doadores'

    def __str__(self):
        return f"DonorProfile({self.user.email})"


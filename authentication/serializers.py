import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomUser, DonorProfile
from verification.models import NGO


class DonorRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'As senhas não coincidem.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            role=CustomUser.Role.DONOR,
        )
        DonorProfile.objects.create(user=user)
        return user


class OngRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    cnpj = serializers.CharField(max_length=18)
    organization_name = serializers.CharField(max_length=255)
    pix_key = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    focus_area = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'password', 'password_confirm', 'cnpj', 'organization_name', 'pix_key', 'description', 'focus_area')

    def validate_cnpj(self, value):
        # Validação básica de formato: 00.000.000/0000-00 ou 14 dígitos
        cnpj_numeros = re.sub(r'\D', '', value)
        if len(cnpj_numeros) != 14:
            raise serializers.ValidationError('CNPJ inválido. Informe 14 dígitos.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'As senhas não coincidem.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        cnpj = validated_data.pop('cnpj')
        organization_name = validated_data.pop('organization_name')
        pix_key = validated_data.pop('pix_key', '')
        description = validated_data.pop('description', '')
        focus_area = validated_data.pop('focus_area', '')
        
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            role=CustomUser.Role.ONG,
        )
        
        NGO.objects.create(
            user=user,
            cnpj=cnpj,
            name=organization_name,
            pix_key=pix_key,
            description=description,
            focus_area=focus_area
        )
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    ngo_profile = serializers.SerializerMethodField()
    donor_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'full_name', 'role', 'date_joined', 'ngo_profile', 'donor_profile')
        read_only_fields = ('id', 'role', 'date_joined', 'ngo_profile', 'donor_profile')

    def get_ngo_profile(self, obj):
        ngo = getattr(obj, 'ngo_profile', None)
        if not ngo:
            return None
        return {
            'id': str(ngo.id),
            'name': ngo.name,
            'cnpj': ngo.cnpj,
            'score': int(float(ngo.current_score or 0)),
        }

    def get_donor_profile(self, obj):
        profile = getattr(obj, 'donor_profile', None)
        if not profile:
            return None
        return {
            'phone': profile.phone,
            'birthDate': profile.birth_date.isoformat() if profile.birth_date else None,
            'preferredCauses': profile.preferred_causes or [],
        }


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Senha atual incorreta.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'As senhas não coincidem.'})
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Adiciona dados extras ao payload do JWT
        token['role'] = user.role
        token['full_name'] = user.full_name
        return token

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser, DonorProfile
from verification.models import NGO
from authentication.serializers import CurrentUserSerializer
from decimal import Decimal
import datetime
from django.utils import timezone
from financial.models import Donation, Campaign, PaymentMethod


class ModelsCoverageTests(TestCase):
    def test_create_user_no_email_raises_error(self):
        with self.assertRaisesMessage(ValueError, 'O email é obrigatório.'):
            CustomUser.objects.create_user(email='', full_name='Test', password='123')

    def test_create_superuser(self):
        admin = CustomUser.objects.create_superuser(
            email='admin@teste.com',
            full_name='Admin',
            password='123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, CustomUser.Role.ADMIN)

    def test_custom_user_str(self):
        user = CustomUser.objects.create_user(email='str@teste.com', full_name='Str', password='123')
        self.assertEqual(str(user), 'str@teste.com')

    def test_donor_profile_str(self):
        user = CustomUser.objects.create_user(email='donorstr@teste.com', full_name='DStr', password='123')
        profile = DonorProfile.objects.create(user=user)
        self.assertEqual(str(profile), 'DonorProfile(donorstr@teste.com)')


class OngRegistrationTests(APITestCase):
    def test_cadastro_ong_valido_retorna_201(self):
        url = reverse('register-ong')
        data = {
            'email': 'ong_valida@teste.com',
            'full_name': 'ONG Responsavel',
            'password': 'Senha@Forte123',
            'password_confirm': 'Senha@Forte123',
            'organization_name': 'ONG Esperança',
            'cnpj': '11.111.111/0001-11',
            'pix_key': 'chavepix',
            'description': 'Ajudando o mundo',
            'focus_area': 'educacao'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'ong')
        self.assertTrue(NGO.objects.filter(cnpj='11.111.111/0001-11').exists())

    def test_cadastro_ong_cnpj_invalido_retorna_400(self):
        url = reverse('register-ong')
        data = {
            'email': 'ong_invalida@teste.com',
            'full_name': 'ONG Teste',
            'password': 'Senha@Forte123',
            'password_confirm': 'Senha@Forte123',
            'organization_name': 'ONG Invalida',
            'cnpj': '123'  # Inválido
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cnpj', response.data)

    def test_cadastro_ong_senhas_divergentes_retorna_400(self):
        url = reverse('register-ong')
        data = {
            'email': 'ong_diverge@teste.com',
            'full_name': 'ONG Teste',
            'password': 'Senha@Forte123',
            'password_confirm': 'SenhaDiferente',
            'organization_name': 'ONG Div',
            'cnpj': '11.111.111/0001-11'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CurrentUserSerializerTests(TestCase):
    def test_get_ngo_profile_none(self):
        user = CustomUser.objects.create_user(email='nongo@teste.com', full_name='Test', password='123')
        serializer = CurrentUserSerializer(user)
        self.assertIsNone(serializer.data['ngo_profile'])

    def test_get_donor_profile_none(self):
        user = CustomUser.objects.create_user(email='nodonor@teste.com', full_name='Test', password='123')
        # Usuários padrão já não vêm com DonorProfile a menos que criemos
        serializer = CurrentUserSerializer(user)
        self.assertIsNone(serializer.data['donor_profile'])


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='logout@teste.com',
            full_name='Logout User',
            password='Senha@Forte123',
            role='donor'
        )

    def test_logout_com_token_valido_retorna_205(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        url = reverse('logout')
        response = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_com_token_invalido_retorna_400(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        url = reverse('logout')
        response = self.client.post(url, {'refresh': 'token_falso_invalido'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class DonorViewsCoverageTests(APITestCase):
    def setUp(self):
        self.donor = CustomUser.objects.create_user(email='don@teste.com', full_name='Don', password='123', role='donor')
        self.not_donor = CustomUser.objects.create_user(email='ong@teste.com', full_name='Ong', password='123', role='ong')
        self.ngo = NGO.objects.create(user=self.not_donor, name='ONG Test', cnpj='11.111.111/0001-11')
        self.pm = PaymentMethod.objects.create(method_type='credit_card', name='CC')
        self.campaign = Campaign.objects.create(
            ong=self.ngo, title='Camp', target_amount=Decimal('100.00'),
            start_date=timezone.now(), end_date=timezone.now() + datetime.timedelta(days=1), status='active'
        )

    def _auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_donor_profile_forbidden(self):
        self._auth(self.not_donor)
        response = self.client.get(reverse('donor-profile'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_donor_profile_get(self):
        self._auth(self.donor)
        Donation.objects.create(
            donor=self.donor, campaign=self.campaign, ong=self.ngo,
            amount=Decimal('50.00'), payment_method=self.pm, status='completed'
        )
        response = self.client.get(reverse('donor-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['profile']['impactMetrics']['totalDonated'], 50.0)

    def test_donor_donations_forbidden(self):
        self._auth(self.not_donor)
        response = self.client.get(reverse('donor-donations'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_donor_donations_get(self):
        self._auth(self.donor)
        Donation.objects.create(
            donor=self.donor, campaign=self.campaign, ong=self.ngo,
            amount=Decimal('50.00'), payment_method=self.pm, status='completed'
        )
        response = self.client.get(reverse('donor-donations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_donor_causes_forbidden(self):
        self._auth(self.not_donor)
        response = self.client.get(reverse('donor-cause-preferences'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response_patch = self.client.patch(reverse('donor-cause-preferences'), {'causes': []})
        self.assertEqual(response_patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_donor_causes_get_and_patch(self):
        self._auth(self.donor)
        response = self.client.get(reverse('donor-cause-preferences'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        patch_data = {'causes': [{'id': 'meio-ambiente'}, 'saude', {'id': 'clima', 'name': 'Clima'}]}
        response_patch = self.client.patch(reverse('donor-cause-preferences'), patch_data, format='json')
        self.assertEqual(response_patch.status_code, status.HTTP_200_OK)
        
        # Test invalid data
        response_patch_invalid = self.client.patch(reverse('donor-cause-preferences'), {'causes': 'invalid'}, format='json')
        self.assertEqual(response_patch_invalid.status_code, status.HTTP_400_BAD_REQUEST)

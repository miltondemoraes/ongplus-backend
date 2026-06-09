from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import CustomUser


class DonorRegistrationTests(APITestCase):
    def test_cadastro_doador_valido_retorna_201(self):
        url = reverse('register-donor')
        data = {
            'email': 'doador@teste.com',
            'full_name': 'João Doador',
            'password': 'Senha@Forte123',
            'password_confirm': 'Senha@Forte123',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'donor')

    def test_cadastro_senhas_divergentes_retorna_400(self):
        url = reverse('register-donor')
        data = {
            'email': 'doador@teste.com',
            'full_name': 'João Doador',
            'password': 'Senha@Forte123',
            'password_confirm': 'SenhaDiferente',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cadastro_ong_sem_cnpj_retorna_400(self):
        url = reverse('register-ong')
        data = {
            'email': 'ong@teste.com',
            'full_name': 'Maria ONG',
            'password': 'Senha@Forte123',
            'password_confirm': 'Senha@Forte123',
            'organization_name': 'ONG Esperança',
            # cnpj ausente
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='usuario@teste.com',
            full_name='Usuário Teste',
            password='Senha@Forte123',
            role='donor',
        )

    def test_login_credenciais_validas_retorna_tokens(self):
        url = reverse('login')
        data = {'email': 'usuario@teste.com', 'password': 'Senha@Forte123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_credenciais_invalidas_retorna_401(self):
        url = reverse('login')
        data = {'email': 'usuario@teste.com', 'password': 'SenhaErrada'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentUserTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='eu@teste.com',
            full_name='Eu Mesmo',
            password='Senha@Forte123',
            role='donor',
        )

    def test_me_sem_token_retorna_401(self):
        url = reverse('current-user')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_com_token_valido_retorna_dados(self):
        # Autentica e pega o token
        login_url = reverse('login')
        login_response = self.client.post(
            login_url,
            {'email': 'eu@teste.com', 'password': 'Senha@Forte123'},
        )
        token = login_response.data['access']

        url = reverse('current-user')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'eu@teste.com')
        self.assertEqual(response.data['role'], 'donor')


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='senha@teste.com',
            full_name='Usuário Senha',
            password='Senha@Forte123',
            role='donor',
        )
        login_response = self.client.post(
            reverse('login'),
            {'email': 'senha@teste.com', 'password': 'Senha@Forte123'},
        )
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_alterar_senha_com_dados_validos_retorna_200(self):
        url = reverse('change-password')
        data = {
            'current_password': 'Senha@Forte123',
            'new_password': 'NovaSenha@456',
            'new_password_confirm': 'NovaSenha@456',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NovaSenha@456'))

    def test_alterar_senha_senha_atual_incorreta_retorna_400(self):
        url = reverse('change-password')
        data = {
            'current_password': 'SenhaErrada',
            'new_password': 'NovaSenha@456',
            'new_password_confirm': 'NovaSenha@456',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alterar_senha_confirmacao_divergente_retorna_400(self):
        url = reverse('change-password')
        data = {
            'current_password': 'Senha@Forte123',
            'new_password': 'NovaSenha@456',
            'new_password_confirm': 'OutraSenha@789',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alterar_senha_sem_token_retorna_401(self):
        self.client.credentials()
        url = reverse('change-password')
        data = {
            'current_password': 'Senha@Forte123',
            'new_password': 'NovaSenha@456',
            'new_password_confirm': 'NovaSenha@456',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

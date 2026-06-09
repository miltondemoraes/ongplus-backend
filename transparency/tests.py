import io
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser
from transparency.models import NGODocument
from verification.models import NGO


@override_settings(MEDIA_ROOT='/tmp/ongplus-test-media')
class UploadNgoDocumentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ngo_user = CustomUser.objects.create_user(
            email='upload-ong@test.com',
            full_name='ONG Upload',
            password='Senha@Forte123',
            role='donor',
        )
        self.ngo_user.role = CustomUser.Role.ONG
        self.ngo_user.save(update_fields=['role'])

        self.ngo = NGO.objects.create(
            user=self.ngo_user,
            name='ONG Upload Teste',
            cnpj='11.111.111/0001-11',
            description='Descrição',
        )
        self.other_user = CustomUser.objects.create_user(
            email='other@test.com',
            full_name='Outro Usuário',
            password='Senha@Forte123',
            role=CustomUser.Role.DONOR,
        )
        self.url = f'/api/v1/transparency/ngos/{self.ngo.id}/documents/upload/'

    def _auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_upload_pdf_creates_private_document(self):
        self._auth(self.ngo_user)
        pdf = SimpleUploadedFile(
            'comprovante.pdf',
            b'%PDF-1.4 test content',
            content_type='application/pdf',
        )

        response = self.client.post(self.url, {'file': pdf}, format='multipart')

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['title'], 'comprovante.pdf')
        self.assertFalse(payload['isPublic'])
        self.assertTrue(payload['documentUrl'].endswith('.pdf'))

        document = NGODocument.objects.get(id=payload['id'])
        self.assertFalse(document.is_public)
        self.assertTrue(document.file.name.endswith('.pdf'))

    def test_rejects_non_pdf(self):
        self._auth(self.ngo_user)
        file_obj = SimpleUploadedFile('nota.txt', b'hello', content_type='text/plain')
        response = self.client.post(self.url, {'file': file_obj}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        pdf = SimpleUploadedFile('comprovante.pdf', b'%PDF-1.4', content_type='application/pdf')
        response = self.client.post(self.url, {'file': pdf}, format='multipart')
        self.assertEqual(response.status_code, 401)

    def test_forbids_other_users(self):
        self._auth(self.other_user)
        pdf = SimpleUploadedFile('comprovante.pdf', b'%PDF-1.4', content_type='application/pdf')
        response = self.client.post(self.url, {'file': pdf}, format='multipart')
        self.assertEqual(response.status_code, 403)

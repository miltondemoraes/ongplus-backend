import json
import uuid
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from verification.exceptions import CnpjNotFound, ExternalApiError
from verification.models import NGO


class ApiTests(TestCase):
    """Integration tests for the verification API endpoints."""

    def setUp(self):
        self.client = Client()
        self.validation_url = reverse('ong-validation')
        self.ngo = NGO.objects.create(
            name='ONG Teste',
            cnpj='12345678000199',
            focus_area='meio-ambiente',
            city='Manaus',
            state='AM',
            current_score=100,
            years_operating=10,
            address_valid=True,
            verification_status=NGO.VerificationStatus.VERIFIED,
            last_verified_at=timezone.now(),
            social_networks=[
                {'platform': 'instagram', 'handle': '@ongteste'},
            ],
        )

    def test_health_check(self):
        response = self.client.get(reverse('health-check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_list_ngos(self):
        response = self.client.get(reverse('ngo-list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'ONG Teste')
        self.assertEqual(data[0]['score'], 100)
        self.assertTrue(data[0]['verified'])

    def test_ngo_detail(self):
        response = self.client.get(reverse('ngo-detail', args=[self.ngo.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'ONG Teste')
        self.assertEqual(data['socialLinks']['instagram'], '@ongteste')
        self.assertIn('verification', data)

    def test_ngo_verification(self):
        response = self.client.get(reverse('ngo-verification', args=[self.ngo.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'verified')
        self.assertEqual(data['criteria']['score'], 100)
        self.assertEqual(len(data['evidenceList']), 3)

    def test_allocation_criteria(self):
        response = self.client.get(reverse('allocation-criteria'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(sum(item['weight'] for item in data), 100)
        self.assertEqual(data[0]['weight'], 50)

    def test_ngo_detail_not_found(self):
        response = self.client.get(reverse('ngo-detail', args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_valid_request(self):
        payload = {"cnpj": "12345678000199"}

        with patch('verification.views.validate_ngo') as mock_validate:
            mock_validate.return_value = {
                "score": 75,
                "cnpj_ativo": True,
                "endereco_valido": True,
                "anos_atuacao": 10,
                "verification_status": "verified",
            }

            response = self.client.post(
                self.validation_url,
                data=json.dumps(payload),
                content_type='application/json',
            )

            self.assertEqual(response.status_code, 200)
            res_data = response.json()
            self.assertEqual(res_data["score"], 75)
            self.assertTrue(res_data["cnpj_ativo"])
            self.assertTrue(res_data["endereco_valido"])
            self.assertEqual(res_data["anos_atuacao"], 10)

    def test_invalid_cnpj_format(self):
        payload = {"cnpj": "1234567800019"}

        response = self.client.post(
            self.validation_url,
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_missing_cnpj(self):
        payload = {}

        response = self.client.post(
            self.validation_url,
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_cnpj_not_found(self):
        payload = {"cnpj": "00000000000000"}

        with patch('verification.views.validate_ngo') as mock_validate:
            mock_validate.side_effect = CnpjNotFound("CNPJ not found in external registry.")

            response = self.client.post(
                self.validation_url,
                data=json.dumps(payload),
                content_type='application/json',
            )

            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.json())

    def test_external_api_failure(self):
        payload = {"cnpj": "12345678000199"}

        with patch('verification.views.validate_ngo') as mock_validate:
            mock_validate.side_effect = ExternalApiError("External service unavailable.")

            response = self.client.post(
                self.validation_url,
                data=json.dumps(payload),
                content_type='application/json',
            )

            self.assertEqual(response.status_code, 502)
            self.assertIn("error", response.json())

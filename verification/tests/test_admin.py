import json
import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from verification.models import NGO, Campaign, Bundle


class AdminApiTests(TestCase):
    """Integration tests for the verification Admin API endpoints."""

    def setUp(self):
        self.client = Client()
        self.ngo = NGO.objects.create(
            name='ONG Pendente',
            cnpj='12345678000199',
            verification_status=NGO.VerificationStatus.PENDING,
            current_score=50,
        )
        self.campaign = Campaign.objects.create(
            ngo=self.ngo,
            name='Campanha Salve as Árvores',
            status=Campaign.Status.IN_REVIEW,
            target_amount=1000.0,
            is_active=True,
        )
        self.bundle = Bundle.objects.create(
            name='Super Bundle',
            cause='meio-ambiente',
            target_amount=5000.0,
        )

        self.mock_admin_user = MagicMock()
        self.mock_admin_user.role = 'admin'
        
        self.mock_donor_user = MagicMock()
        self.mock_donor_user.role = 'donor'

    @patch('verification.admin_auth.get_authenticated_user')
    def test_require_admin_auth_success(self, mock_get_user):
        """Test that an admin user can access an admin endpoint."""
        mock_get_user.return_value = self.mock_admin_user
        response = self.client.get(reverse('admin-review-ngos'))
        self.assertEqual(response.status_code, 200)

    @patch('verification.admin_auth.get_authenticated_user')
    def test_require_admin_auth_forbidden(self, mock_get_user):
        """Test that a non-admin user cannot access an admin endpoint."""
        mock_get_user.return_value = self.mock_donor_user
        response = self.client.get(reverse('admin-review-ngos'))
        self.assertEqual(response.status_code, 403)
        self.assertIn('Acesso restrito', response.json()['error'])

    @patch('verification.admin_auth.get_authenticated_user')
    def test_require_admin_auth_unauthorized(self, mock_get_user):
        """Test that an unauthenticated request cannot access an admin endpoint."""
        mock_get_user.return_value = None
        response = self.client.get(reverse('admin-review-ngos'))
        self.assertEqual(response.status_code, 401)
        self.assertIn('Autenticação', response.json()['error'])

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_review_ngos_view(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        response = self.client.get(reverse('admin-review-ngos'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'ONG Pendente')

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_ngo_verification_view(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        response = self.client.patch(
            reverse('admin-ngo-verification', args=[self.ngo.id]),
            data=json.dumps({'status': 'verified'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.ngo.refresh_from_db()
        self.assertEqual(self.ngo.verification_status, NGO.VerificationStatus.VERIFIED)
        self.assertIsNotNone(self.ngo.last_verified_at)

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_ngo_score_view(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        response = self.client.patch(
            reverse('admin-ngo-score', args=[self.ngo.id]),
            data=json.dumps({'score': 95.5}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.ngo.refresh_from_db()
        self.assertEqual(self.ngo.current_score, 95.5)

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_campaign_review_view(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        response = self.client.patch(
            reverse('admin-campaign-review', args=[self.campaign.id]),
            data=json.dumps({'status': 'aprovada'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.APPROVED)

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_create_bundle_view(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        payload = {
            'name': 'Novo Bundle Coletivo',
            'cause': 'educacao',
            'description': 'Ajuda geral',
            'targetAmount': 10000,
            'ngoIds': [str(self.ngo.id)]
        }
        response = self.client.post(
            reverse('admin-create-bundle'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['name'], 'Novo Bundle Coletivo')
        self.assertEqual(data['cause'], 'educacao')
        self.assertEqual(len(data['ongs']), 1)

    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_bundle_add_remove_ngo(self, mock_get_user):
        mock_get_user.return_value = self.mock_admin_user
        # Add
        response = self.client.post(
            reverse('admin-bundle-add-ngo', args=[self.bundle.id]),
            data=json.dumps({'ngoId': str(self.ngo.id)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.ngos.count(), 1)
        
        # Remove
        response_rm = self.client.delete(
            reverse('admin-bundle-remove-ngo', args=[self.bundle.id, self.ngo.id]),
        )
        self.assertEqual(response_rm.status_code, 200)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.ngos.count(), 0)

    @patch('verification.admin_views.validate_ngo')
    @patch('verification.admin_auth.get_authenticated_user')
    def test_admin_ngo_validate_view(self, mock_get_user, mock_validate_ngo):
        mock_get_user.return_value = self.mock_admin_user
        mock_validate_ngo.return_value = {'score': 85, 'valido': True}
        response = self.client.post(reverse('admin-ngo-validate', args=[self.ngo.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['validation']['score'], 85)

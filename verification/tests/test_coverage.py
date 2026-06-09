import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from verification.models import NGO, Campaign, Bundle

class VerificationCoverageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ngo = NGO.objects.create(
            name='ONG Coverage',
            cnpj='11222333000188',
            focus_area='saude',
            city='São Paulo',
            state='SP',
            current_score=85,
            years_operating=5,
            address_valid=True,
            verification_status=NGO.VerificationStatus.VERIFIED,
            last_verified_at=timezone.now(),
        )

    def test_campaigns_views(self):
        # Create campaign
        payload = {
            'name': 'Campanha Teste',
            'description': 'Desc',
            'cause': 'saude',
            'status': Campaign.Status.DRAFT,
            'targetAmount': 5000,
            'daysLeft': 30
        }
        resp = self.client.post(
            reverse('ngo_campaigns', args=[self.ngo.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 201)
        camp_id = resp.json()['id']

        # Get campaigns for ngo
        resp_ngo_camps = self.client.get(reverse('ngo_campaigns', args=[self.ngo.id]))
        self.assertEqual(resp_ngo_camps.status_code, 200)

        # Update campaign detail
        update_payload = {'name': 'Campanha Atualizada', 'targetAmount': 6000, 'daysLeft': 15}
        resp_update = self.client.put(
            reverse('campaign_detail', args=[camp_id]),
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        self.assertEqual(resp_update.status_code, 200)
        self.assertEqual(resp_update.json()['name'], 'Campanha Atualizada')

        # Change status
        resp_status = self.client.patch(
            reverse('campaign_status', args=[camp_id]),
            data=json.dumps({'status': Campaign.Status.IN_REVIEW}),
            content_type='application/json'
        )
        self.assertEqual(resp_status.status_code, 200)
        self.assertEqual(resp_status.json()['status'], Campaign.Status.IN_REVIEW)

        resp_status_ap = self.client.patch(
            reverse('campaign_status', args=[camp_id]),
            data=json.dumps({'status': Campaign.Status.PUBLISHED}),
            content_type='application/json'
        )
        self.assertEqual(resp_status_ap.status_code, 200)

        # list all campaigns
        resp_list = self.client.get(reverse('list_campaigns'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(len(resp_list.json()), 1)

    def test_bundles_views(self):
        bundle = Bundle.objects.create(
            name='Bundle Teste',
            description='Test Bundle',
            cause='saude',
            target_amount=10000
        )
        bundle.ngos.add(self.ngo)

        resp_list = self.client.get(reverse('list_bundles'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(len(resp_list.json()), 1)

        resp_detail = self.client.get(reverse('bundle-detail', args=[bundle.id]))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertEqual(resp_detail.json()['name'], 'Bundle Teste')

    def test_ngo_data_sources_view(self):
        resp = self.client.get(reverse('ngo-data-sources', args=[self.ngo.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 3)

    @patch('verification.services.address_service.urllib.request.urlopen')
    def test_address_service_coverage(self, mock_urlopen):
        from verification.services.address_service import get_address_by_cep
        import json, io
        
        # Mock ViaCEP success
        mock_response = io.BytesIO(json.dumps({'logradouro': 'Rua', 'bairro': 'B'}).encode('utf-8'))
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        res = get_address_by_cep('01001000')
        self.assertEqual(res['logradouro'], 'Rua')

    @patch('verification.services.cnpj_service.urllib.request.urlopen')
    def test_cnpj_service_coverage(self, mock_urlopen):
        from verification.services.cnpj_service import get_cnpj_data
        from urllib.error import HTTPError, URLError
        import json, io
        
        mock_response = io.BytesIO(json.dumps({'status': {'text': 'ATIVA'}}).encode('utf-8'))
        mock_urlopen.return_value.__enter__.return_value = mock_response
        data = get_cnpj_data('11111111111111')
        self.assertEqual(data['situacao'], 'ATIVA')

        mock_urlopen.side_effect = HTTPError(url='', code=404, msg='', hdrs={}, fp=None)
        from verification.exceptions import CnpjNotFound, ExternalApiError
        with self.assertRaises(CnpjNotFound):
            get_cnpj_data('11111111111111')
            
        mock_urlopen.side_effect = URLError("timeout")
        with self.assertRaises(ExternalApiError):
            get_cnpj_data('11111111111111')

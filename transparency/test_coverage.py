import json
from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser
from verification.models import NGO, Campaign
from financial.models import FinancialRecord, Donation
from transparency.models import ChangeRequest, NGODocument, NGOReport
from transparency.report_pdf import build_report_pdf

@override_settings(MEDIA_ROOT='/tmp/ongplus-test-media')
class TransparencyCoverageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(
            email='admin@teste.com', full_name='Admin', password='123'
        )
        self.ong_user = CustomUser.objects.create_user(
            email='ong@teste.com', full_name='ONG', password='123', role='ong'
        )
        self.ngo = NGO.objects.create(
            user=self.ong_user, name='Minha ONG', cnpj='11.111.111/0001-11', current_score=85
        )

    def _auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_global_metrics_view(self):
        FinancialRecord.objects.create(ong=self.ngo, record_type='transfer', amount=Decimal('500.00'), description='Repasse')
        Campaign.objects.create(ngo=self.ngo, name='Camp', target_amount=1000, raised_amount=500, end_date=timezone.now() + timezone.timedelta(days=1), status='publicada')
        
        resp = self.client.get('/api/v1/transparency/global-metrics/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['week']['ongsCount'], 1)
        self.assertEqual(resp.json()['week']['distributed'], 500.0)

    def test_recent_transfers_view(self):
        FinancialRecord.objects.create(ong=self.ngo, record_type='transfer', amount=Decimal('200.00'), description='T2')
        resp = self.client.get('/api/v1/transparency/recent-transfers/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]['ong'], 'Minha ONG')

    def test_financial_data_view(self):
        resp = self.client.get(f'/api/v1/transparency/ngos/{self.ngo.id}/financial-data/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('budgetUtilization', resp.json())

    def test_change_requests_flow(self):
        self._auth(self.ong_user)
        # submit
        resp = self.client.post(f'/api/v1/transparency/ngos/{self.ngo.id}/requests/', data=json.dumps({'field_name': 'name', 'new_value': 'Nova ONG', 'reason': 'Mudei'}), content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        req_id = resp.json()['id']
        
        # list pending
        resp_pending = self.client.get(f'/api/v1/transparency/ngos/{self.ngo.id}/pending-requests/')
        self.assertEqual(len(resp_pending.json()), 1)
        
        # list all
        resp_all = self.client.get(f'/api/v1/transparency/ngos/{self.ngo.id}/change-requests/')
        self.assertEqual(len(resp_all.json()), 1)
        
        # approve
        self.client.post(f'/api/v1/transparency/requests/{req_id}/approve/')
        # reject
        resp_submit2 = self.client.post(f'/api/v1/transparency/ngos/{self.ngo.id}/requests/', data=json.dumps({'field_name': 'desc', 'new_value': 'x', 'reason': 'y'}), content_type='application/json')
        req2_id = resp_submit2.json()['id']
        self.client.post(f'/api/v1/transparency/requests/{req2_id}/reject/')

        # history
        resp_hist = self.client.get(f'/api/v1/transparency/ngos/{self.ngo.id}/change-history/')
        self.assertEqual(resp_hist.status_code, 200)

    def test_ngo_documents_view(self):
        NGODocument.objects.create(ong=self.ngo, title='Doc Publico', file='fake.pdf', is_public=True)
        resp = self.client.get(f'/api/v1/transparency/ngos/{self.ngo.id}/documents/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_ngo_documents_upload(self):
        self._auth(self.ong_user)
        # Missing file
        resp = self.client.post(f'/api/v1/transparency/ngos/{self.ngo.id}/documents/upload/', {'title': 'Doc'})
        self.assertEqual(resp.status_code, 400)
        
        # Invalid file size/ext is handled by a mock or we can just send text file
        from django.core.files.uploadedfile import SimpleUploadedFile
        invalid_file = SimpleUploadedFile("doc.txt", b"file_content", content_type="text/plain")
        resp2 = self.client.post(f'/api/v1/transparency/ngos/{self.ngo.id}/documents/upload/', {'title': 'Doc', 'file': invalid_file})
        self.assertEqual(resp2.status_code, 400)
        
        valid_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4...", content_type="application/pdf")
        resp3 = self.client.post(f'/api/v1/transparency/ngos/{self.ngo.id}/documents/upload/', {'title': 'Doc', 'file': valid_file})
        self.assertEqual(resp3.status_code, 201)

    from unittest.mock import patch

    @patch('django.core.files.storage.filesystem.os.remove')
    @patch('pathlib.Path.unlink')
    def test_delete_reports(self, mock_unlink, mock_remove):
        self._auth(self.ong_user)
        NGOReport.objects.create(ong=self.ngo, title='Dummy', period='30-days')
        resp_del = self.client.delete(f'/api/v1/transparency/ngos/{self.ngo.id}/reports/')
        self.assertEqual(resp_del.status_code, 200)

    def test_build_report_pdf_direct(self):
        summary = {
            'ong': {'name': 'ONG Teste'},
            'cnpj': '11.111.111/0001-11',
            'period': 'Últimos 30 dias',
            'score': 95,
            'finance': {'totalIncome': 1000.50, 'totalDistributed': 500.00},
            'donors': {'donationCount': 10, 'uniqueDonors': 5, 'totalAmount': 1000.00},
            'campaigns': {'activeCount': 2, 'totalRaised': 1000.00}
        }
        pdf_bytes = build_report_pdf(summary, 'Relatório Geral')
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

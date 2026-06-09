import datetime
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser
from verification.models import NGO
from financial.models import Campaign, PaymentMethod, Donation, FinancialRecord


class FinancialTests(APITestCase):
    def setUp(self):
        self.ong_user = CustomUser.objects.create_user(
            email='ong@teste.com', full_name='ONG User', password='123', role='ong'
        )
        self.donor_user = CustomUser.objects.create_user(
            email='donor@teste.com', full_name='Donor User', password='123', role='donor'
        )
        self.ong = NGO.objects.create(
            user=self.ong_user, name='ONG Test', cnpj='11.111.111/0001-11'
        )
        self.payment_method = PaymentMethod.objects.create(
            method_type='credit_card', name='Cartão de Crédito'
        )
        self.campaign = Campaign.objects.create(
            ong=self.ong,
            title='Campanha Solidária',
            target_amount=Decimal('1000.00'),
            start_date=timezone.now() - datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=10),
            status=Campaign.Status.ACTIVE
        )
        
    def _auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_campaign_properties(self):
        self.assertEqual(self.campaign.progress_percentage, 0)
        self.assertTrue(self.campaign.is_active_campaign)

        self.campaign.target_amount = Decimal('0.00')
        self.assertEqual(self.campaign.progress_percentage, 0)
        
        self.campaign.target_amount = Decimal('1000.00')
        self.campaign.current_amount = Decimal('500.00')
        self.assertEqual(self.campaign.progress_percentage, 50)
        self.campaign.current_amount = Decimal('2000.00')
        self.assertEqual(self.campaign.progress_percentage, 100)

    def test_campaign_viewset_create(self):
        self._auth(self.ong_user)
        url = '/api/v1/financial/campaigns/'
        data = {
            'ong': str(self.ong.id),
            'title': 'Nova',
            'description': 'Desc',
            'target_amount': '500.00',
            'start_date': timezone.now() + datetime.timedelta(days=1),
            'end_date': timezone.now() + datetime.timedelta(days=5)
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Testar datas inválidas e valor negativo
        data['start_date'] = timezone.now() + datetime.timedelta(days=5)
        data['end_date'] = timezone.now() + datetime.timedelta(days=1)
        response_invalid_date = self.client.post(url, data)
        self.assertEqual(response_invalid_date.status_code, status.HTTP_400_BAD_REQUEST)

        data['start_date'] = timezone.now() + datetime.timedelta(days=1)
        data['end_date'] = timezone.now() + datetime.timedelta(days=5)
        data['target_amount'] = '0.00'
        response_invalid_amount = self.client.post(url, data)
        self.assertEqual(response_invalid_amount.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campaign_stats_and_actions(self):
        self._auth(self.ong_user)
        url = f'/api/v1/financial/campaigns/{self.campaign.id}/'
        
        # stats
        stats_resp = self.client.get(url + 'stats/')
        self.assertEqual(stats_resp.status_code, status.HTTP_200_OK)
        
        # pause / activate
        self.client.post(url + 'pause/')
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'paused')

        self.client.post(url + 'activate/')
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'active')

        # my_campaigns
        resp = self.client.get(f'/api/v1/financial/campaigns/my_campaigns/?ong_id={self.ong.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_donation_viewset_and_processing(self):
        self._auth(self.donor_user)
        url = '/api/v1/financial/donations/'
        data = {
            'campaign': str(self.campaign.id),
            'ong': str(self.ong.id),
            'amount': '100.00',
            'payment_method': str(self.payment_method.id),
            'status': 'pending'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        donation_id = response.data['id']

        # my_donations
        resp = self.client.get('/api/v1/financial/donations/my_donations/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # process donation
        process_url = f'/api/v1/financial/donations/{donation_id}/process/'
        process_resp = self.client.post(process_url)
        self.assertEqual(process_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(process_resp.data['status'], 'completed')
        
        # tentar processar de novo (falha)
        process_again_resp = self.client.post(process_url)
        self.assertEqual(process_again_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # tentar cancelar uma concluída
        cancel_url = f'/api/v1/financial/donations/{donation_id}/cancel/'
        cancel_resp = self.client.post(cancel_url)
        self.assertEqual(cancel_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_pending_donation(self):
        self._auth(self.donor_user)
        donation = Donation.objects.create(
            donor=self.donor_user,
            campaign=self.campaign,
            ong=self.ong,
            amount=Decimal('50.00'),
            payment_method=self.payment_method,
            status=Donation.Status.PENDING
        )
        url = f'/api/v1/financial/donations/{donation.id}/cancel/'
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.FAILED)

    def test_donation_stats(self):
        url = f'/api/v1/financial/donations/stats/?ong_id={self.ong.id}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_financial_record_ong_report(self):
        self._auth(self.ong_user)
        FinancialRecord.objects.create(
            ong=self.ong, record_type='donation', amount=Decimal('100.00'), description='Teste'
        )
        url = f'/api/v1/financial/financial-records/ong_report/?ong_id={self.ong.id}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(float(resp.data['total_income']), 100.0)

    def test_donation_stats_no_ong(self):
        url = '/api/v1/financial/donations/stats/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

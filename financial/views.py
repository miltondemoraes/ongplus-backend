from decimal import Decimal

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Campaign, PaymentMethod, Donation, PaymentTransaction, FinancialRecord
from .serializers import (
    CampaignSerializer, PaymentMethodSerializer, DonationSerializer,
    DonationDetailSerializer, PaymentTransactionSerializer,
    FinancialRecordSerializer, CampaignStatsSerializer, DonationStatsSerializer
)
from verification.models import NGO


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ong', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'target_amount', 'current_amount']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return []

    def create(self, request, *args, **kwargs):
        ong_id = request.data.get('ong')
        if not ong_id:
            return Response(
                {'error': 'ONG é obrigatória'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ong = NGO.objects.get(id=ong_id)
        except NGO.DoesNotExist:
            return Response(
                {'error': 'ONG não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['get'], permission_classes=[])
    def stats(self, request, pk=None):
        campaign = self.get_object()
        donations = campaign.donations.filter(status='completed')
        
        stats = {
            'campaign_id': campaign.id,
            'title': campaign.title,
            'target_amount': campaign.target_amount,
            'current_amount': campaign.current_amount,
            'progress_percentage': campaign.progress_percentage,
            'total_donations': donations.count(),
            'total_amount': donations.aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_donation': donations.aggregate(Avg('amount'))['amount__avg'] or 0,
        }
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_campaigns(self, request):
        try:
            ong = NGO.objects.get(id=request.query_params.get('ong_id'))
            campaigns = Campaign.objects.filter(ong=ong)
            serializer = self.get_serializer(campaigns, many=True)
            return Response(serializer.data)
        except NGO.DoesNotExist:
            return Response(
                {'error': 'ONG não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = Campaign.Status.ACTIVE
        campaign.save()
        return Response(
            {'message': 'Campanha ativada com sucesso'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = Campaign.Status.PAUSED
        campaign.save()
        return Response(
            {'message': 'Campanha pausada com sucesso'},
            status=status.HTTP_200_OK
        )


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'method_type']
    ordering = ['name']


class DonationViewSet(viewsets.ModelViewSet):
    queryset = Donation.objects.all()
    serializer_class = DonationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['donor', 'ong', 'status', 'recurrence_type']
    search_fields = ['donor__full_name', 'notes']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DonationDetailSerializer
        return DonationSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy', 'cancel']:
            return [IsAuthenticated()]
        return []

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_donations(self, request):
        donations = Donation.objects.filter(donor=request.user)
        serializer = self.get_serializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[])
    def stats(self, request):
        ong_id = request.query_params.get('ong_id')
        
        query = Donation.objects.filter(status='completed')
        if ong_id:
            query = query.filter(ong_id=ong_id)
        
        stats = {
            'total_donations': query.count(),
            'total_amount': query.aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_donation': query.aggregate(Avg('amount'))['amount__avg'] or 0,
            'completed_donations': query.filter(status='completed').count(),
            'failed_donations': Donation.objects.filter(status='failed').count(),
        }
        serializer = DonationStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        donation = self.get_object()
        
        if donation.status in ['completed', 'refunded']:
            return Response(
                {'error': 'Não é possível cancelar uma doação já concluída'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        donation.status = Donation.Status.FAILED
        donation.save()
        
        return Response(
            {'message': 'Doação cancelada com sucesso'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def process(self, request, pk=None):
        donation = self.get_object()
        
        if donation.status != Donation.Status.PENDING:
            return Response(
                {'error': 'Doação já foi processada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        donation.status = Donation.Status.PROCESSING
        donation.save()

        try:
            transaction = PaymentTransaction.objects.create(
                donation=donation,
                amount=donation.amount,
                net_amount=donation.amount * Decimal('0.97'),
                fee=donation.amount * Decimal('0.03'),
                status=PaymentTransaction.Status.CAPTURED
            )
            
            donation.status = Donation.Status.COMPLETED
            donation.save()
            
            if donation.campaign:
                donation.campaign.current_amount += donation.amount
                donation.campaign.save()
            
            serializer = self.get_serializer(donation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            donation.status = Donation.Status.FAILED
            donation.save()
            return Response(
                {'error': f'Erro ao processar pagamento: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['donation', 'status']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']

    def get_permissions(self):
        return [IsAuthenticated()]


class FinancialRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialRecord.objects.all()
    serializer_class = FinancialRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ong', 'record_type']
    search_fields = ['description']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_permissions(self):
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def ong_report(self, request):
        ong_id = request.query_params.get('ong_id')
        
        if not ong_id:
            return Response(
                {'error': 'ong_id é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        records = FinancialRecord.objects.filter(ong_id=ong_id)
        
        report = {
            'ong_id': ong_id,
            'total_records': records.count(),
            'total_income': records.filter(
                record_type__in=['donation', 'transfer']
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_fees': records.filter(
                record_type='fee'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_refunds': records.filter(
                record_type='refund'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'net_balance': records.filter(
                record_type__in=['donation', 'transfer']
            ).aggregate(Sum('amount'))['amount__sum'] or 0 - (
                records.filter(
                    record_type__in=['fee', 'refund']
                ).aggregate(Sum('amount'))['amount__sum'] or 0
            ),
        }
        return Response(report)

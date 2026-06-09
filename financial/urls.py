from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CampaignViewSet, PaymentMethodViewSet, DonationViewSet,
    PaymentTransactionViewSet, FinancialRecordViewSet
)

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'donations', DonationViewSet, basename='donation')
router.register(r'transactions', PaymentTransactionViewSet, basename='transaction')
router.register(r'financial-records', FinancialRecordViewSet, basename='financial-record')

app_name = 'financial'

urlpatterns = [
    path('', include(router.urls)),
]

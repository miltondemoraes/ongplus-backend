from django.urls import path

from verification.views import (
    health_check_view,
    list_ngos_view,
    ngo_detail_view,
    ngo_verification_view,
    allocation_criteria_view,
    validate_ong_view,
    list_campaigns_view,
    ngo_campaigns_view,
    campaign_detail_view,
    campaign_status_view,
    list_bundles_view,
    bundle_detail_view,
    ngo_data_sources_view,
)

urlpatterns = [
    path('v1/health/', health_check_view, name='health-check'),
    path('v1/ngos/', list_ngos_view, name='ngo-list'),
    path('v1/ngos/<uuid:pk>/', ngo_detail_view, name='ngo-detail'),
    path('v1/ngos/<uuid:pk>/verification/', ngo_verification_view, name='ngo-verification'),
    path('v1/transparency/allocation-criteria/', allocation_criteria_view, name='allocation-criteria'),
    path('ong-validation/', validate_ong_view, name='ong-validation'),
    path('v1/campaigns/', list_campaigns_view, name='list_campaigns'),
    path('v1/ngos/<uuid:pk>/campaigns/', ngo_campaigns_view, name='ngo_campaigns'),
    path('v1/campaigns/<uuid:pk>/', campaign_detail_view, name='campaign_detail'),
    path('v1/campaigns/<uuid:pk>/status/', campaign_status_view, name='campaign_status'),
    path('v1/bundles/', list_bundles_view, name='list_bundles'),
    path('v1/bundles/<uuid:pk>/', bundle_detail_view, name='bundle-detail'),
    path('v1/ngos/<uuid:pk>/data-sources/', ngo_data_sources_view, name='ngo-data-sources'),
]

from django.urls import path

from .donor_views import (
    DonorCausePreferencesView,
    DonorDonationsView,
    DonorProfileView,
)

urlpatterns = [
    path('profile/', DonorProfileView.as_view(), name='donor-profile'),
    path('donations/', DonorDonationsView.as_view(), name='donor-donations'),
    path('cause-preferences/', DonorCausePreferencesView.as_view(), name='donor-cause-preferences'),
]
